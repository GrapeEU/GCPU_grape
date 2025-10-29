"""
Agent Endpoint - Main chat agent that orchestrates scenario execution

The agent:
1. Receives user questions
2. Detects which scenario to use (neighbourhood, multihop, federation, validation)
3. Executes the scenario using MCP tools
4. Returns results with execution trace for UX display

All execution steps are logged for debugging and frontend display.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import settings
from core.agent_executor import AgentExecutor
from core.agent_logger import AgentLogger, StepType
from core.vertex_ai_config import get_vertex_ai_chat_model

router = APIRouter(prefix="/agent", tags=["Agent"])


# Initialize executor
executor = AgentExecutor()


# Initialize Vertex AI for chat
def get_gemini_llm():
    """Get Gemini LLM instance via Vertex AI for chat."""
    return get_vertex_ai_chat_model(
        model_name="gemini-2.5-pro",
        temperature=0.7
    )


# ============================================================================
# Request/Response Models
# ============================================================================


class QueryRequest(BaseModel):
    question: str = Field(..., description="User's question")
    kg_name: str = Field("grape_hearing", description="Knowledge graph to query (grape_demo, grape_hearing, grape_psychiatry, grape_unified)")
    scenario_id: Optional[str] = Field(None, description="Force a specific scenario (optional, auto-detected if not provided)")


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Natural language answer")
    scenario_used: str = Field(..., description="Scenario that was executed")
    scenario_name: str = Field(..., description="Human-readable scenario name")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Graph nodes for visualization")
    links: List[Dict[str, Any]] = Field(default_factory=list, description="Graph links for visualization")
    sparql_queries: List[str] = Field(default_factory=list, description="SPARQL queries executed")
    trace: List[Dict[str, Any]] = Field(default_factory=list, description="Execution trace (technical)")
    trace_formatted: List[Dict[str, str]] = Field(default_factory=list, description="Execution trace (user-friendly)")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message")
    graph_id: Optional[str] = Field(None, description="Optional graph ID for context")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    is_query: bool = Field(False, description="Whether this requires query execution")
    suggested_kg: Optional[str] = Field(None, description="Suggested KG based on question context")


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Execute a knowledge graph query using the agent.

    This is the main endpoint for executing queries. It:
    1. Detects the appropriate scenario (or uses provided scenario_id)
    2. Executes the scenario using MCP tools
    3. Logs each step for debugging and UX display
    4. Returns results with visualization data

    Example:
    ```json
    {
      "question": "What are the symptoms of Tinnitus?",
      "kg_name": "grape_hearing"
    }
    ```
    """
    try:
        logger = AgentLogger()

        # Detect scenario if not provided
        if request.scenario_id:
            scenario_id = request.scenario_id
            logger.log_step(
                StepType.SCENARIO_DETECTION,
                f"Using provided scenario: {scenario_id}"
            )
        else:
            scenario_id = executor.detect_scenario(request.question, logger)

        # Execute scenario
        result = await executor.execute_scenario(
            scenario_id=scenario_id,
            question=request.question,
            kg_name=request.kg_name,
            logger=logger
        )

        return QueryResponse(
            answer=result.get("summary", "No results found"),
            scenario_used=result["scenario"],
            scenario_name=result["scenario_name"],
            nodes=result.get("nodes", []),
            links=result.get("links", []),
            sparql_queries=result.get("sparql_queries", []),
            trace=result.get("trace", []),
            trace_formatted=result.get("trace_formatted", [])
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    General chat endpoint for conversational interface.

    This endpoint handles both:
    1. General conversation (greetings, clarifications)
    2. Technical queries (which are routed to /agent/query)

    The agent detects whether the message requires KG query execution
    and responds accordingly.
    """
    try:
        llm = get_gemini_llm()

        # Detect if this is a technical query or general conversation
        detection_prompt = f"""You are a medical knowledge graph assistant. Analyze this message:

"{request.message}"

Is this a technical question that requires querying a knowledge graph?
If yes, which medical domain? (general, hearing, psychiatry, or multiple)

Respond with ONLY:
- "QUERY:general" for general medical questions
- "QUERY:hearing" for hearing/tinnitus questions
- "QUERY:psychiatry" for mental health questions
- "QUERY:unified" for cross-domain questions
- "CHAT" for greetings, clarifications, or general conversation

Response:"""

        response = llm.invoke([HumanMessage(content=detection_prompt)])
        detection = response.content.strip().upper()

        if detection.startswith("QUERY:"):
            # This is a technical query - extract domain
            domain = detection.split(":")[1].lower()
            kg_map = {
                "general": "grape_demo",
                "hearing": "grape_hearing",
                "psychiatry": "grape_psychiatry",
                "unified": "grape_unified"
            }
            kg_name = kg_map.get(domain, "grape_hearing")

            return ChatResponse(
                response=f"Let me search the {domain} knowledge graph for you...",
                is_query=True,
                suggested_kg=kg_name
            )

        else:
            # General conversation
            chat_prompt = f"""You are Grape, a friendly medical knowledge graph assistant.

The user said: "{request.message}"

Respond naturally and helpfully. You can:
- Greet users warmly
- Answer general questions about your capabilities
- Ask clarifying questions
- Explain the 4 scenarios you can execute:
  1. Neighbourhood Exploration - Explore relationships around a concept
  2. Multi-Hop Path Finding - Find connections between concepts
  3. Cross-KG Alignment - Discover links between medical domains
  4. Assertion Validation - Validate medical claims

Keep your response concise and friendly.

Response:"""

            chat_response = llm.invoke([HumanMessage(content=chat_prompt)])

            return ChatResponse(
                response=chat_response.content.strip(),
                is_query=False,
                suggested_kg=None
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/scenarios")
async def list_scenarios():
    """List all available scenarios."""
    scenarios = executor.scenarios

    return {
        "total": len(scenarios),
        "scenarios": [
            {
                "id": scenario_id,
                "name": data["name"],
                "description": data["description"],
                "example_questions": data.get("example_questions", []),
                "mcp_tools_required": data.get("mcp_tools_required", [])
            }
            for scenario_id, data in scenarios.items()
        ]
    }


@router.get("/status")
async def agent_status():
    """Get agent status and configuration."""
    return {
        "status": "operational",
        "scenarios_loaded": len(executor.scenarios),
        "mcp_endpoint": executor.base_url,
        "llm_model": "gemini-2.5-pro",
        "available_kgs": [
            "grape_demo",
            "grape_hearing",
            "grape_psychiatry",
            "grape_unified"
        ]
    }
