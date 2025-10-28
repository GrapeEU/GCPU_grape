# Installation Guide

This document explains how to deploy the Grape stack (GraphDB + FastAPI backend + Next.js frontend) on a fresh machine or VM.

> **Dependencies**
>
> - Docker ≥ 24 and Docker Compose
> - Make (optional but used in the commands below)
> - `uv` (optional — makes it easier to run Python scripts without activating the venv manually)

---

## 1. Clone the repository

```bash
git clone https://github.com/<your-org>/GCPU_grape.git
cd GCPU_grape
```

---

## 2. Prepare environment variables

1. Copy the backend template and edit it with real keys:
   ```bash
   cp apps/backend/.env.example apps/backend/.env
   ```
   Minimum values to update:
   - `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) if you plan to call Gemini.
   - `CORS_ORIGINS` — add every domain that will load the frontend (e.g. `http://localhost:3000,http://34.155.101.97:3000`).

2. Configure the frontend API host. Either export it before running Docker:
   ```bash
   export NEXT_PUBLIC_API_URL=http://34.155.101.97:8000
   ```
   or provide it via `.env` in `apps/web/.env`. The Docker compose file falls back to `http://localhost:8000` if you leave it unset.

---

## 3. Start Docker services

```bash
docker compose up -d
# or: make up
```

Verify containers:

```bash
make status
```

You should see `grape-graphdb`, `grape-api`, `grape-web`, and `grape-ollama` running.

---

## 4. Create GraphDB repositories and import TTL files

```bash
make load-kg
```

This command:
1. Creates four repositories (`demo`, `hearing`, `psychiatry`, `unified`) via `scripts/create_repos.py`.
2. Loads the sample TTL files (`kg_example/final_demo/*.ttl`) using `scripts/setup_graphdb.sh`.

You can confirm at http://localhost:7200 or by running:

```bash
curl -X POST -H "Content-Type: application/sparql-query" \
     --data 'SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o }' \
     http://localhost:7200/repositories/unified
```

---

## 5. Install backend dependencies (first-time only)

Inside `apps/backend` run:

```bash
cd apps/backend
./install.sh
```

This script creates a Python virtual environment at `apps/backend/.venv` and installs required packages (FastAPI, FAISS, LangChain, etc.).

Activate it when running scripts manually:

```bash
source .venv/bin/activate
```

If you are using `uv`, you can skip activation and run commands with `uv run ...`.

---

## 6. Ensure Ollama has the embedding model

The embeddings generation pipeline relies on `nomic-embed-text`. Pull it inside the Ollama container:

```bash
docker compose exec ollama ollama pull nomic-embed-text
```

You only need to do this once per machine.

---

## 7. Generate FAISS embeddings for each KG

From the project root (or from `apps/backend`):

```bash
uv run scripts/generate_grape_embeddings.py
# or
python scripts/generate_grape_embeddings.py
```

The script checks:
- GraphDB connectivity
- Ollama availability (and that `nomic-embed-text` is pulled)
- Required FAISS dependencies

When successful you will see:

```
✅ SUCCESS: grape_demo
✅ SUCCESS: grape_hearing
✅ SUCCESS: grape_psychiatry
✅ SUCCESS: grape_unified
```

Embeddings are stored under:
```
apps/backend/gen2kgbot/data/<kg>/faiss_embeddings/classes_with_instance_nomic/
```

Run the script again whenever you update the TTL data.

---

## 8. Optional checks

```bash
# Test SPARQL endpoints defined in scripts/test_sparql.py
python scripts/test_sparql.py

# Test MCP / embeddings integration
uv run scripts/test_gen2kgbot_integration.py
```

---

## 9. Access the stack

- Frontend: http://localhost:3000 (or your public IP if deployed)
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- GraphDB Workbench: http://localhost:7200

If you exposed the frontend publicly, make sure:
- `CORS_ORIGINS` (backend `.env`) includes the frontend origin.
- `NEXT_PUBLIC_API_URL` points to the publicly reachable backend URL.

---

## 10. Common restart commands

```bash
docker compose down
docker compose up -d --build

# Restart only the web container with a new API host
export NEXT_PUBLIC_API_URL=http://34.155.101.97:8000
docker compose up -d --build web

# Re-import TTL data if GraphDB volumes were cleared
make load-kg

# Regenerate embeddings after KG changes
uv run scripts/generate_grape_embeddings.py
```

---

That’s it! The stack is ready.  
Hit http://localhost:3000 (or your deployed domain) to start chatting with the agent and visualising the results.  
For troubleshooting tips, check the individual service logs:

```bash
docker logs -f grape-api
docker logs -f grape-web
docker logs -f grape-graphdb
docker logs -f grape-ollama
```
