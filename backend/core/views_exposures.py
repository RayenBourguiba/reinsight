from decimal import Decimal
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from core.models import Exposure, Portfolio
from core.serializers import BulkExposureRequestSerializer
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from core.serializers import BulkExposureRequestSerializer, BulkExposureResponseSerializer
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)
from core.serializers import (
    BulkExposureRequestSerializer,
    BulkExposureResponseSerializer,
    ExposureListResponseSerializer,
    ExposureListItemSerializer,
)

def _bad_request(message: str, details: dict | None = None):
    payload = {"error": {"code": "bad_request", "message": message}}
    if details:
        payload["error"]["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=["Exposures"],
    operation_id="exposures_bulk_create",
    summary="Bulk create exposures",
    description=(
        "Persist normalized exposure rows into a portfolio. "
        "Supports batch insertion, capped error collection, and optional deduplication."
    ),
    request=BulkExposureRequestSerializer,
    examples=[
        OpenApiExample(
            "Bulk create example",
            request_only=True,
            value={
                "portfolio_id": 1,
                "dedup_mode": "composite",
                "batch_size": 1000,
                "max_errors": 200,
                "rows": [
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
                        "expiry_date": "2026-12-31",
                    }
                ],
            },
        )
    ],
    responses={
        201: OpenApiResponse(
            response=BulkExposureResponseSerializer,
            description="Exposure rows inserted successfully.",
            examples=[
                OpenApiExample(
                    "Bulk create response",
                    value={
                        "portfolio_id": 1,
                        "dedup_mode": "composite",
                        "received_rows": 50,
                        "inserted_rows": 0,
                        "skipped_duplicates": 50,
                        "error_rows": 0,
                        "errors": [],
                        "notes": [
                            "Rows are expected to be in canonical schema (output of apply-mapping).",
                            "For demo, we insert what we can and return first max_errors errors.",
                        ],
                    },
                )
            ],
        ),
        400: OpenApiResponse(description="Invalid request body."),
        404: OpenApiResponse(description="Portfolio not found."),
    },
)

@api_view(["POST"])
def bulk_create_exposures(request):
    """
    POST /v1/exposures/bulk
    Body:
      {
        "portfolio_id": 1,
        "rows": [ {canonical exposure row}, ... ],
        "batch_size": 1000,
        "max_errors": 200
      }
    """
    serializer = BulkExposureRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return _bad_request("Invalid request body", {"validation": serializer.errors})

    data = serializer.validated_data
    portfolio_id = data["portfolio_id"]
    rows = data["rows"]
    batch_size = data["batch_size"]
    max_errors = data["max_errors"]
    dedup_mode = data.get("dedup_mode", "none")

    try:
        portfolio = Portfolio.objects.get(id=portfolio_id)
    except Portfolio.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Portfolio not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    existing_policy_ids = set()
    existing_composites = set()
    skipped_duplicates = 0

    if dedup_mode == "policy_id":
        existing_policy_ids = set(
            Exposure.objects.filter(portfolio=portfolio)
            .exclude(policy_id="")
            .values_list("policy_id", flat=True)
        )

    if dedup_mode == "composite":
        existing_composites = set(
            Exposure.objects.filter(portfolio=portfolio)
            .exclude(policy_id="")
            .values_list("policy_id", "country", "region", "lob", "peril")
        )

    errors = []
    to_create = []
    inserted = 0

    # Convert and build Exposure instances
    for i, r in enumerate(rows):
        try:
            # Required fields already validated by serializer
            tiv_val = r["tiv"]
            if tiv_val is None or tiv_val <= 0:
                raise ValueError("tiv must be > 0")

            lob = str(r["lob"]).strip().upper()
            peril = str(r["peril"]).strip().upper()
            country = str(r["country"]).strip().upper()
            region = (r.get("region") or "").strip()
            policy_id = (r.get("policy_id") or "").strip()
            location_id = (r.get("location_id") or "").strip()

            # ---- DEDUP CHECK (skip duplicates) ----
            if dedup_mode == "policy_id" and policy_id:
                if policy_id in existing_policy_ids:
                    skipped_duplicates += 1
                    continue
                existing_policy_ids.add(policy_id)

            if dedup_mode == "composite" and policy_id:
                key = (policy_id, country, region, lob, peril)
                if key in existing_composites:
                    skipped_duplicates += 1
                    continue
                existing_composites.add(key)

            exp = Exposure(
                portfolio=portfolio,
                lob=lob,
                peril=peril,
                country=country,
                region=region,
                tiv=Decimal(str(tiv_val)),
                premium=Decimal(str(r["premium"])) if r.get("premium") is not None else None,
                policy_id=policy_id,
                location_id=location_id,
            )
            to_create.append(exp)
        except Exception as e:
            if len(errors) < max_errors:
                errors.append({"index": i, "reason": str(e), "row": r})
            continue

        # Bulk insert in batches
        if len(to_create) >= batch_size:
            Exposure.objects.bulk_create(to_create, batch_size=batch_size)
            inserted += len(to_create)
            to_create = []

    # Insert remaining
    if to_create:
        Exposure.objects.bulk_create(to_create, batch_size=batch_size)
        inserted += len(to_create)

    return Response(
        {
            "portfolio_id": portfolio_id,
            "dedup_mode": dedup_mode,
            "received_rows": len(rows),
            "inserted_rows": inserted,
            "skipped_duplicates": skipped_duplicates,
            "error_rows": len(errors),
            "errors": errors,
            "notes": [
                "Rows are expected to be in canonical schema (output of apply-mapping).",
                "For demo, we insert what we can and return first max_errors errors.",
            ],
        },
        status=status.HTTP_201_CREATED,
    )

