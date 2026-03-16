from decimal import Decimal
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from core.models import Exposure, Portfolio, Treaty

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)
from core.serializers import NetResponseSerializer

def _bad_request(message: str, details: dict | None = None):
    payload = {"error": {"code": "bad_request", "message": message}}
    if details:
        payload["error"]["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


def _clamp(x: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x

@extend_schema(
    tags=["Analytics"],
    operation_id="analytics_net_of_treaty",
    summary="Compute net-of-treaty view",
    description=(
        "Compute gross, ceded, and net exposure for a portfolio under a selected treaty. "
        "Supports Quota Share (QS) and Excess of Loss (XOL) logic, with optional grouping "
        "by country, region, line of business, or peril."
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
            name="treaty_id",
            type=int,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Treaty identifier applied to the portfolio.",
        ),
        OpenApiParameter(
            name="group_by",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Optional grouping dimension.",
            enum=["country", "region", "lob", "peril"],
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=NetResponseSerializer,
            description="Net-of-treaty metrics computed successfully.",
            examples=[
                OpenApiExample(
                    "Quota Share by country",
                    value={
                        "portfolio_id": 1,
                        "treaty": {
                            "id": 1,
                            "name": "Demo QS 30%",
                            "treaty_type": "QS",
                            "ceded_share_pct": 30.0,
                            "attachment": None,
                            "limit": None,
                        },
                        "count": 73,
                        "totals": {
                            "gross_tiv": 56860000.0,
                            "ceded_tiv": 17058000.0,
                            "net_tiv": 39802000.0,
                            "ceded_pct": 30.0,
                        },
                        "group_by": "country",
                        "buckets": [
                            {
                                "key": "FR",
                                "count": 35,
                                "gross_tiv": 30580000.0,
                                "ceded_tiv": 9174000.0,
                                "net_tiv": 21406000.0,
                                "ceded_pct": 30.0,
                            },
                            {
                                "key": "DE",
                                "count": 11,
                                "gross_tiv": 7700000.0,
                                "ceded_tiv": 2310000.0,
                                "net_tiv": 5390000.0,
                                "ceded_pct": 30.0,
                            },
                        ],
                    },
                )
            ],
        ),
        400: OpenApiResponse(description="Invalid request parameters."),
        404: OpenApiResponse(description="Portfolio or treaty not found."),
    },
)

@api_view(["GET"])
def net_of_treaty(request):
    """
    GET /v1/analytics/net?portfolio_id=...&treaty_id=...&group_by=country

    QS:
      ceded = tiv * (ceded_share_pct / 100)
    XOL:
      ceded = clamp(tiv - attachment, 0..limit)
    """
    portfolio_id = request.query_params.get("portfolio_id")
    treaty_id = request.query_params.get("treaty_id")
    group_by = request.query_params.get("group_by")  # optional

    if not portfolio_id or not treaty_id:
        return _bad_request("portfolio_id and treaty_id are required query params")

    try:
        portfolio = Portfolio.objects.get(id=int(portfolio_id))
    except Portfolio.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Portfolio not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        treaty = Treaty.objects.get(id=int(treaty_id), portfolio=portfolio)
    except Treaty.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Treaty not found for this portfolio"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    allowed_group = {None, "", "country", "region", "lob", "peril"}
    if group_by not in allowed_group:
        return _bad_request("Invalid group_by", {"allowed": ["country", "region", "lob", "peril"]})

    qs_share = None
    xol_attachment = None
    xol_limit = None

    if treaty.treaty_type == Treaty.QS:
        if treaty.ceded_share_pct is None:
            return _bad_request("QS treaty requires ceded_share_pct")
        qs_share = Decimal(treaty.ceded_share_pct) / Decimal("100")

    elif treaty.treaty_type == Treaty.XOL:
        if treaty.attachment is None or treaty.limit is None:
            return _bad_request("XOL treaty requires attachment and limit")
        xol_attachment = Decimal(treaty.attachment)
        xol_limit = Decimal(treaty.limit)

    exposures = Exposure.objects.filter(portfolio=portfolio)

    gross_total = Decimal("0")
    ceded_total = Decimal("0")
    net_total = Decimal("0")
    count = 0

    buckets = {}  # key -> {count, gross, ceded, net}

    for e in exposures.iterator():
        tiv = Decimal(e.tiv)
        gross = tiv

        if treaty.treaty_type == Treaty.QS:
            ceded = gross * qs_share
        else:
            ceded = _clamp(gross - xol_attachment, Decimal("0"), xol_limit)

        net = gross - ceded

        gross_total += gross
        ceded_total += ceded
        net_total += net
        count += 1

        if group_by:
            key = getattr(e, group_by) or "UNKNOWN"
            if key not in buckets:
                buckets[key] = {"key": key, "count": 0, "gross_tiv": Decimal("0"), "ceded_tiv": Decimal("0"), "net_tiv": Decimal("0")}
            buckets[key]["count"] += 1
            buckets[key]["gross_tiv"] += gross
            buckets[key]["ceded_tiv"] += ceded
            buckets[key]["net_tiv"] += net

    bucket_list = []
    if group_by:
        for b in buckets.values():
            gross_b = b["gross_tiv"]
            b["gross_tiv"] = float(gross_b)
            b["ceded_tiv"] = float(b["ceded_tiv"])
            b["net_tiv"] = float(b["net_tiv"])
            b["ceded_pct"] = round((b["ceded_tiv"] / b["gross_tiv"] * 100.0), 2) if b["gross_tiv"] else 0.0
            bucket_list.append(b)

        # Sort by gross desc
        bucket_list.sort(key=lambda x: x["gross_tiv"], reverse=True)

    return Response(
        {
            "portfolio_id": portfolio.id,
            "treaty": {
                "id": treaty.id,
                "name": treaty.name,
                "treaty_type": treaty.treaty_type,
                "ceded_share_pct": float(treaty.ceded_share_pct) if treaty.ceded_share_pct is not None else None,
                "attachment": float(treaty.attachment) if treaty.attachment is not None else None,
                "limit": float(treaty.limit) if treaty.limit is not None else None,
            },
            "count": count,
            "totals": {
                "gross_tiv": float(gross_total),
                "ceded_tiv": float(ceded_total),
                "net_tiv": float(net_total),
                "ceded_pct": round((float(ceded_total) / float(gross_total) * 100.0), 2) if gross_total else 0.0,
            },
            "group_by": group_by or None,
            "buckets": bucket_list,
        }
    )