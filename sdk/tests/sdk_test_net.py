from reinsight_sdk import Client

client = Client(base_url="http://localhost:8000", api_key="demo-key-123")

res = client.analytics.net_of_treaty(portfolio_id=1, treaty_id=1, group_by="country")
print(res.totals)
print(res.buckets[0])

client.close()