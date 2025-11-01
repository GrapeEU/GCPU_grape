# Grape Backend

> **AI-Powered Knowledge Graph Querying Platform**
> FastAPI backend with MCP tools for natural language to SPARQL conversion, powered by gen2kgbot.

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

Grape Backend is a production-ready FastAPI server that enables **natural language querying** of medical knowledge graphs through an intelligent agent architecture. It combines:

- **6 Validated MCP Tools** - Reusable building blocks for KG operations
- **4 Core Scenarios** - LLM-orchestrated workflows via prompts
- **gen2kgbot Integration** - Proven NL2SPARQL engine with validated components
- **Universal RDF Support** - Works with any RDF/OWL knowledge graph

### What Can It Do?

- **Explore neighbourhoods**: "What are the symptoms and treatments for Tinnitus?"
- **Find hidden paths**: "How is Tinnitus related to Anxiety?"
- **Cross-KG alignment**: "What concepts are shared between hearing and psychiatry graphs?"
- **Validate assertions**: "Is it true that HearingLoss requires CBT therapy?"
- **Semantic search**: Find concepts using embeddings (96 medical concepts indexed)

### Architecture

```
User Question (Natural Language)
         ↓
    LLM Agent (Gemini)
         ↓
  Reads Scenario Prompts ──→ Decides which MCP tools to call
         ↓
    MCP Tools (6 validated)
         ↓
    gen2kgbot Components ──→ SPARQL Execution
         ↓                        ↓
    GraphDB Repositories    Results (CSV)
         ↓                        ↓
    Interpretation (LLM) ←───────┘
         ↓
  Structured Response
  (text + nodes + links for viz)
```

**Key principle**: Gemini still chooses the scenario and MCP sequence, while deterministic SPARQL templates keep each call aligned with the intended ontology constraints.

---

## Features

### 🧠 4 Core Scenarios (LLM-Orchestrated)

Each scenario is defined as a **system prompt** that guides the LLM on which MCP tools to call:

1. **Neighbourhood Exploration** - Explore relationships around a concept (symptoms, treatments, risk factors)
2. **Multi-Hop Path Finding** - Find connections between two concepts through intermediate nodes
3. **Federated Cross-KG Alignment** - Discover alignments between different medical domains (owl:sameAs)
4. **Assertion Validation & Proof** - Validate medical claims with evidence from the KG

See [prompts/](prompts/) for detailed scenario prompts.

### 🔧 6 Validated MCP Tools

Each tool is a tested gen2kgbot component exposed as an HTTP endpoint:

| MCP Tool | Purpose | gen2kgbot Component |
|----------|---------|---------------------|
| **`/mcp/extract_entities`** | Extract medical entities using LLM | `ChatGoogleGenerativeAI` |
| **`/mcp/concepts`** | Find similar concepts via embeddings | `graph_nodes.select_similar_classes` |
| **`/mcp/neighbourhood`** | Retrieve connected concepts | `construct_util.get_connected_classes` |
| **`/mcp/sparql`** | Execute SPARQL queries | `sparql_toolkit.run_sparql_query` |
| **`/mcp/interpret`** | Convert CSV results to natural language | `graph_nodes.interpret_results` |
| **`/mcp/configure`** | Switch between knowledge graphs | `config_manager` |

**Test coverage**: Offline template assertions live in [`tests/test_agent_templates.py`](tests/test_agent_templates.py)

### 🌐 API Endpoints

- `GET /` - API information
- `GET /api/health` - Health check with GraphDB connectivity
- `POST /api/mcp/sparql` - Execute SPARQL queries
- `POST /api/mcp/concepts` - Semantic concept search
- `POST /api/mcp/neighbourhood` - Neighbourhood retrieval
- `POST /api/mcp/interpret` - Result interpretation
- `POST /api/mcp/extract_entities` - Entity extraction
- `POST /api/mcp/configure` - KG configuration
- `GET /api/mcp/tools` - List all available MCP tools
- `GET /docs` - Interactive API documentation (Swagger UI)

---

## Quick Start

### Prerequisites

