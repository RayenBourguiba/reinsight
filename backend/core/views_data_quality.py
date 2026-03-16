from collections import Counter, defaultdict
from decimal import Decimal
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
from core.serializers import DataQualityResponseSerializer

def _percentile(sorted_vals, p: float):
    # p in [0,1]
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    idx = int(round((n - 1) * p))
    idx = max(0, min(idx, n - 1))
    return sorted_vals[idx]

@extend_schema(
    tags=["Quality"],
    operation_id="portfolio_data_quality",
    summary="Get portfolio data quality report",
    description=(
        "Return a portfolio-level data quality summary including missing required fields, "
        "invalid values, duplicate records, outliers, and high-level distributions."
    ),
    parameters=[
        OpenApiParameter(
            name="portfolio_id",
            type=int,
            location=OpenApiParameter.PATH,
            required=True,
            description="Portfolio identifier.",
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DataQualityResponseSerializer,
            description="Data quality report returned successfully.",
            examples=[
                OpenApiExample(
                    "Data quality example",
                    value={
                        "portfolio_id": 1,
                        "totals": {"exposures": 73},
                        "missing_required": {
                            "counts": {"lob": 0, "peril": 0, "country": 0, "tiv": 0},
                            "pct": {"lob": 0.0, "peril": 0.0, "country": 0.0, "tiv": 0.0},
                        },
                        "invalid_values": {
                            "tiv_non_positive": 0,
                            "premium_negative": 0,
                        },
                        "duplicates": {
                            "empty_policy_id": 9,
                            "by_policy_id_top": [
                                {"policy_id": "POL-0001", "count": 2},
                                {"policy_id": "POL-0002", "count": 2},
                            ],
                            "by_composite_top": [
                                {
                                    "key": {
                                        "policy_id": "POL-0001",
                                        "country": "FR",
                                        "region": "IDF",
                                        "lob": "PROPERTY",
                                        "peril": "FLOOD",
                                    },
                                    "count": 2,
                                }
                            ],
                        },
                        "outliers": {
                            "tiv_p95": 1200000.0,
                            "tiv_p99": 1400000.0,
                            "top_tiv": [
                                {
                                    "id": 22,
                                    "policy_id": "POL-0011",
                                    "country": "FR",
                                    "region": "IDF",
                                    "lob": "PROPERTY",
                                    "peril": "FLOOD",
                                    "tiv": 1500000.0,
                                }
                            ],
                        },
                        "distributions": {
                            "by_country": [
                                {"key": "FR", "count": 35, "tiv": 30580000.0}
                            ],
                            "by_lob": [
                                {"key": "PROPERTY", "count": 54, "tiv": 44310000.0}
                            ],
                            "by_peril": [
                                {"key": "FLOOD", "count": 34, "tiv": 30790000.0}
                            ],
                        },
                        "notes": [
                            "This is a lightweight demo-quality report (single-pass scan).",
                            "It highlights duplicates and extreme values that often break bordereaux ingestion.",
                        ],
                    },
                )
            ],
        ),
        404: OpenApiResponse(description="Portfolio not found."),
    },
)

