"""
MCP Tools Router - Exposes validated gen2kgbot functions as HTTP endpoints

Based on tested gen2kgbot core components:
- SPARQL execution (sparql_toolkit)
- Concept finding (embeddings + select_similar_classes)
- Neighbourhood retrieval (construct_util)
- Result interpretation (graph_nodes)
- Entity extraction (LLM-based)
"""

import logging
from ast import literal_eval
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add gen2kgbot to path
gen2kgbot_path = Path(__file__).parent.parent / "gen2kgbot"
if str(gen2kgbot_path) not in sys.path:
    sys.path.insert(0, str(gen2kgbot_path))

# Import validated gen2kgbot components
from app.utils.sparql_toolkit import run_sparql_query
from app.utils.graph_nodes import select_similar_classes
from app.utils.construct_util import get_connected_classes, prefixed_to_fulliri
import app.utils.config_manager as config
from core.config import settings
from core.vertex_ai_config import get_vertex_ai_chat_model
from langchain_core.messages import HumanMessage

router = APIRouter(prefix="/mcp", tags=["MCP Tools"])
logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================


class SPARQLQueryRequest(BaseModel):
    query: str = Field(..., description="SPARQL query string")
    endpoint: Optional[str] = Field(None, description="SPARQL endpoint URL (default: config)")
    kg_name: Optional[str] = Field(None, description="KG short name for context")


class ConceptFinderRequest(BaseModel):
    query_text: str = Field(..., description="Natural language query or concept name")
    kg_name: str = Field(..., description="KG short name (grape_demo, grape_hearing, grape_psychiatry, grape_unified)")
    limit: int = Field(5, description="Maximum number of similar concepts")
    scenario_id: Optional[str] = Field(
        "scenario_3",
        description="gen2kgbot scenario id to use for embeddings lookup (defaults to scenario_3)"
    )
    entities: Optional[List[str]] = Field(
        None,
        description="Optional list of entities already extracted from the question"
    )


class NeighbourhoodRequest(BaseModel):
    concept_uris: List[str] = Field(..., description="List of concept URIs to explore")
    kg_name: str = Field(..., description="KG short name")


class InterpretResultsRequest(BaseModel):
    question: str = Field(..., description="Original user question")
    sparql_results: str = Field(..., description="SPARQL results in CSV format")
    kg_name: str = Field(..., description="KG short name")
    scenario_id: Optional[str] = Field(None, description="(Reserved) scenario hint for compatibility")
    guidance: Optional[str] = Field(None, description="Optional instructions influencing the interpretation style")


class ExtractEntitiesRequest(BaseModel):
    question: str = Field(..., description="Natural language question")
    kg_name: str = Field(..., description="KG short name for context")


class ConfigureKGRequest(BaseModel):
    kg_name: str = Field(..., description="KG short name")
    endpoint: str = Field(..., description="SPARQL endpoint URL")
    description: Optional[str] = Field(None, description="KG description")


# ============================================================================
# Helper Functions
# ============================================================================


def configure_gen2kgbot_for_kg(kg_name: str, endpoint: Optional[str] = None):
    """Configure gen2kgbot for a specific KG."""
    config.config["kg_short_name"] = kg_name

    if endpoint:
        config.config["kg_sparql_endpoint_url"] = endpoint
        config.config["ontologies_sparql_endpoint_url"] = endpoint
    else:
        # Use endpoints from settings (environment-aware)
        repo_map = {
            "grape_demo": settings.graphdb_repo_demo,
            "grape_hearing": settings.graphdb_repo_hearing,
            "grape_psychiatry": settings.graphdb_repo_psychiatry,
            "grape_unified": settings.graphdb_repo_unified,
        }

        repo_endpoint = repo_map.get(kg_name)
        if not repo_endpoint:
            raise ValueError(
                f"Unknown KG name: {kg_name}. Use grape_demo, grape_hearing, grape_psychiatry, or grape_unified"
            )

        config.config["kg_sparql_endpoint_url"] = repo_endpoint
        config.config["ontologies_sparql_endpoint_url"] = repo_endpoint


