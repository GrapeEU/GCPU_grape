# Installation (Simple & Clear)

> Goal: run GraphDB, the FastAPI backend, and the Next.js frontend; load the unified demo KG and generate embeddings. Keep it simple.

---

## 0) Prerequisites

- Docker & Docker Compose
- Python 3.12, `uv` (optional, recommended)
- (Optional) Ollama installed locally for embeddings (`nomic-embed-text`)

---

## 1) Clone the repo

```bash
git clone https://github.com/<your-org>/GCPU_grape.git
cd GCPU_grape
```

---

## 2) Configure environments

- Backend env:
  ```bash
  cp apps/backend/.env.example apps/backend/.env
  ```
  Edit `apps/backend/.env` and set your keys:
  - `GCP_PROJECT_ID="your-id"`
  - `VERTEX_AI_LOCATION=us-central1`
  - Ensure `CORS_ORIGINS` includes your frontend origin.
  If you need our cloud values for a staged demo, contact us.

- Frontend env (only if backend isn’t on localhost):
  ```bash
  echo "NEXT_PUBLIC_API_URL=http://<backend-host>:8000" > apps/web/.env
  ```

---


## 2.5 Easy installation

you can install all the project by simply run :
```bash
make run
```
This will: start the stack, load the demo KG into `unified`, pull `nomic-embed-text`, generate embeddings, and show URLs.

you can setup manually or if there are any problems by following the steps below.


## 3) Start GraphDB

```bash
docker-compose -f docker-compose.graphdb.yml up -d
```
GraphDB UI: http://localhost:7200

---

## 4) Install backend (venv + deps)

```bash
cd apps/backend
./install.sh
# the script prints the next steps
```

---

## 5) Load the unified demo KG

From the repo root:
```bash
bash scripts/refresh_unified_demo.sh
```
This clears and reloads the demo TTLs into the `unified` repository.

Quick sanity check:
```bash
curl -G -H 'Accept: application/sparql-results+json' \
  --data-urlencode 'query=SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5' \
  http://localhost:7200/repositories/unified
```

---

## 6) Embeddings (Ollama)

Pull the model once if not present:
```bash
ollama pull nomic-embed-text
```
Generate embeddings for the unified KG:
```bash
python scripts/generate_grape_embeddings.py unified
```
(Checks GraphDB connectivity and Ollama availability.)

---

## 7) Run the backend API

```bash
cd apps/backend
source .venv/bin/activate
python main.py
```
API: http://localhost:8000 • Docs: http://localhost:8000/docs

---

## 8) Run the frontend

If not containerised:
```bash
cd apps/web
# ensure NEXT_PUBLIC_API_URL is correct in apps/web/.env
npm install
npm run dev
```
Frontend: http://localhost:3000


---

## Quick checklist

- [ ] GraphDB up on http://localhost:7200
- [ ] `bash scripts/refresh_unified_demo.sh` completed
- [ ] `ollama pull nomic-embed-text` done
- [ ] `python scripts/generate_grape_embeddings.py unified` successful
- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:3000 (or your domain)

---

## Troubleshooting

- GraphDB says “Missing parameter: query” → use `curl -G --data-urlencode 'query=…'` as shown.
- Frontend can’t reach backend → set `NEXT_PUBLIC_API_URL` to the reachable backend URL.
- Embeddings script fails → check that GraphDB `unified` has data and that the Ollama model was pulled.
- Logs:
  ```bash
  docker logs -f grape-api
  docker logs -f grape-graphdb
  docker logs -f grape-web
  docker logs -f grape-ollama
  ```
