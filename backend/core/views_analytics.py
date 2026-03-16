from decimal import Decimal
from django.db.models import Sum, Count
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)
from core.serializers import AccumulationResponseSerializer

ALLOWED_GROUP_BY = {"country", "region", "lob", "peril"}

def _bad_request(message: str, details: dict | None = None):
    payload = {"error": {"code": "bad_request", "message": message}}
    if details:
        payload["error"]["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=["Analytics"],
    operation_id="analytics_accumulation",
    summary="Compute portfolio accumulation",
    description=(
        "Aggregate exposures for a portfolio and return concentration metrics "
        "grouped by country, region, line of business, or peril. "
        "Supports optional filters and top-N ranking by total insured value (TIV)."
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
            name="group_by",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Dimension used for aggregation.",
            enum=["country", "region", "lob", "peril"],
            default="country",
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
            name="country",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Optional country filter.",
        ),
        OpenApiParameter(
            name="region",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Optional region filter.",
        ),
        OpenApiParameter(
            name="top_n",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Maximum number of aggregation buckets to return.",
            default=10,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=AccumulationResponseSerializer,
            description="Accumulation summary computed successfully.",
            examples=[
                OpenApiExample(
                    "Accumulation by country",
                    value={
                        "portfolio_id": 1,
                        "group_by": "country",
                        "filters": {"peril": "FLOOD"},
                        "totals": {
                            "count": 32,
                            "total_tiv": 28790000.0,
                        },
                        "buckets": [
                            {
                                "key": "FR",
                                "count": 20,
                                "tiv": 21000000.0,
                                "share_pct": 72.94,
                            },
                            {
                                "key": "DE",
                                "count": 4,
                                "tiv": 3200000.0,
                                "share_pct": 11.11,
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
def accumulation(request):
    """
    GET /v1/analytics/accumulation

    Required:
      - portfolio_id (int)

    Optional filters:
      - group_by in {country, region, lob, peril} (default: country)
      - lob
      - peril
      - country
      - region
      - top_n (int, default 10)

    Returns:
      - totals: count, total_tiv
      - buckets: list of {key, count, tiv, share_pct}
    """
    from core.models import Exposure  # local import keeps module lightweight

    # ---- Required params ----
    portfolio_id = request.query_params.get("portfolio_id")
    if not portfolio_id:
        return _bad_request("Missing required query param: portfolio_id")

    try:
        portfolio_id_int = int(portfolio_id)
    except ValueError:
        return _bad_request("portfolio_id must be an integer")

    # ---- group_by ----
    group_by = (request.query_params.get("group_by") or "country").strip().lower()
    if group_by not in ALLOWED_GROUP_BY:
        return _bad_request(
            "Invalid group_by",
            details={"allowed": sorted(ALLOWED_GROUP_BY), "received": group_by},
        )

    # ---- top_n ----
    top_n_raw = request.query_params.get("top_n") or "10"
    try:
        top_n = int(top_n_raw)
        if top_n <= 0 or top_n > 200:
            raise ValueError
    except ValueError:
        return _bad_request("top_n must be an integer between 1 and 200")

    # ---- Build queryset ----
    qs = Exposure.objects.filter(portfolio_id=portfolio_id_int)

    # Optional filters
    for field in ["lob", "peril", "country", "region"]:
        val = request.query_params.get(field)
        if val:
            qs = qs.filter(**{field: val})

    # ---- Totals ----
    totals = qs.aggregate(
        total_count=Count("id"),
        total_tiv=Sum("tiv"),
    )

    total_count = totals["total_count"] or 0
    total_tiv = totals["total_tiv"] or Decimal("0")

    # If no data, return empty buckets cleanly
    if total_count == 0 or total_tiv == 0:
        return Response(
            {
                "portfolio_id": portfolio_id_int,
                "group_by": group_by,
                "filters": {
                    k: request.query_params.get(k)
                    for k in ["lob", "peril", "country", "region"]
                    if request.query_params.get(k)
                },
                "totals": {"count": total_count, "total_tiv": float(total_tiv)},
                "buckets": [],
            }
        )

    # ---- Bucket aggregation ----
    bucket_qs = (
        qs.values(group_by)
        .annotate(
            count=Count("id"),
            tiv=Sum("tiv"),
        )
        .order_by("-tiv")[:top_n]
    )

    buckets = []
    for row in bucket_qs:
        key = row.get(group_by) or "UNKNOWN"
        tiv = row.get("tiv") or Decimal("0")
        share = (tiv / total_tiv) * Decimal("100") if total_tiv > 0 else Decimal("0")
        buckets.append(
            {
                "key": key,
                "count": row.get("count", 0),
                "tiv": float(tiv),
                "share_pct": float(share.quantize(Decimal("0.01"))),
            }
        )

    return Response(
        {
            "portfolio_id": portfolio_id_int,
            "group_by": group_by,
            "filters": {
                k: request.query_params.get(k)
                for k in ["lob", "peril", "country", "region"]
                if request.query_params.get(k)
            },
            "totals": {"count": total_count, "total_tiv": float(total_tiv)},
            "buckets": buckets,
        }
    )