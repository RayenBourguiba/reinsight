from reinsight_sdk import Client
from reinsight_sdk.models import ScenarioRequest, ScenarioStress, ScenarioFilters

client = Client(base_url="http://localhost:8000", api_key="demo-key-123")

req = ScenarioRequest(
    portfolio_id=1,
    treaty_id=2,
    group_by="country",
    stresses=[
        ScenarioStress(
            name="FR Flood +20%",
            filters=ScenarioFilters(country="FR", peril="FLOOD"),
            tiv_factor=1.2,
        ),
        ScenarioStress(
            name="DE Wind +10%",
            filters=ScenarioFilters(country="DE", peril="WIND"),
            tiv_factor=1.1,
        ),
    ],
)

res = client.analytics.scenario(req)
print(res.baseline)
print(res.stressed)
print(res.delta)
if res.buckets:
    print("baseline FR bucket:", [b for b in res.buckets.baseline if b.key == "FR"][0])

client.close()