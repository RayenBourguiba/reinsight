import csv
import re
import csv
import io
from difflib import SequenceMatcher
from datetime import datetime
from decimal import Decimal, InvalidOperation

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from core.schema import CANONICAL_EXPOSURE_SCHEMA
from core.models import Upload
from drf_spectacular.utils import OpenApiRequest
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)
from core.serializers import (
    SuggestMappingResponseSerializer,
    ApplyMappingRequestSerializer,
    ApplyMappingResponseSerializer,
)
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
)
from core.serializers import UploadFileRequestSerializer, UploadFileResponseSerializer

def _bad_request(message: str, details: dict | None = None):
    payload = {"error": {"code": "bad_request", "message": message}}
    if details:
        payload["error"]["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def canonical_schema(request):
    return Response(CANONICAL_EXPOSURE_SCHEMA)

@extend_schema(
    tags=["Ingestion"],
    operation_id="ingestion_upload_file",
    summary="Upload a CSV bordereau",
    description="Upload a CSV file containing raw exposure data for preview, mapping, and normalization.",
    request=OpenApiRequest(
        request={
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "format": "binary",
                    "description": "CSV bordereau file to upload."
                }
            },
            "required": ["file"],
        },
        encoding={"file": {"contentType": "text/csv"}},
    ),
    responses={
        201: OpenApiResponse(
            response=UploadFileResponseSerializer,
            description="File uploaded successfully.",
            examples=[
                OpenApiExample(
                    "Upload response example",
                    value={
                        "upload_id": "3befa7ab-7861-4963-a924-1b0ad3a4fa20",
                        "status": "UPLOADED",
                        "filename": "sample_bordereau.csv",
                        "size_bytes": 4217,
                        "content_type": "text/csv",
                        "created_at": "2026-03-12T12:59:25.980507+00:00",
                    },
                )
            ],
        ),
        400: OpenApiResponse(description="Invalid upload request."),
    },
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):
    """
    multipart/form-data:
      - file: CSV file
    """
    f = request.FILES.get("file")
    if not f:
        return _bad_request("Missing file field 'file' in multipart form-data")

    # Basic validation
    if f.size > 20 * 1024 * 1024:
        return _bad_request("File too large (max 20MB)")

    filename = f.name or "upload.csv"
    content_type = getattr(f, "content_type", "") or ""

    up = Upload.objects.create(
        filename=filename,
        content_type=content_type,
        size_bytes=f.size,
        status=Upload.STATUS_UPLOADED,
        file=f,
    )

    return Response(
        {
            "upload_id": str(up.id),
            "status": up.status,
            "filename": up.filename,
            "size_bytes": up.size_bytes,
            "content_type": up.content_type,
            "created_at": up.created_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def upload_status(request, upload_id: str):
    try:
        up = Upload.objects.get(id=upload_id)
    except Upload.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Upload not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "upload_id": str(up.id),
            "status": up.status,
            "filename": up.filename,
            "size_bytes": up.size_bytes,
            "content_type": up.content_type,
            "error_message": up.error_message,
            "created_at": up.created_at.isoformat(),
        }
    )


