# Reinsight - Exposure Intelligence for Reinsurance

Reinsight is a mini reinsurance intelligence platform that ingests messy exposure bordereaux, normalizes them into a canonical schema, computes portfolio analytics, and exposes everything through:
- A Django REST API
- A first-class Python SDK
- An agent/tool interface for LLM-ready integrations

It is designed as a demo platform inspired by real underwriting and reinsurance workflows: bordereaux ingestion, accumulation analysis, treaty-aware net calculations, stress scenarios, and data quality controls.

---

## What it does

### Ingestion
- Upload raw CSV bordereaux
- Preview uploaded files
- Suggest mapping from source columns to canonical exposure fields
- Apply mapping and normalize rows
- Bulk import normalized exposures
- Deduplicate repeated imports

### Analytics
- Accumulation / concentration by country, region, line of business, or peril
- Top exposures by TIV or premium
- Scenario stress testing
- Net-of-treaty analytics for:
  - Quota Share (QS)
  - Excess of Loss (XOL)

### Data quality
- Missing required fields
- Invalid values
- Duplicate detection
- Outlier detection
- Exposure distributions

### Developer layer
- Swagger / OpenAPI docs
- Python SDK with typed models and error handling
- Tool schema + tool execution endpoints
- Rules-based local agent runner

---

## Architecture

Backend:
- Django
- Django REST Framework
- PostgreSQL
- drf-spectacular (OpenAPI)

SDK:
- Python
- httpx
- Pydantic

Infra:
- Docker Compose

---

## Repository Structure
- reinsight/
- backend/ # Django API
- sdk/ # Python SDK
- demo/ # Demo scripts and agent runner
- sample_bordereau.csv
- docker-compose.yml
- README.md


---

## Quickstart

### 1. Start the stack

```bash
docker compose up --build
```

### 2. Health check
```bash
curl -H "X-API-Key: demo-key-123" http://localhost:8000/health/
```

### 3. Open Swagger
```bash
http://localhost:8000/docs/
```
Use Api Key 
```bash
demo-key-123
```

## Example Workflow (API)
### Upload a bordereau
```bash
curl -X POST \
  -H "X-API-Key: demo-key-123" \
  -F "file=@sample_bordereau.csv" \
  http://localhost:8000/v1/ingestion/uploads
```
### Suggest Mapping
```bash
curl -X POST \
  -H "X-API-Key: demo-key-123" \
  http://localhost:8000/v1/ingestion/uploads/<UPLOAD_ID>/suggest-mapping
```
### Apply Mapping
```bash
curl -X POST \
  -H "X-API-Key: demo-key-123" \
  -H "Content-Type: application/json" \
  --data-binary @mapping.json \
  "http://localhost:8000/v1/ingestion/uploads/<UPLOAD_ID>/apply-mapping?include_rows=true"
```
### Bulk import exposures
```bash
curl -X POST \
  -H "X-API-Key: demo-key-123" \
  -H "Content-Type: application/json" \
  --data-binary @bulk_payload.json \
  http://localhost:8000/v1/exposures/bulk
```

### Run Analytics
```bash
curl -H "X-API-Key: demo-key-123" \
  "http://localhost:8000/v1/analytics/accumulation?portfolio_id=1&group_by=country"
```

## Python SDK Example
```bash
from reinsight_sdk import Client

client = Client(base_url="http://localhost:8000", api_key="demo-key-123")

result = client.ingestion.ingest_csv(
    portfolio_id=1,
    file_path="sample_bordereau.csv",
    dedup_mode="composite",
)

print("Upload:", result.upload.upload_id)
print("Inserted rows:", result.bulk_result.inserted_rows)

acc = client.analytics.accumulation(
    portfolio_id=1,
    group_by="country"
)

print("Accumulation totals:", acc.totals)
```
## Tool Interface (Agent-Ready)
### Discover Tools
```bash
curl -H "X-API-Key: demo-key-123" \
  http://localhost:8000/v1/tools/schema
```
### Execute a tool
```bash
curl -X POST \
  -H "X-API-Key: demo-key-123" \
  -H "Content-Type: application/json" \
  -d '{"tool":"accumulation","input":{"portfolio_id":1,"group_by":"country"}}' \
  http://localhost:8000/v1/tools/execute
```
### Local Agent Runner
```bash
python demo/agent_runner.py "Show me the accumulation by country"
```

## Main API Endpoints
### Ingestion
- POST /v1/ingestion/uploads
- GET /v1/ingestion/uploads/{upload_id}
- GET /v1/ingestion/uploads/{upload_id}/preview
- POST /v1/ingestion/uploads/{upload_id}/suggest-mapping
- POST /v1/ingestion/uploads/{upload_id}/apply-mapping
### Exposures
- POST /v1/exposures/bulk
- GET /v1/exposures
- GET /v1/exposures/{id}
### Analytics
- GET /v1/analytics/accumulation
- GET /v1/analytics/top-exposures
- GET /v1/analytics/net
- POST /v1/analytics/scenario
### Data Quality
- GET /v1/portfolios/{portfolio_id}/data-quality
### Tools
- GET /v1/tools/schema
- POST /v1/tools/execute

## Notes
- API authentication uses the ***X-API-Key*** header
- Swagger docs available at ***/docs/***
- All responses include ***X-Request-ID*** header
- Demo API key: ***demo-key-123***

## Project Status
### Implemented:
- Full ingestion pipeline
- Analytics engine
- Treaty-aware calculations
- Data quality reporting
- Python SDK
- Tool execution layer
- Swagger documentation
### Optional future improvements:
- Analytics caching
- Rate limiting
- Extended automated testing
- Portfolio / cedant CRUD endpoints
