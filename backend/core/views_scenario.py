from decimal import Decimal
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from core.models import Exposure, Portfolio, Treaty

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from core.serializers import ScenarioRequestSerializer, ScenarioResponseSerializer

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


def _compute_ceded(treaty: Treaty | None, tiv: Decimal) -> Decimal:
    if treaty is None:
        return Decimal("0")

    if treaty.treaty_type == Treaty.QS:
        share = Decimal(treaty.ceded_share_pct) / Decimal("100")
        return tiv * share

    # XOL
    att = Decimal(treaty.attachment)
    lim = Decimal(treaty.limit)
    return _clamp(tiv - att, Decimal("0"), lim)

@extend_schema(
    tags=["Analytics"],
    operation_id="analytics_scenario_stress",
    summary="Run a stress scenario",
    description=(
        "Apply one or more stress assumptions to portfolio exposures and compare "
        "baseline vs stressed values. Optionally applies treaty logic to compute "
        "gross, ceded, and net stressed results."
    ),
    request=ScenarioRequestSerializer,
    examples=[
        OpenApiExample(
            "Simple flood stress example",
            request_only=True,
            value={
                "portfolio_id": 1,
                "treaty_id": 1,
                "group_by": "country",
                "stresses": [
                    {
                        "name": "France Flood +20%",
                        "filters": {
                            "country": "FR",
                            "peril": "FLOOD"
                        },
                        "tiv_factor": 1.2
                    }
                ]
            },
        )
    ],
    responses={
        200: OpenApiResponse(
            response=ScenarioResponseSerializer,
            description="Scenario stress computed successfully.",
        ),
        400: OpenApiResponse(description="Invalid request payload."),
        404: OpenApiResponse(description="Portfolio or treaty not found."),
    },
)
@api_view(["POST"])
def scenario_stress(request):
    """
    POST /v1/analytics/scenario

    Body:
      {
        "portfolio_id": 1,
        "treaty_id": 1,               # optional
        "base_filters": {             # optional
          "country": "FR",
          "lob": "PROPERTY",
          "peril": "FLOOD"
        },
        "stresses": [
          {
            "name": "FR Flood +20%",
            "filters": {"country":"FR","peril":"FLOOD"},
            "tiv_factor": 1.2
          }
        ],
        "group_by": "country"         # optional: country|region|lob|peril
      }
    """
    body = request.data or {}

    portfolio_id = body.get("portfolio_id")
    if not portfolio_id:
        return _bad_request("portfolio_id is required")

    treaty_id = body.get("treaty_id")
    base_filters = body.get("base_filters") or {}
    stresses = body.get("stresses") or []
    group_by = body.get("group_by")

    if not isinstance(stresses, list) or len(stresses) == 0:
        return _bad_request("stresses must be a non-empty list")

    allowed_group = {None, "", "country", "region", "lob", "peril"}
    if group_by not in allowed_group:
        return _bad_request("Invalid group_by", {"allowed": ["country", "region", "lob", "peril"]})

    try:
        portfolio = Portfolio.objects.get(id=int(portfolio_id))
    except Portfolio.DoesNotExist:
        return Response(
            {"error": {"code": "not_found", "message": "Portfolio not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    treaty = None
    if treaty_id is not None:
        try:
            treaty = Treaty.objects.get(id=int(treaty_id), portfolio=portfolio)
        except Treaty.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Treaty not found for this portfolio"}},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Validate treaty params
        if treaty.treaty_type == Treaty.QS and treaty.ceded_share_pct is None:
            return _bad_request("QS treaty requires ceded_share_pct")
        if treaty.treaty_type == Treaty.XOL and (treaty.attachment is None or treaty.limit is None):
            return _bad_request("XOL treaty requires attachment and limit")

    # Base queryset + base filters
    qs = Exposure.objects.filter(portfolio=portfolio)

    def _apply_filters(qs_in, f: dict):
        if not isinstance(f, dict):
            return qs_in
        if f.get("country"):
            qs_in = qs_in.filter(country=str(f["country"]).strip().upper())
        if f.get("lob"):
            qs_in = qs_in.filter(lob=str(f["lob"]).strip().upper())
        if f.get("peril"):
            qs_in = qs_in.filter(peril=str(f["peril"]).strip().upper())
        if f.get("region"):
            qs_in = qs_in.filter(region=str(f["region"]).strip())
        return qs_in

    qs = _apply_filters(qs, base_filters)

    # Pre-compile stress rules
    rules = []
    for s in stresses:
        if not isinstance(s, dict):
            return _bad_request("Each stress must be an object")
        name = s.get("name") or "stress"
        tiv_factor = s.get("tiv_factor")
        if tiv_factor is None:
            return _bad_request("Each stress must include tiv_factor")
        try:
            tiv_factor = Decimal(str(tiv_factor))
        except Exception:
            return _bad_request("Invalid tiv_factor", {"value": tiv_factor})
        if tiv_factor <= 0:
            return _bad_request("tiv_factor must be > 0")

        rules.append(
            {
                "name": name,
                "filters": s.get("filters") or {},
                "tiv_factor": tiv_factor,
            }
        )

    # helper: does exposure match rule filters?
    def _matches(exposure, f: dict) -> bool:
        if not f:
            return True
        if f.get("country") and exposure.country != str(f["country"]).strip().upper():
            return False
        if f.get("lob") and exposure.lob != str(f["lob"]).strip().upper():
            return False
        if f.get("peril") and exposure.peril != str(f["peril"]).strip().upper():
            return False
        if f.get("region") and getattr(exposure, "region", "") != str(f["region"]).strip():
            return False
        return True

    # Totals + optional grouping
    base = {"count": 0, "gross_tiv": Decimal("0"), "ceded_tiv": Decimal("0"), "net_tiv": Decimal("0")}
    stressed = {"count": 0, "gross_tiv": Decimal("0"), "ceded_tiv": Decimal("0"), "net_tiv": Decimal("0")}

    buckets_base = {}
    buckets_stressed = {}

    for e in qs.iterator():
        base_tiv = Decimal(e.tiv)
        stressed_tiv = base_tiv

        # Apply all matching stress factors multiplicatively
        applied = []
        for rule in rules:
            if _matches(e, rule["filters"]):
                stressed_tiv = stressed_tiv * rule["tiv_factor"]
                applied.append(rule["name"])

        # Base net-of-treaty
        base_ceded = _compute_ceded(treaty, base_tiv)
        base_net = base_tiv - base_ceded

        # Stressed net-of-treaty
        stressed_ceded = _compute_ceded(treaty, stressed_tiv)
        stressed_net = stressed_tiv - stressed_ceded

        base["count"] += 1
        base["gross_tiv"] += base_tiv
        base["ceded_tiv"] += base_ceded
        base["net_tiv"] += base_net

        stressed["count"] += 1
        stressed["gross_tiv"] += stressed_tiv
        stressed["ceded_tiv"] += stressed_ceded
        stressed["net_tiv"] += stressed_net

        if group_by:
            key = getattr(e, group_by) or "UNKNOWN"

            if key not in buckets_base:
                buckets_base[key] = {"key": key, "count": 0, "gross_tiv": Decimal("0"), "ceded_tiv": Decimal("0"), "net_tiv": Decimal("0")}
                buckets_stressed[key] = {"key": key, "count": 0, "gross_tiv": Decimal("0"), "ceded_tiv": Decimal("0"), "net_tiv": Decimal("0")}

            buckets_base[key]["count"] += 1
            buckets_base[key]["gross_tiv"] += base_tiv
            buckets_base[key]["ceded_tiv"] += base_ceded
            buckets_base[key]["net_tiv"] += base_net

            buckets_stressed[key]["count"] += 1
            buckets_stressed[key]["gross_tiv"] += stressed_tiv
            buckets_stressed[key]["ceded_tiv"] += stressed_ceded
            buckets_stressed[key]["net_tiv"] += stressed_net

    def _fmt_totals(d: dict):
        gross = d["gross_tiv"]
        ceded = d["ceded_tiv"]
        net = d["net_tiv"]
        return {
            "count": d["count"],
            "gross_tiv": float(gross),
            "ceded_tiv": float(ceded),
            "net_tiv": float(net),
            "ceded_pct": round((float(ceded) / float(gross) * 100.0), 2) if gross else 0.0,
        }

    def _delta(a: Decimal, b: Decimal):
        # b - a
        diff = b - a
        pct = (diff / a * Decimal("100")) if a else Decimal("0")
        return float(diff), float(pct)

    delta_gross, delta_gross_pct = _delta(base["gross_tiv"], stressed["gross_tiv"])
    delta_net, delta_net_pct = _delta(base["net_tiv"], stressed["net_tiv"])

    out = {
        "portfolio_id": portfolio.id,
        "treaty": (
            {
                "id": treaty.id,
                "name": treaty.name,
                "treaty_type": treaty.treaty_type,
                "ceded_share_pct": float(treaty.ceded_share_pct) if treaty.ceded_share_pct is not None else None,
                "attachment": float(treaty.attachment) if treaty.attachment is not None else None,
                "limit": float(treaty.limit) if treaty.limit is not None else None,
            }
            if treaty
            else None
        ),
        "base_filters": base_filters,
        "stresses": [{"name": r["name"], "filters": r["filters"], "tiv_factor": float(r["tiv_factor"])} for r in rules],
        "group_by": group_by or None,
        "baseline": _fmt_totals(base),
        "stressed": _fmt_totals(stressed),
        "delta": {
            "gross_tiv": delta_gross,
            "gross_tiv_pct": round(delta_gross_pct, 2),
            "net_tiv": delta_net,
            "net_tiv_pct": round(delta_net_pct, 2),
        },
    }

    if group_by:
        bl = []
        st = []
        for key in buckets_base.keys():
            b = buckets_base[key]
            s = buckets_stressed[key]

            bl.append(
                {
                    "key": key,
                    "count": b["count"],
                    "gross_tiv": float(b["gross_tiv"]),
                    "ceded_tiv": float(b["ceded_tiv"]),
                    "net_tiv": float(b["net_tiv"]),
                }
            )
            st.append(
                {
                    "key": key,
                    "count": s["count"],
                    "gross_tiv": float(s["gross_tiv"]),
                    "ceded_tiv": float(s["ceded_tiv"]),
                    "net_tiv": float(s["net_tiv"]),
                }
            )

        bl.sort(key=lambda x: x["gross_tiv"], reverse=True)
        st.sort(key=lambda x: x["gross_tiv"], reverse=True)

        out["buckets"] = {"baseline": bl, "stressed": st}

    return Response(out)