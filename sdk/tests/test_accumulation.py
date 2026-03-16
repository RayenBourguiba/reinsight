import respx
import httpx

from reinsight_sdk import Client

@respx.mock
def test_accumulation_parses_response():
    base_url = "http://testserver"
    route = respx.get(f"{base_url}/v1/analytics/accumulation").mock(
        return_value=httpx.Response(
            200,
            json={
                "portfolio_id": 1,
                "group_by": "region",
                "filters": {"peril": "FLOOD", "country": "FR"},
                "totals": {"count": 3, "total_tiv": 1000.0},
                "buckets": [
                    {"key": "IDF", "count": 2, "tiv": 700.0, "share_pct": 70.0},
                    {"key": "NAQ", "count": 1, "tiv": 300.0, "share_pct": 30.0},
                ],
            },
        )
    )

    client = Client(base_url=base_url, api_key="demo-key-123")
    resp = client.analytics.accumulation(portfolio_id=1, group_by="region", peril="FLOOD", country="FR")

    assert resp.portfolio_id == 1
    assert resp.group_by == "region"
    assert resp.totals.count == 3
    assert resp.totals.total_tiv == 1000.0
    assert resp.buckets[0].key == "IDF"
    assert route.called
    client.close()


@respx.mock
def test_accumulation_raises_on_auth_error():
    base_url = "http://testserver"
    respx.get(f"{base_url}/v1/analytics/accumulation").mock(
        return_value=httpx.Response(
            401,
            json={"error": {"code": "auth", "message": "Invalid API key"}}
        )
    )

    client = Client(base_url=base_url, api_key="bad")
    try:
        client.analytics.accumulation(portfolio_id=1)
        assert False, "Expected auth error"
    except Exception as e:
        assert "Invalid API key" in str(e)
    finally:
        client.close()