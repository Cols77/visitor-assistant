# TourAssist

TourAssist is a multi-tenant, text-based AI tourist assistant with tenant-scoped RAG, evaluation harness, and observability.

## Quick start

```bash
cd tourassist
make install
make run
```

### Create a tenant

```bash
curl -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "demo"}'
```

### Ingest a demo document

```bash
curl -X POST http://localhost:8000/ingest \
  -H "X-API-Key: <api_key>" \
  -F tenant_id=demo \
  -F file=@data/demo/spa.md
```

### Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api_key>" \
  -d '{"tenant_id": "demo", "session_id": "session-1", "user_message": "What time does the spa open on Sundays?"}'
```

### Run evaluation

```bash
make eval
```

## Docker

```bash
docker-compose up --build
```
