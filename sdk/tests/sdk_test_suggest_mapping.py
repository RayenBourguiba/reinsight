from reinsight_sdk import Client

client = Client(base_url="http://localhost:8000", api_key="demo-key-123")

up = client.ingestion.upload_csv(portfolio_id=1, file_path="sample_bordereau.csv")
suggest = client.ingestion.suggest_mapping(up.upload_id)

print("missing_required_fields:", suggest.missing_required_fields)
print("mapping:", suggest.mapping)
print("first suggestion:", suggest.suggestions[0])