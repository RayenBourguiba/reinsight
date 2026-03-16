from reinsight_sdk import Client

BASE_URL = "http://localhost:8000"
API_KEY = "demo-key-123"

with Client(BASE_URL, API_KEY) as client:
    # 1) upload
    up = client.ingestion.upload_csv(portfolio_id=1, file_path="sample_bordereau.csv")
    print("upload:", up)

    # 2) suggest mapping
    sm = client.ingestion.suggest_mapping(up.upload_id)
    print("mapping keys:", list(sm.mapping.keys()))

    # 3) apply mapping with full rows
    am = client.ingestion.apply_mapping(
        up.upload_id,
        mapping=sm.mapping,
        options={"max_rows": 50, "preview_rows": 5, "include_rows": True},
    )
    rows = am.normalized_rows or []
    print("rows len:", len(rows))

    # 4) bulk create
    bulk = client.exposures.bulk_create(
        portfolio_id=1,
        rows=rows,
        dedup_mode="composite",
    )
    print("bulk:", bulk)