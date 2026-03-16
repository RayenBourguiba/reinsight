from reinsight_sdk import Client

BASE_URL = "http://localhost:8000"
API_KEY = "demo-key-123"

mapping = {
    "policy_id": "PolicyNumber",
    "lob": "LOB",
    "peril": "PerilType",
    "country": "CountryCode",
    "region": "Region",
    "tiv": "TIV_USD",
    "premium": "Premium_USD",
    "lat": "Latitude",
    "lon": "Longitude",
    "inception_date": "InceptionDate",
    "expiry_date": "ExpiryDate",
}

with Client(base_url=BASE_URL, api_key=API_KEY) as client:
    upload = client.ingestion.upload_csv(portfolio_id=1, file_path="sample_bordereau.csv")
    print("upload:", upload)

    prev = client.ingestion.preview(upload.upload_id, rows=5)
    print("preview columns:", prev["columns"])

    applied = client.ingestion.apply_mapping(upload.upload_id, mapping=mapping)
    canonical_rows = applied.canonical_rows()
    print("mapped rows:", len(canonical_rows))
    print("first mapped row keys:", list(canonical_rows[0].keys()))

    bulk = client.exposures.bulk_create(portfolio_id=1, rows=canonical_rows, dedup_mode="composite")
    print("bulk:", bulk)