@api_view(["GET"])
def portfolio_data_quality(request, portfolio_id: int):
    """
    GET /v1/portfolios/{id}/data-quality
    """
    try:
        portfolio = Portfolio.objects.get(id=int(portfolio_id))
    except Portfolio.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Portfolio not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    qs = Exposure.objects.filter(portfolio=portfolio)
    total = qs.count()

    # Required fields (for your current DB model)
    required = ["lob", "peril", "country", "tiv"]

    missing_counts = {f: 0 for f in required}
    invalid = {
        "tiv_non_positive": 0,
        "premium_negative": 0,
    }

    empty_policy_id = 0
    policy_id_counter = Counter()
    composite_counter = Counter()

    tiv_values = []
    premium_values = []

    # Distributions
    dist_country = defaultdict(lambda: {"count": 0, "tiv": Decimal("0")})
    dist_lob = defaultdict(lambda: {"count": 0, "tiv": Decimal("0")})
    dist_peril = defaultdict(lambda: {"count": 0, "tiv": Decimal("0")})

    # Iterate once
    for e in qs.iterator():
        # Missing required
        if not e.lob:
            missing_counts["lob"] += 1
        if not e.peril:
            missing_counts["peril"] += 1
        if not e.country:
            missing_counts["country"] += 1
        if e.tiv is None:
            missing_counts["tiv"] += 1

        # Invalid numeric
        tiv = Decimal(e.tiv) if e.tiv is not None else None
        if tiv is not None:
            tiv_values.append(float(tiv))
            if tiv <= 0:
                invalid["tiv_non_positive"] += 1

        prem = e.premium
        if prem is not None:
            premium_values.append(float(prem))
            if prem < 0:
                invalid["premium_negative"] += 1

        # Duplicates
        pid = (e.policy_id or "").strip()
        if pid == "":
            empty_policy_id += 1
        else:
            policy_id_counter[pid] += 1

        # Composite duplicate key (stronger than just policy_id)
        comp = (
            pid,
            (e.country or "").strip(),
            (e.region or "").strip(),
            (e.lob or "").strip(),
            (e.peril or "").strip(),
        )
        if pid != "":
            composite_counter[comp] += 1

        # Distributions (only if tiv exists)
        if tiv is not None:
            c = (e.country or "UNKNOWN").strip().upper()
            l = (e.lob or "UNKNOWN").strip().upper()
            p = (e.peril or "UNKNOWN").strip().upper()

            dist_country[c]["count"] += 1
            dist_country[c]["tiv"] += tiv

            dist_lob[l]["count"] += 1
            dist_lob[l]["tiv"] += tiv

            dist_peril[p]["count"] += 1
            dist_peril[p]["tiv"] += tiv

    # Duplicate summaries
    duplicate_policy_ids = [{"policy_id": k, "count": v} for k, v in policy_id_counter.items() if v > 1]
    duplicate_policy_ids.sort(key=lambda x: x["count"], reverse=True)

    duplicate_composites = [
        {"key": {"policy_id": k[0], "country": k[1], "region": k[2], "lob": k[3], "peril": k[4]}, "count": v}
        for k, v in composite_counter.items()
        if v > 1
    ]
    duplicate_composites.sort(key=lambda x: x["count"], reverse=True)

    # Outliers (simple p95/p99)
    tiv_sorted = sorted(tiv_values)
    p95 = _percentile(tiv_sorted, 0.95)
    p99 = _percentile(tiv_sorted, 0.99)

    # List top 10 tiv as “outliers candidates”
    top_tiv = []
    if total > 0:
        top_qs = qs.order_by("-tiv")[:10]
        for e in top_qs:
            top_tiv.append(
                {
                    "id": e.id,
                    "policy_id": (e.policy_id or ""),
                    "country": e.country,
                    "region": e.region,
                    "lob": e.lob,
                    "peril": e.peril,
                    "tiv": float(e.tiv) if e.tiv is not None else None,
                }
            )

    def _dist_to_list(d):
        out = []
        for k, v in d.items():
            out.append({"key": k, "count": v["count"], "tiv": float(v["tiv"])})
        out.sort(key=lambda x: x["tiv"], reverse=True)
        return out

    # Missing % calculation
    missing_pct = {
        f: round((missing_counts[f] / total * 100.0), 2) if total else 0.0 for f in required
    }

    return Response(
        {
            "portfolio_id": portfolio.id,
            "totals": {
                "exposures": total,
            },
            "missing_required": {
                "counts": missing_counts,
                "pct": missing_pct,
            },
            "invalid_values": invalid,
            "duplicates": {
                "empty_policy_id": empty_policy_id,
                "by_policy_id_top": duplicate_policy_ids[:20],
                "by_composite_top": duplicate_composites[:20],
            },
            "outliers": {
                "tiv_p95": p95,
                "tiv_p99": p99,
                "top_tiv": top_tiv,
            },
            "distributions": {
                "by_country": _dist_to_list(dist_country),
                "by_lob": _dist_to_list(dist_lob),
                "by_peril": _dist_to_list(dist_peril),
            },
            "notes": [
                "This is a lightweight demo-quality report (single-pass scan).",
                "It highlights duplicates and extreme values that often break bordereaux ingestion.",
            ],
        }
    )