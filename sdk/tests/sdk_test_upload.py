from reinsight_sdk import Client

with Client("http://localhost:8000", "demo-key-123") as client:
    up = client.ingestion.upload_csv(portfolio_id=1, file_path="sample_bordereau.csv")
    print("upload:", up)

    st = client.ingestion.get_upload(up.upload_id)
    print("status:", st)

    pv = client.ingestion.preview(up.upload_id, rows=5)
    print("preview:", pv)