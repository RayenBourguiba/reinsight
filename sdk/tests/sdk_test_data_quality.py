from reinsight_sdk import Client

client = Client(base_url="http://localhost:8000", api_key="demo-key-123")

dq = client.portfolios.data_quality(1)

print("portfolio_id:", dq.portfolio_id)
print("exposures:", dq.totals.exposures)
print("missing tiv %:", dq.missing_required.pct.tiv)
print("duplicates empty_policy_id:", dq.duplicates.empty_policy_id)
print("top tiv first:", dq.outliers.top_tiv[0] if dq.outliers.top_tiv else None)

client.close()