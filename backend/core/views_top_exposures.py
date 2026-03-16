from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from core.models import Exposure, Portfolio

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)
from core.serializers import TopExposuresResponseSerializer

def _bad_request(message: str, details: dict | None = None):
    payload = {"error": {"code": "bad_request", "message": message}}
    if details:
        payload["error"]["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=["Analytics"],
    operation_id="analytics_top_exposures",
    summary="Get top exposures",
    description=(
        "Return the largest exposures in a portfolio ranked by total insured value (TIV) "
        "or premium. Supports optional filters by country, line of business, and peril."
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
            name="by",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            enum=["tiv", "premium"],
            default="tiv",
            description="Ranking field.",
        ),
        OpenApiParameter(
            name="limit",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            default=50,
            description="Maximum number of exposures to return.",
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
    ],
    responses={
        200: OpenApiResponse(
            response=TopExposuresResponseSerializer,
            description="Top exposures returned successfully.",
            examples=[
                OpenApiExample(
                    "Top exposures by TIV",
                    value={
                        "portfolio_id": 1,
                        "by": "tiv",
                        "limit": 10,
                        "filters": {
                            "country": "FR",
                            "lob": None,
                            "peril": "FLOOD",
                        },
                        "count": 3,
                        "items": [
                            {
                                "id": 22,
                                "policy_id": "POL-0011",
                                "location_id": "",
                                "lob": "PROPERTY",
                                "peril": "FLOOD",
                                "country": "FR",
                                "region": "IDF",
                                "tiv": 1500000.0,
                                "premium": 18000.0,
                            },
                            {
                                "id": 57,
                                "policy_id": "POL-0046",
                                "location_id": "",
                                "lob": "PROPERTY",
                                "peril": "FLOOD",
                                "country": "FR",
                                "region": "IDF",
                                "tiv": 1400000.0,
                                "premium": 16000.0,
                            },
                        ],
                    },
                )
            ],
        ),
        400: OpenApiResponse(description="Invalid request parameters."),
        404: OpenApiResponse(description="Portfolio not found."),
    },
)

@api_view(["GET"])
def top_exposures(request):
    """
    GET /v1/analytics/top-exposures?portfolio_id=...&by=tiv&limit=50
    Optional filters: country, lob, peril
    """
    portfolio_id = request.query_params.get("portfolio_id")
    if not portfolio_id:
        return _bad_request("portfolio_id is required")

    by = (request.query_params.get("by") or "tiv").lower()
    if by not in ("tiv", "premium"):
        return _bad_request("Invalid 'by' param", {"allowed": ["tiv", "premium"]})

    try:
        limit = int(request.query_params.get("limit") or 50)
    except ValueError:
        return _bad_request("limit must be an integer")
    limit = max(1, min(limit, 200))

    country = request.query_params.get("country")
    lob = request.query_params.get("lob")
    peril = request.query_params.get("peril")

    try:
        portfolio = Portfolio.objects.get(id=int(portfolio_id))
    except Portfolio.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Portfolio not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    qs = Exposure.objects.filter(portfolio=portfolio)

    if country:
        qs = qs.filter(country=country.strip().upper())
    if lob:
        qs = qs.filter(lob=lob.strip().upper())
    if peril:
        qs = qs.filter(peril=peril.strip().upper())

    order_field = "-tiv" if by == "tiv" else "-premium"

    # If ordering by premium, null premiums should go last
    # (Django will handle NULLS LAST depending on DB; if not, it's still fine for demo)
    qs = qs.order_by(order_field)[:limit]

    items = []
    for e in qs:
        items.append(
            {
                "id": e.id,
                "policy_id": getattr(e, "policy_id", ""),
                "location_id": getattr(e, "location_id", ""),
                "lob": e.lob,
                "peril": e.peril,
                "country": e.country,
                "region": getattr(e, "region", ""),
                "tiv": float(e.tiv) if e.tiv is not None else None,
                "premium": float(e.premium) if e.premium is not None else None,
            }
        )

    return Response(
        {
            "portfolio_id": portfolio.id,
            "by": by,
            "limit": limit,
            "filters": {
                "country": country.strip().upper() if country else None,
                "lob": lob.strip().upper() if lob else None,
                "peril": peril.strip().upper() if peril else None,
            },
            "count": len(items),
            "items": items,
        }
    )