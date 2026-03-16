from reinsight_sdk import Client

client = Client(base_url="http://localhost:8000", api_key="demo-key-123")

res = client.analytics.top_exposures(portfolio_id=1, by="tiv", limit=10)
print(res.count, res.by, res.limit)
print(res.items[0])

client.close()