from reinsight_sdk import Client

BASE_URL = "http://localhost:8000"
API_KEY = "demo-key-123"

with Client(BASE_URL, API_KEY) as client:
    up = client.ingestion.upload_csv(portfolio_id=1, file_path="sample_bordereau.csv")
    print("upload:", up)

    sm = client.ingestion.suggest_mapping(up.upload_id)
    print("missing_required_fields:", sm.missing_required_fields)
    print("mapping keys:", list(sm.mapping.keys()))

    am = client.ingestion.apply_mapping(
        up.upload_id,
        mapping=sm.mapping,
        options={"max_rows": 50, "preview_rows": 5, "include_rows": True},
    )

    print("apply mapping stats:", am.stats)
    print("preview len:", len(am.normalized_preview))
    print("rows type:", type(am.normalized_rows))
    print("rows len:", len(am.normalized_rows or []))
    print("first row keys:", list((am.normalized_rows or am.normalized_preview)[0].keys()))