- **Python 3.12**
- **uv** package manager ([install guide](https://github.com/astral-sh/uv))
- **GraphDB** or compatible SPARQL endpoint running on `localhost:7200`
- **Ollama** with `nomic-embed-text` model (for embeddings)

### Installation

```bash
cd apps/backend

# Run automated installation
./install.sh
```

This script will:
- ✓ Install `uv` if not present
- ✓ Create a Python 3.12 virtual environment
- ✓ Install all dependencies from `requirements.txt`
- ✓ Download Spacy models (`en_core_web_sm`, `en_core_web_lg`)
- ✓ Create `.env` from template

### Configuration

```bash
# Create .env from template
cp .env.example .env

# Edit with your credentials
nano .env
```

**Essential variables:**

```bash
# Google API (for Gemini LLM)
GOOGLE_API_KEY=your-google-api-key

# GraphDB SPARQL endpoint
KG_SPARQL_ENDPOINT_URL=http://localhost:7200/repositories/hearing

# Optional: Ollama endpoint for embeddings
OLLAMA_BASE_URL=http://localhost:11434
```

### Generate Embeddings (One-Time Setup)

```bash
# Start GraphDB first
docker-compose -f ../../docker-compose.graphdb.yml up -d

# Generate embeddings for all 4 medical KGs
apps/backend/.venv/bin/python scripts/generate_grape_embeddings.py
```

This will create FAISS embeddings for:
- `grape_demo` (20 concepts)
- `grape_hearing` (22 concepts)
- `grape_psychiatry` (21 concepts)
- `grape_unified` (33 concepts)

**Total**: 96 medical concepts indexed for semantic search.

### Running the Server

```bash
# Method 1: Using Python (recommended)
python main.py

# Method 2: With venv activated
source .venv/bin/activate
uvicorn main:app --reload
```

The API will be available at:
- **Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **MCP Tools List**: http://localhost:8000/api/mcp/tools

---

## Usage Examples

### Example 1: Semantic Concept Search

```bash
curl -X POST "http://localhost:8000/api/mcp/concepts" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Tinnitus",
    "kg_name": "grape_hearing",
    "limit": 5
  }'
```

**Response:**
```json
{
  "concepts": [
    {
      "uri": "http://example.org/hearing/Tinnitus",
      "label": "Tinnitus",
      "description": "Ringing in the ears"
    },
    {
      "uri": "http://example.org/hearing/Hyperacusis",
      "label": "Hyperacusis",
      "description": "Sensitivity to loud sounds"
    }
  ],
  "count": 2,
  "query": "Tinnitus",
  "kg": "grape_hearing"
}
```

### Example 2: SPARQL Query Execution

```bash
curl -X POST "http://localhost:8000/api/mcp/sparql" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
    "kg_name": "grape_hearing"
  }'
```

### Example 3: Neighbourhood Exploration

```bash
curl -X POST "http://localhost:8000/api/mcp/neighbourhood" \
  -H "Content-Type: application/json" \
  -d '{
    "concept_uris": ["http://example.org/hearing/Tinnitus"],
    "kg_name": "grape_hearing"
  }'
```

### Example 4: Entity Extraction (LLM-based)

```bash
curl -X POST "http://localhost:8000/api/mcp/extract_entities" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the symptoms and treatments for Tinnitus?",
    "kg_name": "grape_hearing"
  }'
```

**Response:**
```json
{
  "entities": ["Tinnitus", "symptoms", "treatments"],
  "count": 3,
  "question": "What are the symptoms and treatments for Tinnitus?",
  "kg": "grape_hearing"
}
```

---

## Project Structure

```
apps/backend/
├── api/                         # FastAPI application
│   ├── mcp.py                   # MCP tools router (6 validated tools)
│   ├── agent.py                 # Main LLM agent (Gemini-based)
│   └── server.py                # FastAPI instance
│
├── core/                        # Core business logic
│   └── config.py                # Application settings (Pydantic)
│
├── models/                      # Pydantic data models
│   ├── requests.py              # API request schemas
│   └── responses.py             # API response schemas
│
├── prompts/                     # Scenario prompts for LLM orchestration
│   ├── scenario_1_neighbourhood.json
│   ├── scenario_2_multihop.json
│   ├── scenario_3_federation.json
│   └── scenario_4_validation.json
│
├── gen2kgbot/                   # Integrated gen2kgbot library
│   ├── app/
│   │   ├── utils/
│   │   │   ├── sparql_toolkit.py      # SPARQL execution (VALIDATED ✅)
│   │   │   ├── graph_nodes.py         # Core graph operations (VALIDATED ✅)
│   │   │   ├── construct_util.py      # Neighbourhood retrieval (VALIDATED ✅)
│   │   │   └── config_manager.py      # Configuration management
│   │   └── preprocessing/
│   │       ├── gen_descriptions.py    # Universal SPARQL queries for RDF
│   │       └── compute_embeddings.py  # FAISS embedding generation
│   └── data/
│       ├── grape_demo/faiss_embeddings/
│       ├── grape_hearing/faiss_embeddings/
│       ├── grape_psychiatry/faiss_embeddings/
│       └── grape_unified/faiss_embeddings/
│
├── tests/                       # Offline template coverage
│   └── test_agent_templates.py  # Scenario query + concept resolution assertions
│
├── scripts/                     # Utility scripts
│   └── generate_grape_embeddings.py  # One-time embedding generation
│
├── main.py                      # Application entry point
├── pyproject.toml               # Project metadata & dependencies (uv)
├── requirements.txt             # Pip-compatible dependencies
├── .env.example                 # Environment variables template
├── install.sh                   # Automated installation script
├── SCENARIO_PROMPTS.md          # Detailed scenario documentation
└── README.md                    # This file
```

### Key Changes from Original Architecture

**❌ Removed:**
- `pipelines/*.py` - Replaced by direct gen2kgbot integration
- `scenarios/*.py` - Replaced by LLM-orchestrated prompts
- Hardcoded scenario logic

**✅ Added:**
- `api/mcp.py` - 6 validated MCP tools
- `prompts/` - Scenario prompt files for LLM
- `tests/test_agent_templates.py` - Scenario template validation
- `scripts/generate_grape_embeddings.py` - Embedding preprocessing
- `SCENARIO_PROMPTS.md` - Scenario documentation

**Philosophy**: **Tools, not pipelines**. Expose capabilities, let intelligence orchestrate.

---

## Technology Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Language** | Python 3.12 | Latest stable Python |
| **Web Framework** | FastAPI | High-performance async API |
| **Package Manager** | uv | Fast Python package manager |
| **LLM Orchestration** | LangChain + Google Gemini | Agent workflows |
| **NL2SPARQL Engine** | gen2kgbot | Natural language to SPARQL |
| **Knowledge Graph** | SPARQLWrapper | SPARQL execution |
| **Vector Store** | FAISS | Semantic search (96 concepts) |
| **Embeddings** | Ollama (nomic-embed-text) | Concept embeddings |
| **Entity Extraction** | Google Gemini | LLM-based NER (replaces Spacy) |
| **Graph Database** | GraphDB | RDF triplestore with OWL reasoning |
| **API Validation** | Pydantic 2.9+ | Request/response validation |
| **Testing** | Pytest | Template/unit coverage |

---

## Development

### Running Tests

```bash
# Run template-focused tests
uv run pytest tests/test_agent_templates.py -v
```

**Test coverage:**
- ✅ Scenario SPARQL templates stay in sync with ontology constraints
- ✅ First-hit concept resolution remains deterministic
- 🔜 End-to-end smoke tests once automated GraphDB fixtures are available

### Adding a New MCP Tool

```python
# api/mcp.py

@router.post("/my_tool", response_model=Dict[str, Any])
async def my_custom_tool(request: MyToolRequest):
    """
    Description of what this tool does.

    Uses: gen2kgbot/app/utils/my_module.my_function()
    """
    try:
        # Configure gen2kgbot if needed
        configure_gen2kgbot_for_kg(request.kg_name)

        # Call gen2kgbot component
        result = my_function(request.param)

        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Adding a New Scenario Prompt

Create a JSON file in `prompts/`:

```json
{
  "scenario_id": "scenario_5_my_scenario",
  "name": "My Custom Scenario",
  "description": "What this scenario does",
  "system_prompt": "You are a medical KG assistant. Steps: 1. Call /mcp/extract_entities...",
  "example_questions": [
    "Example question 1",
    "Example question 2"
  ],
  "mcp_tools_required": [
    "/mcp/extract_entities",
    "/mcp/concepts",
    "/mcp/sparql"
  ]
}
```

---

## Troubleshooting

### "Module not found" errors

```bash
# Ensure venv is activated
source .venv/bin/activate

# Reinstall dependencies
uv pip install -r requirements.txt
```

### Embeddings not found

```bash
# Generate embeddings first
apps/backend/.venv/bin/python scripts/generate_grape_embeddings.py

# Check embeddings exist
ls -la gen2kgbot/data/*/faiss_embeddings/
```

### GraphDB connection errors

```bash
# Start GraphDB
docker-compose -f ../../docker-compose.graphdb.yml up -d

# Test connectivity
curl http://localhost:7200/repositories/hearing/size

# Health check
curl http://localhost:8000/api/mcp/health
```

### SPARQL query errors

The system uses **universal SPARQL queries** that work with any RDF graph (only `rdfs:label` and `rdfs:comment`). If you see errors:

1. Check GraphDB is running
2. Verify repository exists
3. Test with simple query: `SELECT * WHERE { ?s ?p ?o } LIMIT 1`

---

## Documentation

- **[SCENARIO_PROMPTS.md](SCENARIO_PROMPTS.md)** - Detailed scenario prompts for LLM orchestration
- **[tests/test_agent_templates.py](tests/test_agent_templates.py)** - Template and resolution tests
- **[scripts/generate_grape_embeddings.py](scripts/generate_grape_embeddings.py)** - Embedding generation
- **API Docs** - http://localhost:8000/docs (when server is running)
- **gen2kgbot Docs** - [gen2kgbot/README.md](gen2kgbot/README.md)

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- **[gen2kgbot](https://github.com/Wimmics/gen2kgbot)** - Core NL2SPARQL engine by Wimmics team
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[LangChain](https://www.langchain.com/)** - LLM orchestration
- **Google Cloud Platform** - Gemini LLM services

---

**Built with ❤️ for the Google Cloud Hackathon**
