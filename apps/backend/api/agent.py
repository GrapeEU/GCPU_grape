"""
Agent Endpoint - Main chat agent that routes to 9 scenarios

Simple Gemini-based agent that:
1. Receives user messages
2. Identifies which scenario to use (1-9)
3. Executes the scenario with MCP tools
4. Returns the result

Usage:
    POST /api/agent/chat
    {
        "message": "What is the relationship between X and Y?",
        "graph_id": "optional_graph_id"
    }
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import settings

router = APIRouter(prefix="/agent", tags=["Agent"])

# Initialize Gemini
def get_gemini_llm():
    """Get Gemini LLM instance."""
    api_key = settings.gemini_api_key or settings.google_api_key
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set in .env file")

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.7,
    )


# Agent system prompt
AGENT_SYSTEM_PROMPT = """You are Grape KG Agent, a friendly assistant expert in knowledge graph exploration.

## Behavior Rules:

1. **General conversation**: Answer normally to greetings, general questions, or clarifications.

2. **Technical KG questions**: When the user asks a technical question requiring knowledge graph analysis:
   - Respond with: "Laissez-moi regarder dans le graph [[X]]"
   - Replace X with the scenario number (1-9)
   - Add a brief friendly message after if appropriate

## Available Scenarios:

1. **Concept Exploration** - Explore information around a specific concept
2. **Multi-hop Reasoning** - Find logical paths between concepts
3. **NL2SPARQL Adaptive** - Convert complex questions to SPARQL queries
4. **Cross-KG Federation** - Link concepts across multiple knowledge graphs
5. **Validation/Proof** - Prove or refute assertions
6. **Explainable Reasoning** - Explain the reasoning path taken
7. **Filtered Exploration** - Query with business constraints
8. **Alignment Detection** - Detect agreements/divergences between KGs
9. **Decision Synthesis** - Actionable synthesis with traceability

## Examples:

User: "Hello!"
You: "Bonjour ! Comment puis-je vous aider avec votre knowledge graph aujourd'hui ?"

User: "What is the relationship between protein X and disease Y?"
You: "Laissez-moi regarder dans le graph [[2]]"

User: "Can you explain that?"
You: "Bien sûr, je vais vous expliquer le raisonnement. Laissez-moi regarder dans le graph [[6]]"
"""


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message")
    graph_id: Optional[str] = Field(None, description="Optional graph ID for context")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    scenario_used: Optional[int] = Field(None, description="Scenario number used (1-9)")
    reasoning: Optional[str] = Field(None, description="Why this scenario was chosen")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - receives user message and routes to appropriate scenario.

    The agent can:
    1. Respond to general questions normally
    2. For technical KG questions, respond with "Laissez-moi regarder dans le graph [[X]]"
       where X is the scenario number (parsed by frontend)
    """
    try:
        llm = get_gemini_llm()

        # Get response from Gemini
        messages = [
            SystemMessage(content=AGENT_SYSTEM_PROMPT),
            HumanMessage(content=request.message)
        ]

        response = llm.invoke(messages)
        agent_response = response.content.strip()

        # Extract scenario number from [[X]] pattern if present
        import re
        scenario_match = re.search(r'\[\[(\d)\]\]', agent_response)

        if scenario_match:
            scenario_num = int(scenario_match.group(1))
            # Scenario execution will be implemented next
            # For now, just return the response with scenario ID
            return ChatResponse(
                response=agent_response,
                scenario_used=scenario_num,
                reasoning=f"Technical query requiring scenario {scenario_num}"
            )
        else:
            # General conversation, no scenario needed
            return ChatResponse(
                response=agent_response,
                scenario_used=None,
                reasoning="General conversation"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.get("/scenarios")
async def list_scenarios():
    """List all available scenarios."""
    return {
        "scenarios": [
            {"id": 1, "name": "Concept Exploration", "description": "Explore information around a concept"},
            {"id": 2, "name": "Multi-hop Reasoning", "description": "Find logical paths between concepts"},
            {"id": 3, "name": "NL2SPARQL Adaptive", "description": "Complex question to SPARQL with context"},
            {"id": 4, "name": "Cross-KG Federation", "description": "Link concepts across multiple KGs"},
            {"id": 5, "name": "Validation/Proof", "description": "Prove or refute assertions"},
            {"id": 6, "name": "Explainable Reasoning", "description": "Explain the reasoning path"},
            {"id": 7, "name": "Filtered Exploration", "description": "Query with business constraints"},
            {"id": 8, "name": "Alignment Detection", "description": "Detect agreements/divergences"},
            {"id": 9, "name": "Decision Synthesis", "description": "Actionable synthesis with traceability"}
        ]
    }
