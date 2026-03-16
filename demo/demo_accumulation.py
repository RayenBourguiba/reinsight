from reinsight_sdk import Client

def main():
    with Client("http://localhost:8000", "demo-key-123") as client:
        response = client.analytics.accumulation(
            portfolio_id=1,
            peril="FLOOD",
            country="FR",
            group_by="region",
        )

        print("Totals:")
        print(response.totals)

        print("\nBuckets:")
        for bucket in response.buckets:
            print(bucket)

if __name__ == "__main__":
    main()