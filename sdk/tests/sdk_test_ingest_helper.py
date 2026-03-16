from reinsight_sdk import Client

client = Client(base_url="http://localhost:8000", api_key="demo-key-123")

res = client.ingestion.ingest_csv(
    portfolio_id=1,
    file_path="sample_bordereau.csv",
    dedup_mode="composite",
)

print("upload_id:", res.upload.upload_id)
print("missing_required_fields:", res.suggested_mapping.missing_required_fields)
print("normalized_rows:", len(res.applied_mapping.normalized_rows or []))
print("inserted_rows:", res.bulk_result.inserted_rows)
print("skipped_duplicates:", res.bulk_result.skipped_duplicates)

client.close()