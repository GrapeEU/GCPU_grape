# 🍇 Grape

> Google Cloud University Hackathon 2025 · Knowledge-graph powered medical reasoning agent

---

![Grape cover](docs/grape_cover.png)

## Overview

Grape is an end‑to‑end demo of a graph‑centric AI assistant.  
The backend orchestrates deterministic scenarios over several RDF repositories, while the frontend streams MCP traces and renders the exact nodes/edges that powered each answer.

Out of the box we ship three knowledge graphs (`hearing`, `psychiatry`, `unified`) plus a small demo graph.  
All scenarios run without “hallucination” because they ground every answer in SPARQL results.

---

## Key capabilities

- **Scenario 1 – Neighbourhood Exploration**  
  Given a concept URI, retrieves nearby symptoms, interventions, risk factors, and tests.

- **Scenario 2 – Multi-hop Path Finding (Demo)**  
  Finds multi-hop paths (up to 3 hops) between Chronic Stress and Hearing Loss inside the unified graph and explains the link.

- **Scenario 3 – Federated Cross-KG Alignment (Demo)**  
  Surfaces deterministic owl:sameAs pairs between the hearing and psychiatry repositories.

- **Scenario 4 – Conversational Agent**  
  The `/api/agent/chat` endpoint leverages scenario detection, embeddings, MCP tools, and returns formatted traces that match the UI timeline.

- **MCP Tool suite** (`/api/mcp/*`)  
  - `extract_entities` → LLM/regex hybrid entity extractor  
  - `concepts` → FAISS semantic lookup over class descriptions (powered by Ollama `nomic-embed-text`)  
  - `neighbourhood` → Retrieves connected classes + caches turtle snippets  
  - `sparql` → Runs deterministic queries against the selected repository  
  - `interpret` → Summarises SPARQL results into human-readable explanations

- **Dynamic graph visualiser**  
  Next.js + `react-force-graph` component that colour-codes nodes by repository, shows execution traces, and fetches node ontology on demand.

---

## Architecture (high level)

```
┌──────────────┐   WebSockets & REST   ┌────────────────┐   SPARQL/HTTP   ┌─────────────┐
│ Next.js UI   ├──────────────────────▶│ FastAPI Backend├────────────────▶│ GraphDB KGs │
│ • Chat       │                       │ • Scenario core│                 │ hearing ... │
│ • Graph view │◀──────────────────────┤ • MCP tools    │                 └─────────────┘
└──────────────┘   JSON traces          └───────┬────────┘
                                               │
                                               │ Embedding lookups
                                               ▼
                                         Ollama (nomic-embed-text)
```

- **Frontend** (`apps/web`)  
  Next.js 14 + Tailwind, chat interface, graph visualiser, MCP timeline.

- **Backend** (`apps/backend`)  
  FastAPI with scenario orchestrator, MCP endpoints, FAISS embedding index, asynchronous SPARQL pipeline.

- **Knowledge store**  
  GraphDB 10.7 running four repositories: `demo`, `hearing`, `psychiatry`, `unified`.

- **Embeddings**  
  Generated via `scripts/generate_grape_embeddings.py`, stored under `apps/backend/gen2kgbot/data/...`.

---

## Installation

A detailed guide is available in **[docs/installation.md](docs/installation.md)**.  
It covers:

1. Cloning the repository and exporting `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS`, etc.
2. Starting the Docker stack (`docker compose up -d`) and verifying the services.
3. Loading TTL files into GraphDB (`make load-kg`).
4. Installing backend dependencies (`apps/backend/install.sh`) and regenerating embeddings via `uv run scripts/generate_grape_embeddings.py`.
5. Pulling the `nomic-embed-text` Ollama model (`docker compose exec ollama ollama pull nomic-embed-text`).

Use that document whenever you deploy to a new machine.

---

## Quick commands

```bash
# Start / stop services
make up
make down

# Load knowledge graphs into GraphDB
make load-kg

# Regenerate embeddings after KG updates
cd apps/backend
uv run scripts/generate_grape_embeddings.py

# Restart web container with a custom API host
export NEXT_PUBLIC_API_URL=http://34.155.101.97:8000
docker compose up -d --build web
```

Service URLs (default):  
Frontend → http://localhost:3000 • Backend → http://localhost:8000 • GraphDB → http://localhost:7200

---

## Repository layout

```
grape/
├── apps/
│   ├── backend/        # FastAPI backend, MCP tools, scenarios
│   └── web/            # Next.js frontend (chat + graph)
├── docs/
│   ├── installation.md # Deployment guide
│   └── grape_cover.png
├── kg_example/         # TTL files imported into GraphDB
├── scripts/
│   ├── create_repos.py
│   ├── setup_graphdb.sh
│   └── generate_grape_embeddings.py
├── docker-compose.yml
└── Makefile
```

---

## Contributing / Support

- Open issues for bug reports, deployment questions, or feature requests.
- PRs are welcome—especially new KG scenarios or MCP tool improvements.
- For internal hackathon teams, ping us on the shared Slack.

Enjoy exploring 🍇 Grape!