@api_view(["GET"])
def upload_preview(request, upload_id: str):
    rows_raw = request.query_params.get("rows", "50")
    try:
        rows = int(rows_raw)
        if rows <= 0 or rows > 200:
            raise ValueError
    except ValueError:
        return _bad_request("rows must be an integer between 1 and 200")

    try:
        up = Upload.objects.get(id=upload_id)
    except Upload.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Upload not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Read a small chunk; assume CSV for now
    try:
        with up.file.open("rb") as fh:
            raw = fh.read(1024 * 256)  # 256KB for preview
        # Attempt UTF-8 first; fallback latin-1
        try:
            text = raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
            encoding = "latin-1"

        # Detect delimiter from sample
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ","

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        header = next(reader, None)
        if not header:
            return _bad_request("CSV appears empty or missing header row")

        data_rows = []
        for i, row in enumerate(reader):
            if i >= rows:
                break
            # normalize row length
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            data_rows.append({header[j]: row[j] for j in range(len(header))})

        # mark parsed (optional)
        if up.status == Upload.STATUS_UPLOADED:
            up.status = Upload.STATUS_PARSED
            up.save(update_fields=["status"])

        return Response(
            {
                "upload_id": str(up.id),
                "filename": up.filename,
                "encoding": encoding,
                "delimiter": delimiter,
                "columns": header,
                "preview_rows": data_rows,
                "returned_rows": len(data_rows),
            }
        )
    except Exception as e:
        up.status = Upload.STATUS_FAILED
        up.error_message = str(e)
        up.save(update_fields=["status", "error_message"])
        return Response(
            {"error": {"code": "preview_failed", "message": "Failed to preview upload", "details": {"reason": str(e)}}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _norm(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[\s\-\.\(\)\[\]\/\\]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# Strong synonyms to look “industry-smart”
SYNONYMS = {
    "lob": ["lob", "line_of_business", "lineofbusiness", "class", "class_of_business", "business_line"],
    "peril": ["peril", "periltype", "hazard", "cat_peril", "event_type"],
    "country": ["country", "countrycode", "country_code", "iso_country", "iso2", "iso_2", "cntry"],
    "region": ["region", "state", "province", "county", "area", "admin1"],
    "city": ["city", "town", "municipality"],
    "tiv": ["tiv", "total_insured_value", "totalinsuredvalue", "total_value", "sum_tiv", "tiv_usd", "tiv_eur",
            "tiv_gbp"],
    "sum_insured": ["sum_insured", "suminsured", "si", "insured_sum", "insured_value"],
    "premium": ["premium", "written_premium", "gross_premium", "premium_usd", "premium_eur", "premium_gbp", "gwpi",
                "gwp"],
    "limit": ["limit", "policy_limit", "coverage_limit", "sum_limit"],
    "deductible": ["deductible", "excess", "retention", "franchise"],
    "lat": ["lat", "latitude", "y", "coord_y"],
    "lon": ["lon", "longitude", "lng", "long", "x", "coord_x"],
    "policy_id": ["policy_id", "policynumber", "policy_number", "policy", "contract_id"],
    "location_id": ["location_id", "loc_id", "location", "site_id", "risk_id"],
    "inception_date": ["inception_date", "inception", "start_date", "effective_date", "inceptiondate"],
    "expiry_date": ["expiry_date", "expiry", "end_date", "expiration_date", "expirydate"],
}


def _canonical_fields():
    # pulls from your canonical schema dict
    required = [f["name"] for f in CANONICAL_EXPOSURE_SCHEMA["required"]]
    optional = [f["name"] for f in CANONICAL_EXPOSURE_SCHEMA["optional"]]
    return required, optional


def _read_csv_header_and_delimiter(upload_obj):
    with upload_obj.file.open("rb") as fh:
        raw = fh.read(1024 * 128)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, None)
    if not header:
        raise ValueError("CSV appears empty or missing header row")
    return header, delimiter


def _score_column_to_field(col: str, field: str) -> float:
    coln = _norm(col)
    fieldn = _norm(field)

    # Exact normalized match is strong
    if coln == fieldn:
        return 1.0

    # Synonym match
    for syn in SYNONYMS.get(field, []):
        if coln == _norm(syn):
            return 0.98

    # Heuristic boosts (common in bordereaux)
    if field == "tiv" and ("tiv" in coln or "insured_value" in coln or "total" in coln and "value" in coln):
        return max(_similarity(coln, fieldn), 0.75)

    if field == "premium" and ("premium" in coln or "gwp" in coln or "gwpi" in coln):
        return max(_similarity(coln, fieldn), 0.75)

    if field in ("lat", "lon") and field in coln:
        return max(_similarity(coln, fieldn), 0.85)

    # General fuzzy similarity
    return _similarity(coln, fieldn)

@extend_schema(
    tags=["Ingestion"],
    operation_id="ingestion_suggest_mapping",
    summary="Suggest a canonical column mapping",
    description=(
        "Analyze uploaded CSV headers and suggest a mapping from source columns "
        "to the canonical exposure schema used by Reinsight."
    ),
    parameters=[
        OpenApiParameter(
            name="upload_id",
            type=str,
            location=OpenApiParameter.PATH,
            required=True,
            description="Upload UUID.",
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=SuggestMappingResponseSerializer,
            description="Suggested mapping generated successfully.",
            examples=[
                OpenApiExample(
                    "Suggested mapping example",
                    value={
                        "upload_id": "a43f7800-b67b-4c7a-96eb-f3ac656c78c0",
                        "filename": "sample_bordereau.csv",
                        "delimiter": ",",
                        "columns": [
                            "PolicyNumber", "LOB", "PerilType", "CountryCode", "Region",
                            "TIV_USD", "Premium_USD", "Latitude", "Longitude",
                            "InceptionDate", "ExpiryDate"
                        ],
                        "canonical_required": ["lob", "peril", "country", "tiv"],
                        "canonical_optional": [
                            "region", "city", "premium", "policy_id", "location_id",
                            "lat", "lon", "inception_date", "expiry_date",
                            "sum_insured", "limit", "deductible"
                        ],
                        "suggestions": [
                            {
                                "field": "lob",
                                "suggested_column": "LOB",
                                "confidence": 1.0,
                                "required": True
                            },
                            {
                                "field": "tiv",
                                "suggested_column": "TIV_USD",
                                "confidence": 0.98,
                                "required": True
                            }
                        ],
                        "mapping": {
                            "lob": "LOB",
                            "peril": "PerilType",
                            "country": "CountryCode",
                            "tiv": "TIV_USD",
                            "region": "Region",
                            "premium": "Premium_USD",
                            "policy_id": "PolicyNumber",
                            "lat": "Latitude",
                            "lon": "Longitude",
                            "inception_date": "InceptionDate",
                            "expiry_date": "ExpiryDate"
                        },
                        "missing_required_fields": [],
                        "unmapped_columns": [],
                        "notes": [
                            "This is a suggestion. Next step is apply-mapping to normalize rows.",
                            "Confidence >= 0.60 is auto-accepted by default in this demo."
                        ],
                    },
                )
            ],
        ),
        404: OpenApiResponse(description="Upload not found."),
        500: OpenApiResponse(description="Failed to read upload header."),
    },
)

@api_view(["POST"])
def suggest_mapping(request, upload_id: str):
    """
    POST /v1/ingestion/uploads/{id}/suggest-mapping

    Returns suggested mapping from CSV columns -> canonical fields,
    with confidence scores.
    """
    try:
        up = Upload.objects.get(id=upload_id)
    except Upload.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Upload not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        columns, delimiter = _read_csv_header_and_delimiter(up)
    except Exception as e:
        return Response(
            {"error": {"code": "suggest_mapping_failed", "message": "Failed to read header",
                       "details": {"reason": str(e)}}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    required_fields, optional_fields = _canonical_fields()
    all_fields = required_fields + optional_fields

    # Compute best match for each canonical field (one-to-one greedy)
    remaining_cols = columns[:]
    suggestions = []
    mapping = {}  # canonical_field -> column

    # rank fields: required first
    for field in all_fields:
        best_col = None
        best_score = -1.0

        for col in remaining_cols:
            score = _score_column_to_field(col, field)
            if score > best_score:
                best_score = score
                best_col = col

        # Threshold: only accept reasonable matches
        accepted = best_col is not None and best_score >= 0.60
        suggestions.append(
            {
                "field": field,
                "suggested_column": best_col if accepted else None,
                "confidence": round(float(best_score), 3) if best_col else 0.0,
                "required": field in required_fields,
            }
        )

        if accepted:
            mapping[field] = best_col
            remaining_cols.remove(best_col)

    missing_required = [f for f in required_fields if f not in mapping]
    used_columns = set(mapping.values())
    unmapped_columns = [c for c in columns if c not in used_columns]

    return Response(
        {
            "upload_id": str(up.id),
            "filename": up.filename,
            "delimiter": delimiter,
            "columns": columns,
            "canonical_required": required_fields,
            "canonical_optional": optional_fields,
            "suggestions": suggestions,
            "mapping": mapping,  # canonical -> source column
            "missing_required_fields": missing_required,
            "unmapped_columns": unmapped_columns,
            "notes": [
                "This is a suggestion. Next step is apply-mapping to normalize rows.",
                "Confidence >= 0.60 is auto-accepted by default in this demo.",
            ],
        }
    )


def _parse_decimal(val: str):
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None
    # handle common formatting: "1,200,000" or "1 200 000"
    s = s.replace(" ", "").replace(",", "")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Invalid number: {val}")


def _parse_float(val: str):
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Invalid float: {val}")


def _parse_date(val: str):
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None
    # accept YYYY-MM-DD (what we used in the sample)
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        # try common alternatives
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
    raise ValueError(f"Invalid date: {val}")


def _normalize_string(val: str):
    if val is None:
        return ""
    return str(val).strip()


def _normalize_lob(val: str):
    s = _normalize_string(val).upper()
    # normalize common abbreviations
    mapping = {
        "PROP": "PROPERTY",
        "PROPERTY": "PROPERTY",
        "ENERGY": "ENERGY",
        "MARINE": "MARINE",
        "AVIATION": "AVIATION",
        "CYBER": "CYBER",
        "LIAB": "LIABILITY",
        "LIABILITY": "LIABILITY",
        "POLRISK": "POLITICAL_RISK",
        "POLITICAL_RISK": "POLITICAL_RISK",
    }
    return mapping.get(s, s)


def _normalize_peril(val: str):
    s = _normalize_string(val).upper()
    mapping = {
        "INONDATION": "FLOOD",
        "FLOOD": "FLOOD",
        "WIND": "WIND",
        "QUAKE": "QUAKE",
        "STORM": "STORM",
        "FIRE": "FIRE",
        "TERROR": "TERROR",
    }
    return mapping.get(s, s)

@extend_schema(
    tags=["Ingestion"],
    operation_id="ingestion_apply_mapping",
    summary="Apply a mapping and normalize rows",
    description=(
        "Apply a canonical mapping to an uploaded CSV and normalize rows into the "
        "standard exposure schema. Can return a preview and optionally all normalized rows."
    ),
    request=ApplyMappingRequestSerializer,
    parameters=[
        OpenApiParameter(
            name="upload_id",
            type=str,
            location=OpenApiParameter.PATH,
            required=True,
            description="Upload UUID.",
        ),
        OpenApiParameter(
            name="include_rows",
            type=bool,
            location=OpenApiParameter.QUERY,
            required=False,
            description="If true, include full normalized_rows in the response.",
        ),
    ],
    examples=[
        OpenApiExample(
            "Apply mapping example",
            request_only=True,
            value={
                "mapping": {
                    "lob": "LOB",
                    "peril": "PerilType",
                    "country": "CountryCode",
                    "tiv": "TIV_USD",
                    "region": "Region",
                    "premium": "Premium_USD",
                    "policy_id": "PolicyNumber",
                    "lat": "Latitude",
                    "lon": "Longitude",
                    "inception_date": "InceptionDate",
                    "expiry_date": "ExpiryDate"
                },
                "options": {
                    "max_rows": 50,
                    "preview_rows": 5,
                    "include_rows": True
                }
            },
        )
    ],
    responses={
        200: OpenApiResponse(
            response=ApplyMappingResponseSerializer,
            description="Mapping applied and rows normalized successfully.",
            examples=[
                OpenApiExample(
                    "Apply mapping response example",
                    value={
                        "upload_id": "a43f7800-b67b-4c7a-96eb-f3ac656c78c0",
                        "filename": "sample_bordereau.csv",
                        "encoding": "utf-8",
                        "delimiter": ",",
                        "stats": {
                            "max_rows": 50,
                            "preview_rows": 5,
                            "parsed_rows": 50,
                            "valid_rows": 50,
                            "invalid_rows": 0,
                            "error_rows_returned": 0
                        },
                        "mapping": {
                            "lob": "LOB",
                            "peril": "PerilType",
                            "country": "CountryCode",
                            "tiv": "TIV_USD",
                            "region": "Region",
                            "premium": "Premium_USD",
                            "policy_id": "PolicyNumber",
                            "lat": "Latitude",
                            "lon": "Longitude",
                            "inception_date": "InceptionDate",
                            "expiry_date": "ExpiryDate"
                        },
                        "normalized_preview": [
                            {
                                "lob": "PROPERTY",
                                "peril": "FLOOD",
                                "country": "FR",
                                "tiv": 1200000.0,
                                "region": "IDF",
                                "premium": 12000.0,
                                "policy_id": "POL-0001",
                                "lat": 48.8566,
                                "lon": 2.3522,
                                "inception_date": "2026-01-01",
                                "expiry_date": "2026-12-31"
                            }
                        ],
                        "row_errors": [],
                        "next_step": {
                            "hint": "Send normalized_rows into POST /v1/exposures/bulk to persist them.",
                            "endpoint": "POST /v1/exposures/bulk"
                        },
                        "normalized_rows": []
                    },
                )
            ],
        ),
        400: OpenApiResponse(description="Invalid mapping request."),
        404: OpenApiResponse(description="Upload not found."),
        500: OpenApiResponse(description="Failed to apply mapping."),
    },
)

@api_view(["POST"])
def apply_mapping(request, upload_id: str):
    """
    POST /v1/ingestion/uploads/{id}/apply-mapping

    Body JSON:
      {
        "mapping": { "lob": "LOB", "tiv": "TIV_USD", ... },
        "options": {
           "max_rows": 5000,
           "preview_rows": 50
        }
      }

    Returns:
      - normalized_preview: first N normalized rows (canonical keys)
      - row_errors: first N errors with row_number, reason
      - stats
    """
    try:
        up = Upload.objects.get(id=upload_id)
    except Upload.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Upload not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    body = request.data or {}
    mapping = body.get("mapping")
    if not isinstance(mapping, dict) or not mapping:
        return _bad_request("Body must include a non-empty 'mapping' object")

    options = body.get("options") or {}
    include_rows_opt = options.get("include_rows", False)
    include_rows_qp = request.query_params.get("include_rows", "").lower() in ("1", "true", "yes", "y")
    include_rows = bool(include_rows_opt) or include_rows_qp
    max_rows = int(options.get("max_rows", 5000))
    preview_rows = int(options.get("preview_rows", 50))

    if max_rows <= 0 or max_rows > 200000:
        return _bad_request("options.max_rows must be between 1 and 200000")
    if preview_rows <= 0 or preview_rows > 200:
        return _bad_request("options.preview_rows must be between 1 and 200")

    required_fields, optional_fields = _canonical_fields()
    allowed_fields = set(required_fields + optional_fields)

    # Validate mapping keys are canonical fields
    unknown_fields = [k for k in mapping.keys() if k not in allowed_fields]
    if unknown_fields:
        return _bad_request("Mapping contains unknown canonical fields", {"unknown_fields": unknown_fields})

    # Read full file (but we will stop at max_rows)
    try:
        with up.file.open("rb") as fh:
            raw = fh.read()
        try:
            text = raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
            encoding = "latin-1"

        # delimiter detect
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ","

        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        if not reader.fieldnames:
            return _bad_request("CSV appears empty or missing header row")

        fieldnames = reader.fieldnames

        # validate referenced columns exist
        missing_columns = []
        for canonical_field, col in mapping.items():
            if col not in fieldnames:
                missing_columns.append({"field": canonical_field, "column": col})
        if missing_columns:
            return _bad_request("Some mapped columns do not exist in CSV header", {"missing_columns": missing_columns})

        normalized_preview = []
        normalized_rows = [] if include_rows else None
        row_errors = []
        parsed = 0
        valid = 0
        invalid = 0

        for idx, row in enumerate(reader, start=2):  # start=2 because header is line 1
            if parsed >= max_rows:
                break
            parsed += 1

            try:
                normalized = {}

                # Map fields
                for canonical_field, src_col in mapping.items():
                    raw_val = row.get(src_col)

                    # Type coercion based on field
                    if canonical_field in ("tiv", "premium", "sum_insured", "limit", "deductible"):
                        dec = _parse_decimal(raw_val)
                        normalized[canonical_field] = float(dec) if dec is not None else None

                    elif canonical_field in ("lat", "lon"):
                        fl = _parse_float(raw_val)
                        normalized[canonical_field] = fl

                    elif canonical_field in ("inception_date", "expiry_date"):
                        normalized[canonical_field] = _parse_date(raw_val)

                    elif canonical_field == "lob":
                        normalized[canonical_field] = _normalize_lob(raw_val)

                    elif canonical_field == "peril":
                        normalized[canonical_field] = _normalize_peril(raw_val)

                    else:
                        normalized[canonical_field] = _normalize_string(raw_val)

                # Ensure required fields exist
                missing_req = []
                for rf in required_fields:
                    v = normalized.get(rf)
                    if v is None or (isinstance(v, str) and v.strip() == ""):
                        missing_req.append(rf)

                if missing_req:
                    raise ValueError(f"Missing required fields after mapping: {missing_req}")

                valid += 1

                if include_rows:
                    normalized_rows.append(normalized)

                if len(normalized_preview) < preview_rows:
                    normalized_preview.append(normalized)

            except Exception as e:
                invalid += 1
                if len(row_errors) < 200:
                    row_errors.append(
                        {
                            "row_number": idx,
                            "reason": str(e),
                            "raw_row": row if len(row_errors) < 10 else None,
                            # only include raw row for first 10 errors
                        }
                    )

        response = {
            "upload_id": str(up.id),
            "filename": up.filename,
            "encoding": encoding,
            "delimiter": delimiter,
            "stats": {
                "max_rows": max_rows,
                "preview_rows": preview_rows,
                "parsed_rows": parsed,
                "valid_rows": valid,
                "invalid_rows": invalid,
                "error_rows_returned": len(row_errors),
            },
            "mapping": mapping,
            "normalized_preview": normalized_preview,
            "row_errors": row_errors,
            "next_step": {
                "hint": "Send normalized_rows into POST /v1/exposures/bulk to persist them.",
                "endpoint": "POST /v1/exposures/bulk",
            },
        }

        if include_rows:
            response["normalized_rows"] = normalized_rows

        return Response(response)

    except Exception as e:
        up.status = Upload.STATUS_FAILED
        up.error_message = str(e)
        up.save(update_fields=["status", "error_message"])
        return Response(
            {"error": {"code": "apply_mapping_failed", "message": "Failed to apply mapping",
                       "details": {"reason": str(e)}}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