async def extract_entities_with_llm(question: str, kg_description: str = "") -> List[str]:
    """Extract medical entities from question using Gemini LLM via Vertex AI."""
    try:
        llm = get_vertex_ai_chat_model(
            model_name="gemini-2.5-pro",
            temperature=0.0
        )

        prompt = f"""Extract medical concepts, symptoms, conditions, or treatments from this question.
Return ONLY a comma-separated list of entities, nothing else.

Knowledge Graph context: {kg_description or "Medical knowledge graph"}

Question: {question}

Entities:"""

        response = llm.invoke(prompt)
        entities_str = response.content.strip()
        entities = [e.strip() for e in entities_str.split(",") if e.strip()]
        return entities
    except Exception as e:
        # Fallback: extract capitalized words
        import re
        words = re.findall(r'\b[A-Z][a-z]+\b', question)
        return list(set(words))


# ============================================================================
# MCP Tool Endpoints
# ============================================================================


@router.post("/sparql", response_model=Dict[str, Any])
async def execute_sparql(request: SPARQLQueryRequest):
    """
    Execute a SPARQL query against a knowledge graph.

    Uses: gen2kgbot/app/utils/sparql_toolkit.run_sparql_query()
    """
    try:
        # Configure if kg_name provided
        if request.kg_name:
            configure_gen2kgbot_for_kg(request.kg_name, request.endpoint)
            endpoint = config.get_kg_sparql_endpoint_url()
        else:
            endpoint = request.endpoint or settings.kg_sparql_endpoint_url

        # Execute SPARQL query (returns CSV string)
        csv_results = run_sparql_query(request.query, endpoint)

        # Parse CSV to list of dicts
        lines = csv_results.strip().split("\n")
        if not lines:
            return {"results": [], "count": 0}

        headers = [h.strip() for h in lines[0].split(",")]
        results = []

        for line in lines[1:]:
            if line.strip():
                values = [v.strip() for v in line.split(",")]
                row = {headers[i]: values[i] if i < len(values) else "" for i in range(len(headers))}
                results.append(row)

        return {
            "results": results,
            "count": len(results),
            "query": request.query,
            "endpoint": endpoint
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL execution failed: {str(e)}")


@router.post("/concepts", response_model=Dict[str, Any])
async def find_concepts(request: ConceptFinderRequest):
    """
    Find concepts semantically similar to query text using embeddings.

    Uses: gen2kgbot/app/utils/graph_nodes.select_similar_classes()
    """
    try:
        # Configure gen2kgbot for the specified KG
        configure_gen2kgbot_for_kg(request.kg_name)

        # Determine which entities to use for similarity search
        entity_candidates = request.entities or [request.query_text]
        entities = [e.strip() for e in entity_candidates if e and e.strip()]
        if not entities:
            entities = [request.query_text]

        # Build minimal state for gen2kgbot similarity search
        scenario_id = request.scenario_id or "scenario_3"
        state = {
            "scenario_id": scenario_id,
            "question_relevant_entities": entities
        }

        # Call gen2kgbot's similarity search
        updated_state = select_similar_classes(state)

        # Extract similar classes
        similar_classes = updated_state.get("selected_classes", [])

        # Format response
        concepts = []
        seen_uris = set()
        blacklist_prefixes = (
            "http://www.w3.org/",
            "https://www.w3.org/",
        )

        for raw_cls in similar_classes:
            cls_tuple = raw_cls

            if isinstance(raw_cls, str):
                try:
                    cls_tuple = literal_eval(raw_cls)
                except (ValueError, SyntaxError):
                    # Skip entries that cannot be parsed
                    continue

            if not isinstance(cls_tuple, (list, tuple)) or len(cls_tuple) == 0:
                continue

            cls_uri = cls_tuple[0]
            cls_label = cls_tuple[1] if len(cls_tuple) > 1 else None
            cls_description = cls_tuple[2] if len(cls_tuple) > 2 else None

            if not cls_uri:
                continue

            full_uri = prefixed_to_fulliri(str(cls_uri))

            if any(full_uri.startswith(prefix) for prefix in blacklist_prefixes):
                continue

            if full_uri in seen_uris:
                continue

            seen_uris.add(full_uri)

            if cls_label:
                label_value = cls_label.strip()
            else:
                trimmed_uri = full_uri.split("#")[-1] if "#" in full_uri else full_uri
                trimmed_uri = trimmed_uri.split("/")[-1] if "/" in trimmed_uri else trimmed_uri
                trimmed_uri = trimmed_uri.split(":")[-1] if ":" in trimmed_uri else trimmed_uri
                label_value = trimmed_uri.strip()

            concepts.append({
                "uri": full_uri,
                "label": label_value,
                "description": cls_description
            })

            if len(concepts) >= request.limit:
                break

        return {
            "concepts": concepts,
            "count": len(concepts),
            "query": request.query_text,
            "kg": request.kg_name
        }
    except Exception as e:
        logger.exception("Concept finder failed for kg=%s query=%s", request.kg_name, request.query_text)
        raise HTTPException(status_code=500, detail=f"Concept finding failed: {str(e)}")


@router.post("/neighbourhood", response_model=Dict[str, Any])
async def retrieve_neighbourhood(request: NeighbourhoodRequest):
    """
    Retrieve connected classes for given concept URIs.

    Uses: gen2kgbot/app/utils/construct_util.get_connected_classes()
    """
    try:
        # Configure gen2kgbot
        configure_gen2kgbot_for_kg(request.kg_name)

        # Get connected classes
        connected = get_connected_classes(request.concept_uris)

        # Format response
        neighbours = []
        for cls_uri, cls_label, cls_description in connected:
            neighbours.append({
                "uri": cls_uri,
                "label": cls_label or cls_uri.split("/")[-1].split("#")[-1],
                "description": cls_description
            })

        return {
            "neighbours": neighbours,
            "count": len(neighbours),
            "seed_concepts": request.concept_uris,
            "kg": request.kg_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neighbourhood retrieval failed: {str(e)}")


@router.post("/interpret", response_model=Dict[str, Any])
async def interpret_sparql_results(request: InterpretResultsRequest):
    """
    Convert SPARQL CSV results into natural language explanation.

    Uses Gemini LLM to summarize SPARQL CSV output.
    """
    try:
        # Keep gen2kgbot configuration in sync (sets KG metadata used elsewhere)
        configure_gen2kgbot_for_kg(request.kg_name)

        llm = get_vertex_ai_chat_model(
            model_name="gemini-2.5-pro",
            temperature=0.2
        )

        csv_content = request.sparql_results.strip()
        lines = [line for line in csv_content.split("\n") if line.strip()] if csv_content else []
        results_count = max(len(lines) - 1, 0)

        if results_count == 0:
            interpretation = (
                "No rows were returned for this query. "
                "Try refining the question or expanding the neighbourhood search."
            )
        else:
            guidance_block = ""
            if request.guidance:
                guidance_block = f"""\nAdditional presentation guidance:\n{request.guidance.strip()}\n"""

            prompt = f"""You are a medical knowledge graph assistant helping a user interpret SPARQL results.

Question:
{request.question}

Results (CSV):
```csv
{csv_content}
```

Please provide:
1. A concise paragraph (<=4 sentences) answering the question.
2. Mention the number of result rows ({results_count}) and highlight notable relationships.
3. Optional bullet list of key facts if it helps clarity.
Keep the tone factual and helpful.{guidance_block}"""

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            interpretation = response.content.strip() if response and response.content else ""
            if not interpretation:
                interpretation = "Results were retrieved, but no interpretation could be generated."

        return {
            "interpretation": interpretation,
            "question": request.question,
            "kg": request.kg_name,
            "results_count": results_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interpretation failed: {str(e)}")


@router.post("/extract_entities", response_model=Dict[str, Any])
async def extract_entities(request: ExtractEntitiesRequest):
    """
    Extract named entities from question using LLM.

    Uses: Gemini LLM for intelligent entity extraction (replaces Spacy NER)
    """
    try:
        # Get KG description for context
        kg_descriptions = {
            "grape_demo": "General medical knowledge graph with common conditions",
            "grape_hearing": "Hearing & Tinnitus knowledge graph with audiology concepts",
            "grape_psychiatry": "Mental health knowledge graph with psychiatric conditions",
            "grape_unified": "Unified medical knowledge graph combining all domains"
        }

        kg_desc = kg_descriptions.get(request.kg_name, "Medical knowledge graph")

        # Extract entities using LLM
        entities = await extract_entities_with_llm(request.question, kg_desc)

        return {
            "entities": entities,
            "count": len(entities),
            "question": request.question,
            "kg": request.kg_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity extraction failed: {str(e)}")


@router.post("/configure", response_model=Dict[str, Any])
async def configure_kg(request: ConfigureKGRequest):
    """
    Configure gen2kgbot to work with a specific knowledge graph.

    Allows dynamic switching between KGs or connecting to external SPARQL endpoints.
    """
    try:
        configure_gen2kgbot_for_kg(request.kg_name, request.endpoint)

        if request.description:
            config.config["kg_description"] = request.description

        return {
            "status": "configured",
            "kg_name": request.kg_name,
            "endpoint": config.get_kg_sparql_endpoint_url(),
            "description": config.config.get("kg_description", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration failed: {str(e)}")


@router.get("/tools")
async def list_tools():
    """List all available MCP tools with their descriptions."""
    return {
        "total": 6,
        "tools": [
            {
                "name": "execute_sparql",
                "endpoint": "/api/mcp/sparql",
                "description": "Execute SPARQL queries against knowledge graphs",
                "method": "POST",
                "gen2kgbot_component": "sparql_toolkit.run_sparql_query"
            },
            {
                "name": "find_concepts",
                "endpoint": "/api/mcp/concepts",
                "description": "Find concepts using semantic similarity (embeddings)",
                "method": "POST",
                "gen2kgbot_component": "graph_nodes.select_similar_classes"
            },
            {
                "name": "retrieve_neighbourhood",
                "endpoint": "/api/mcp/neighbourhood",
                "description": "Get classes connected to seed concepts",
                "method": "POST",
                "gen2kgbot_component": "construct_util.get_connected_classes"
            },
            {
                "name": "interpret_results",
                "endpoint": "/api/mcp/interpret",
                "description": "Convert SPARQL results to natural language",
                "method": "POST",
                "gen2kgbot_component": "graph_nodes.interpret_results"
            },
            {
                "name": "extract_entities",
                "endpoint": "/api/mcp/extract_entities",
                "description": "Extract medical entities from questions using LLM",
                "method": "POST",
                "gen2kgbot_component": "ChatGoogleGenerativeAI (replaces Spacy)"
            },
            {
                "name": "configure_kg",
                "endpoint": "/api/mcp/configure",
                "description": "Switch between KGs or connect to external endpoints",
                "method": "POST",
                "gen2kgbot_component": "config_manager"
            },
        ],
    }


@router.get("/health")
async def health_check():
    """Check if MCP tools and gen2kgbot are operational."""
    try:
        # Test SPARQL connectivity
        test_query = "SELECT * WHERE { ?s ?p ?o } LIMIT 1"
        run_sparql_query(test_query, settings.kg_sparql_endpoint_url)

        return {
            "status": "healthy",
            "gen2kgbot": "loaded",
            "sparql_endpoint": settings.kg_sparql_endpoint_url,
            "tools_available": 6
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "tools_available": 6
        }
