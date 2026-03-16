from reinsight_sdk import Client

BASE_URL = "http://localhost:8000"
API_KEY = "demo-key-123"

def main():
    with Client(BASE_URL, API_KEY) as client:
        up = client.ingestion.upload_csv(portfolio_id=1, file_path="sample_bordereau.csv")
        prev = client.ingestion.preview(up.upload_id, rows=5)

        print("preview model type:", type(prev))
        print("upload_id:", prev.upload_id)
        print("columns:", prev.columns)
        print("returned_rows:", prev.returned_rows)
        print("first row keys:", list(prev.preview_rows[0].keys()))

if __name__ == "__main__":
    main()