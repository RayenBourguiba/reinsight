import respx
import httpx
from reinsight_sdk import Client

@respx.mock
def test_health_ok():
    base_url = "http://testserver"
    respx.get(f"{base_url}/health/").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    client = Client(base_url=base_url, api_key="demo-key-123")
    resp = client.health.get()
    assert resp.status == "ok"
    client.close()