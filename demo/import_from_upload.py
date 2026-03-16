import argparse
import json
import sys
import requests

BULK_ALLOWED_KEYS = {
    "lob",
    "peril",
    "country",
    "tiv",
    "region",
    "premium",
    "policy_id",
    "location_id",
    "lat",
    "lon",
    "inception_date",
    "expiry_date",
}

def strip_row(row: dict) -> dict:
    return {k: row.get(k) for k in BULK_ALLOWED_KEYS if k in row}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--api-key", default="demo-key-123")
    p.add_argument("--upload-id", required=True)
    p.add_argument("--portfolio-id", required=True, type=int)
    p.add_argument("--mapping-file", default="mapping.json")
    args = p.parse_args()

    with open(args.mapping_file, "r", encoding="utf-8") as f:
        mapping_body = json.load(f)

    apply_url = f"{args.base_url}/v1/ingestion/uploads/{args.upload_id}/apply-mapping?include_rows=true"
    r = requests.post(
        apply_url,
        headers={"X-API-Key": args.api_key, "Content-Type": "application/json"},
        json=mapping_body,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()

    rows = data.get("normalized_rows")
    if not isinstance(rows, list) or not rows:
        print("No normalized_rows returned from apply-mapping", file=sys.stderr)
        print(json.dumps(data, indent=2), file=sys.stderr)
        sys.exit(1)

    cleaned_rows = [strip_row(row) for row in rows]

    bulk_url = f"{args.base_url}/v1/exposures/bulk"
    payload = {
        "portfolio_id": args.portfolio_id,
        "rows": cleaned_rows,
        "batch_size": 1000,
        "max_errors": 200,
    }

    r2 = requests.post(
        bulk_url,
        headers={"X-API-Key": args.api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    r2.raise_for_status()

    print("Bulk import response:")
    print(json.dumps(r2.json(), indent=2))

if __name__ == "__main__":
    main()