@extend_schema(
    tags=["Exposures"],
    operation_id="exposures_list",
    summary="List exposures",
    description=(
        "List normalized exposures for a portfolio with optional filters and simple pagination."
    ),
    parameters=[
        OpenApiParameter(
            name="portfolio_id",
            type=int,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Portfolio identifier.",
        ),
        OpenApiParameter(
            name="country",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Optional country filter.",
        ),
        OpenApiParameter(
            name="lob",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Optional line-of-business filter.",
        ),
        OpenApiParameter(
            name="peril",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Optional peril filter.",
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Page number (default 1).",
            default=1,
        ),
        OpenApiParameter(
            name="page_size",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Number of items per page (default 20, max 200).",
            default=20,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ExposureListResponseSerializer,
            description="Exposure list returned successfully.",
            examples=[
                OpenApiExample(
                    "Exposure list example",
                    value={
                        "count": 73,
                        "page": 1,
                        "page_size": 2,
                        "results": [
                            {
                                "id": 22,
                                "portfolio_id": 1,
                                "lob": "PROPERTY",
                                "peril": "FLOOD",
                                "country": "FR",
                                "region": "IDF",
                                "tiv": 1500000.0,
                                "premium": 18000.0,
                                "policy_id": "POL-0011",
                                "location_id": "",
                                "lat": 48.8566,
                                "lon": 2.3522,
                                "inception_date": "2026-01-01",
                                "expiry_date": "2026-12-31",
                                "sum_insured": None,
                                "limit": None,
                                "deductible": None,
                            },
                            {
                                "id": 57,
                                "portfolio_id": 1,
                                "lob": "PROPERTY",
                                "peril": "FLOOD",
                                "country": "FR",
                                "region": "IDF",
                                "tiv": 1400000.0,
                                "premium": 16000.0,
                                "policy_id": "POL-0046",
                                "location_id": "",
                                "lat": 48.8566,
                                "lon": 2.3522,
                                "inception_date": "2026-01-01",
                                "expiry_date": "2026-12-31",
                                "sum_insured": None,
                                "limit": None,
                                "deductible": None,
                            },
                        ],
                    },
                )
            ],
        ),
        400: OpenApiResponse(description="Invalid request parameters."),
    },
)
@api_view(["GET"])
def list_exposures(request):
    portfolio_id = request.query_params.get("portfolio_id")
    if not portfolio_id:
        return _bad_request("Missing required query param: portfolio_id")

    try:
        portfolio_id = int(portfolio_id)
    except ValueError:
        return _bad_request("portfolio_id must be an integer")

    page_raw = request.query_params.get("page", "1")
    page_size_raw = request.query_params.get("page_size", "20")

    try:
        page = int(page_raw)
        page_size = int(page_size_raw)
        if page <= 0:
            raise ValueError
        if page_size <= 0 or page_size > 200:
            raise ValueError
    except ValueError:
        return _bad_request("page must be >= 1 and page_size must be between 1 and 200")

    qs = Exposure.objects.filter(portfolio_id=portfolio_id).order_by("-tiv", "id")

    for field in ["country", "lob", "peril"]:
        val = request.query_params.get(field)
        if val:
            qs = qs.filter(**{field: val})

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs[start:end]

    results = []
    for e in items:
        results.append(
            {
                "id": e.id,
                "portfolio_id": e.portfolio_id,
                "lob": e.lob,
                "peril": e.peril,
                "country": e.country,
                "region": e.region,
                "tiv": float(e.tiv),
                "premium": float(e.premium) if e.premium is not None else None,
                "policy_id": e.policy_id or "",
                "location_id": e.location_id or "",
                "lat": float(e.lat) if getattr(e, "lat", None) is not None else None,
                "lon": float(e.lon) if getattr(e, "lon", None) is not None else None,
                "inception_date": e.inception_date.isoformat() if getattr(e, "inception_date", None) else None,
                "expiry_date": e.expiry_date.isoformat() if getattr(e, "expiry_date", None) else None,
                "sum_insured": float(e.sum_insured) if getattr(e, "sum_insured", None) is not None else None,
                "limit": float(e.limit) if getattr(e, "limit", None) is not None else None,
                "deductible": float(e.deductible) if getattr(e, "deductible", None) is not None else None,
            }
        )

    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": results,
        }
    )


@extend_schema(
    tags=["Exposures"],
    operation_id="exposures_get",
    summary="Get exposure detail",
    description="Return a single normalized exposure by its identifier.",
    responses={
        200: OpenApiResponse(
            response=ExposureListItemSerializer,
            description="Exposure returned successfully.",
        ),
        404: OpenApiResponse(description="Exposure not found."),
    },
)
@api_view(["GET"])
def get_exposure(request, exposure_id: int):
    try:
        e = Exposure.objects.get(id=exposure_id)
    except Exposure.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Exposure not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "id": e.id,
            "portfolio_id": e.portfolio_id,
            "lob": e.lob,
            "peril": e.peril,
            "country": e.country,
            "region": e.region,
            "tiv": float(e.tiv),
            "premium": float(e.premium) if e.premium is not None else None,
            "policy_id": e.policy_id or "",
            "location_id": e.location_id or "",
            "lat": float(e.lat) if getattr(e, "lat", None) is not None else None,
            "lon": float(e.lon) if getattr(e, "lon", None) is not None else None,
            "inception_date": e.inception_date.isoformat() if getattr(e, "inception_date", None) else None,
            "expiry_date": e.expiry_date.isoformat() if getattr(e, "expiry_date", None) else None,
            "sum_insured": float(e.sum_insured) if getattr(e, "sum_insured", None) is not None else None,
            "limit": float(e.limit) if getattr(e, "limit", None) is not None else None,
            "deductible": float(e.deductible) if getattr(e, "deductible", None) is not None else None,
        }
    )