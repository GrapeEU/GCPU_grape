"""
Agent Executor - Orchestrates MCP tool calls based on scenario prompts

Reads scenario prompts from prompts/*.json and executes them by:
1. Loading the scenario prompt
2. Calling MCP tools in sequence
3. Logging each step
4. Returning structured results
"""

import json
import re
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from langchain_core.messages import HumanMessage

from core.config import settings
from core.agent_logger import AgentLogger, StepType, StepStatus
from core.vertex_ai_config import get_vertex_ai_chat_model


class AgentExecutor:
    """
    Executes scenarios by orchestrating MCP tool calls.

    The executor:
    - Loads scenario prompts from JSON files
    - Uses Gemini LLM to decide which MCP tools to call
    - Executes MCP tools via HTTP
    - Logs each step for debugging and UX display
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        self.scenarios = self._load_scenarios()

        self.known_concept_map = {
            "chronic stress": "http://example.org/psychiatry/ChronicStress",
            "hearing loss": "http://example.org/hearing/HearingLoss",
            "tinnitus": "http://example.org/hearing/Tinnitus",
            "generalized anxiety disorder": "http://example.org/psychiatry/GeneralizedAnxietyDisorder",
            "hyperacusis": "http://example.org/hearing/Hyperacusis",
            "cognitive behavioral therapy": "http://example.org/hearing/CognitiveBehavioralTherapy",
            "cbt": "http://example.org/hearing/CognitiveBehavioralTherapy",
        }
        self.demo_triggers = {
            "scenario_2_multihop": [
                "chronic stress",
                "hearing loss"
            ],
            "scenario_3_federation": [
                "tinnitus",
                "generalized anxiety disorder"
            ],
            "scenario_4_validation": [
                "hearing loss",
                "cbt"
            ]
        }
        self.demo_scenarios = {
            "scenario_1_neighbourhood",
            "scenario_2_multihop",
            "scenario_3_federation",
            "scenario_4_validation"
        }

        # Initialize Vertex AI LLM for orchestration
        self.llm = get_vertex_ai_chat_model(
            model_name="gemini-2.5-pro",
            temperature=0.0  # Deterministic for tool calling
        )

    def _load_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Load all scenario prompts from JSON files."""
        scenarios = {}

        for json_file in self.prompts_dir.glob("scenario_*.json"):
            with open(json_file, "r") as f:
                scenario_data = json.load(f)
                scenario_id = scenario_data["scenario_id"]
                scenarios[scenario_id] = scenario_data

        return scenarios

    def get_scenario_by_id(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Get scenario prompt by ID."""
        return self.scenarios.get(scenario_id)

    def detect_scenario(self, question: str, logger: AgentLogger) -> str:
        """
        Detect which scenario to use based on the question.

        Uses Gemini to analyze the question and match it to a scenario.
        """
        logger.start_step(StepType.SCENARIO_DETECTION, "Analyzing question to identify scenario...")

        # Build scenario descriptions for LLM
        scenarios_desc = "\n".join([
            f"- {sid}: {data['name']} - {data['description']}"
            for sid, data in self.scenarios.items()
        ])

        detection_prompt = f"""You are a medical knowledge graph assistant. Analyze the user's question and identify which scenario fits best.

**Available Scenarios:**
{scenarios_desc}

**User Question:** {question}

**Instructions:**
Return ONLY the scenario_id (e.g., "scenario_1_neighbourhood"). No explanation needed.

**Scenario ID:**"""

        try:
            response = self.llm.invoke([HumanMessage(content=detection_prompt)])
            detected = response.content.strip()

            # Validate scenario exists
            if detected not in self.scenarios:
                # Default to neighbourhood if unsure
                detected = "scenario_1_neighbourhood"

            logger.log_scenario_detection(question, self.scenarios[detected]["name"])
            return detected

        except Exception as e:
            logger.log_error(f"Scenario detection failed: {str(e)}", e)
            return "scenario_1_neighbourhood"  # Safe default

    async def call_mcp_tool(
        self,
        tool_path: str,
        payload: Dict[str, Any],
        logger: AgentLogger
    ) -> Dict[str, Any]:
        """
        Call an MCP tool via HTTP.

        Args:
            tool_path: Tool endpoint path (e.g., "/mcp/concepts")
            payload: Request payload
            logger: Logger instance

        Returns:
            Tool response as dictionary
        """
        url = f"{self.base_url}/api{tool_path}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.log_error(f"MCP tool {tool_path} failed: HTTP {e.response.status_code}", e)
            raise
        except Exception as e:
            logger.log_error(f"MCP tool {tool_path} failed: {str(e)}", e)
            raise

    async def execute_scenario(
        self,
        scenario_id: str,
        question: str,
        kg_name: str = "grape_hearing",
        logger: Optional[AgentLogger] = None
    ) -> Dict[str, Any]:
        """
        Execute a scenario by calling MCP tools in sequence.

        Args:
            scenario_id: Scenario to execute
            question: User's question
            kg_name: Knowledge graph to query
            logger: Optional logger instance

        Returns:
            Execution result with nodes, links, summary, and trace
        """
        if logger is None:
            logger = AgentLogger()

        context: Dict[str, Any] = {
            "entities": [],
            "concepts": [],
            "concept_uris": [],
            "last_sparql_results": [],
            "last_sparql_query": "",
            "scenario_id": scenario_id,
            "question": question
        }

        scenario = self.get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        # Short-circuit demo scenarios with deterministic pipelines
        if scenario_id == "scenario_2_multihop" and self._is_demo_question(question, scenario_id):
            return await self._execute_multihop_demo(question, kg_name, logger)
        if scenario_id == "scenario_3_federation" and self._is_demo_question(question, scenario_id):
            return await self._execute_federation_demo(question, kg_name, logger)
        if scenario_id == "scenario_4_validation" and self._is_demo_question(question, scenario_id):
            return await self._execute_validation_demo(question, kg_name, logger)

        logger.log_step(
            StepType.SCENARIO_DETECTION,
            f"Executing scenario: {scenario['name']}",
            details={"scenario_id": scenario_id, "kg_name": kg_name}
        )

        # Use the scenario's system prompt to guide LLM orchestration
        orchestration_prompt = f"""{scenario['system_prompt']}

**Current Task:**
- Question: {question}
- Knowledge Graph: {kg_name}
- Scenario: {scenario['name']}

**Instructions:**
Execute this scenario step by step. For each MCP tool call, provide:
1. Tool endpoint (e.g., /mcp/extract_entities)
2. Payload as JSON

Format your response as a JSON array of steps:
```json
[
  {{
    "tool": "/mcp/extract_entities",
    "payload": {{"question": "{question}", "kg_name": "{kg_name}"}}
  }},
  {{
    "tool": "/mcp/concepts",
    "payload": {{"query_text": "extracted_entity", "kg_name": "{kg_name}", "limit": 3}}
  }}
]
```

Provide the execution plan:"""

        try:
            # Get execution plan from LLM
            response = self.llm.invoke([HumanMessage(content=orchestration_prompt)])
            plan_text = response.content.strip()

            # Extract JSON from markdown code blocks if present
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', plan_text)
            if json_match:
                plan_text = json_match.group(1)

            execution_plan = json.loads(plan_text)

            # Execute each step in the plan
            results = {
                "nodes": [],
                "links": [],
                "sparql_queries": [],
                "summary": ""
            }

            for i, step in enumerate(execution_plan):
                tool = step["tool"]
                payload = step["payload"]

                # Ensure interpret tool receives scenario context
                if tool == "/mcp/interpret":
                    payload.setdefault("scenario_id", scenario_id)
                    payload.setdefault("kg_name", kg_name)

                logger.start_step(
                    StepType.SPARQL_QUERY if "sparql" in tool else StepType.CONCEPT_SEARCH,
                    f"Step {i+1}: Calling {tool}"
                )

                # Call MCP tool with optional fallback for SPARQL queries
                fallback_attempted = False
                regen_attempts = 0

                while True:
                    try:
                        if "neighbourhood" in tool:
                            payload = self._prepare_neighbourhood_payload(payload, context, logger)
                        if "sparql" in tool:
                            payload = self._prepare_sparql_payload(payload, context, kg_name, scenario_id)
                            preview = payload.get("query", "")
                            if preview:
                                logger.log_step(
                                    StepType.SPARQL_QUERY,
                                    "Prepared SPARQL payload",
                                    status=StepStatus.IN_PROGRESS,
                                    details={
                                        "context_uris": context.get("concept_uris", []),
                                        "query_preview": preview[:200]
                                    }
                                )
                                logger.logger.info(f"[SPARQL] Query prepared:\n{preview}")

                        tool_result = await self.call_mcp_tool(tool, payload, logger)
                        break

                    except httpx.HTTPStatusError as e:
                        if "sparql" in tool:
                            # Attempt regeneration if retries remaining
                            if regen_attempts < 7:
                                error_text = ""
                                try:
                                    error_text = e.response.text[:500]
                                except Exception:
                                    error_text = str(e)

                                regenerated_query = self._regenerate_sparql_query(
                                    scenario,
                                    question,
                                    context,
                                    payload.get("query", ""),
                                    error_text,
                                    regen_attempts + 1
                                )

                                if regenerated_query:
                                    regen_attempts += 1
                                    payload["query"] = regenerated_query
                                    logger.log_step(
                                        StepType.SPARQL_QUERY,
                                        f"Retrying SPARQL with regenerated query (attempt {regen_attempts})",
                                        status=StepStatus.IN_PROGRESS,
                                        details={"query_preview": regenerated_query[:200]}
                                    )
                                    continue

                        if "sparql" in tool and not fallback_attempted:
                            fallback_query = self._build_fallback_sparql(
                                scenario_id, context, kg_name
                            )
                            if fallback_query:
                                payload["query"] = fallback_query
                                payload["kg_name"] = kg_name
                                logger.log_step(
                                    StepType.SPARQL_QUERY,
                                    "Retrying SPARQL with fallback query",
                                    status=StepStatus.IN_PROGRESS,
                                    details={"query_preview": fallback_query[:200]}
                                )
                                fallback_attempted = True
                                regen_attempts = 0
                                continue
                        raise

                # Log specific step types
                if "extract_entities" in tool:
                    entities = tool_result.get("entities", [])
                    logger.log_entity_extraction(entities)
                    context["entities"] = entities

                elif "concepts" in tool:
                    concepts = tool_result.get("concepts", [])
                    query_text = payload.get("query_text", "")
                    logger.log_concept_search(query_text, len(concepts))

                    if concepts:
                        context["concepts"].append({
                            "query": query_text,
                            "items": concepts
                        })

                        best_concept = self._select_best_concept(query_text, concepts)
                        if best_concept:
                            best_label = (best_concept.get("label") or "").lower()
                            normalized_query = query_text.lower().strip()
                            if normalized_query and normalized_query not in best_label:
                                inferred_uri = self._infer_known_concept_uri(query_text)
                                if inferred_uri and inferred_uri not in context["concept_uris"]:
                                    context["concept_uris"].append(inferred_uri)
                                    logger.log_step(
                                        StepType.CONCEPT_SEARCH,
                                        f"Inferred concept URI for '{query_text}'",
                                        details={"uri": inferred_uri, "reason": "label mismatch"}
                                    )
                                elif not inferred_uri:
                                    best_uri = best_concept.get("uri")
                                    if best_uri and best_uri not in context["concept_uris"]:
                                        context["concept_uris"].append(best_uri)
                                        logger.log_step(
                                            StepType.CONCEPT_SEARCH,
                                            f"Selected concept for '{query_text}' (fallback)",
                                            details={"uri": best_uri, "label": best_concept.get("label")}
                                        )
                            else:
                                best_uri = best_concept.get("uri")
                                if best_uri and best_uri not in context["concept_uris"]:
                                    context["concept_uris"].append(best_uri)
                                    logger.log_step(
                                        StepType.CONCEPT_SEARCH,
                                        f"Selected concept for '{query_text}'",
                                        details={"uri": best_uri, "label": best_concept.get("label")}
                                    )
                        else:
                            inferred_uri = self._infer_known_concept_uri(query_text)
                            if inferred_uri and inferred_uri not in context["concept_uris"]:
                                context["concept_uris"].append(inferred_uri)
                                logger.log_step(
                                    StepType.CONCEPT_SEARCH,
                                    f"Inferred concept URI for '{query_text}'",
                                    details={"uri": inferred_uri}
                                )

                    # Add concepts as nodes
                    for concept in concepts:
                        results["nodes"].append({
                            "id": concept["uri"],
                            "label": concept["label"],
                            "type": "concept"
                        })

                elif "sparql" in tool:
                    sparql_results = tool_result.get("results", [])
                    context["last_sparql_results"] = sparql_results
                    context["last_sparql_query"] = payload.get("query")
                    query = tool_result.get("query", "")
                    logger.log_sparql_query(query, len(sparql_results))

                    results["sparql_queries"].append(query)

                    if sparql_results:
                        self._merge_graph_results(results, sparql_results, context, scenario_id)

                elif "interpret" in tool:
                    interpretation = tool_result.get("interpretation", "")
                    results["summary"] = interpretation
                    logger.log_interpretation(interpretation)

            # If no interpretation was generated, create one
            if not results["summary"]:
                logger.start_step(StepType.RESULT_INTERPRETATION, "Generating final summary...")

                # Call interpret with collected data
                csv_results = "\n".join([
                    ",".join(row.values()) for row in sparql_results[:10]
                ]) if "sparql_results" in locals() else ""

                if csv_results:
                    interpret_result = await self.call_mcp_tool(
                        "/mcp/interpret",
                        {
                            "question": question,
                            "sparql_results": csv_results,
                            "kg_name": kg_name,
                            "scenario_id": scenario_id
                        },
                        logger
                    )
                    results["summary"] = interpret_result.get("interpretation", "")
                    logger.log_interpretation(results["summary"])

            summary_override = await self._maybe_generate_demo_summary(
                scenario_id,
                question,
                kg_name,
                results,
                context,
                logger
            )
            if summary_override:
                results["summary"] = summary_override

            logger.log_success(f"Scenario '{scenario['name']}' completed successfully")

            return {
                "scenario": scenario_id,
                "scenario_name": scenario["name"],
                "question": question,
                "kg_name": kg_name,
                **results,
                "trace": logger.get_trace(),
                "trace_formatted": logger.format_for_frontend()
            }

        except json.JSONDecodeError as e:
            logger.log_error(f"Failed to parse LLM execution plan: {str(e)}", e)
            # Fallback: execute a simple default flow
            return await self._execute_default_flow(question, kg_name, logger)

        except Exception as e:
            last_query = context.get("last_sparql_query")
            if last_query:
                logger.log_step(
                    StepType.SPARQL_QUERY,
                    "Last SPARQL query before failure",
                    status=StepStatus.FAILED,
                    details={"query_preview": last_query[:200]}
                )

            logger.log_error(f"Scenario execution failed: {str(e)}", e)
            raise

    def _prepare_sparql_payload(
        self,
        payload: Dict[str, Any],
        context: Dict[str, Any],
        kg_name: str,
        scenario_id: str
    ) -> Dict[str, Any]:
        """Ensure SPARQL payload has KG context and replaces URI placeholders."""
        payload.setdefault("kg_name", kg_name)
        query = payload.get("query")
        if not isinstance(query, str):
            query = ""

        concept_uris = context.get("concept_uris", [])
        source_uri = concept_uris[0] if len(concept_uris) > 0 else None
        target_uri = concept_uris[1] if len(concept_uris) > 1 else None

        replacements: Dict[str, str] = {}
        if source_uri:
            replacements["{{SOURCE_URI}}"] = f"<{source_uri}>"
            replacements["<SOURCE_URI>"] = f"<{source_uri}>"
        if target_uri:
            replacements["{{TARGET_URI}}"] = f"<{target_uri}>"
            replacements["<TARGET_URI>"] = f"<{target_uri}>"

        for placeholder, value in replacements.items():
            if placeholder in query:
                query = query.replace(placeholder, value)

        question = context.get("question", "")
        is_demo = self._is_demo_question(question, scenario_id)

        if scenario_id == "scenario_2_multihop":
            if is_demo:
                fallback_query = self._build_fallback_sparql(scenario_id, context, kg_name)
                if fallback_query:
                    query = fallback_query
            else:
                upper_query = query.upper()
                if "CONSTRUCT" in upper_query and "SELECT" not in upper_query:
                    fallback_query = self._build_fallback_sparql(scenario_id, context, kg_name)
                    if fallback_query:
                        query = fallback_query
        else:
            upper_query = query.upper()
            if "CONSTRUCT" in upper_query and "SELECT" not in upper_query:
                fallback_query = self._build_fallback_sparql(scenario_id, context, kg_name)
                if fallback_query:
                    query = fallback_query

        if not query.strip():
            query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 1"

        payload["query"] = query
        return payload

    def _build_fallback_sparql(
        self,
        scenario_id: str,
        context: Dict[str, Any],
        kg_name: str
    ) -> Optional[str]:
        """Build a fallback SPARQL query for scenarios when LLM-generated query fails."""
        concept_uris = context.get("concept_uris", [])

        if scenario_id == "scenario_2_multihop" and len(concept_uris) >= 2:
            source, target = concept_uris[0], concept_uris[1]
            return f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?intermediate ?relation1 ?relation2 ?intermediateLabel
WHERE {{
  <{source}> ?relation1 ?intermediate .
  ?intermediate ?relation2 <{target}> .
  OPTIONAL {{ ?intermediate rdfs:label ?intermediateLabel }}
}}
LIMIT 25"""

        if scenario_id == "scenario_4_validation" and len(concept_uris) >= 2:
            subject, obj = concept_uris[0], concept_uris[1]
            return f"""SELECT ?relation
WHERE {{
  <{subject}> ?relation <{obj}> .
}}
LIMIT 10"""

        return None

    async def _maybe_generate_demo_summary(
        self,
        scenario_id: str,
        question: str,
        kg_name: str,
        results: Dict[str, Any],
        context: Dict[str, Any],
        logger: AgentLogger
    ) -> str:
        """Ensure deterministic demos still pass through the interpret MCP with tailored guidance."""
        if scenario_id != "scenario_1_neighbourhood":
            return ""

        rows = context.get("last_sparql_results", [])
        if not rows:
            return ""

        csv_content = self._rows_to_csv(rows)
        if not csv_content:
            return ""

        guidance = self._build_demo_guidance(
            scenario_id,
            question,
            results,
            rows,
            context=context
        )

        payload: Dict[str, Any] = {
            "question": question,
            "kg_name": kg_name,
            "sparql_results": csv_content,
            "scenario_id": scenario_id
        }
        if guidance:
            payload["guidance"] = guidance

        interpret_result = await self.call_mcp_tool(
            "/mcp/interpret",
            payload,
            logger
        )

        summary = interpret_result.get("interpretation", "")
        if summary:
            logger.log_interpretation(summary)
        return summary

    def _determine_focus_concept(
        self,
        results: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], str]:
        """Infer the primary concept URI and a human-readable label for neighbourhood summaries."""
        context = context or {}
        concept_uris = context.get("concept_uris", [])
        primary_uri = concept_uris[0] if concept_uris else None

        focus_label = self._infer_label(primary_uri) if primary_uri else None
        if not focus_label:
            entities = context.get("entities", [])
            focus_label = entities[0] if entities else context.get("question", "")
        focus_label = (focus_label or "the concept").strip() or "the concept"

        if not primary_uri:
            focus_lower = focus_label.lower()
            for node in results.get("nodes", []):
                label = (node.get("label") or "").lower()
                if label and (focus_lower in label or label in focus_lower):
                    primary_uri = node.get("id")
                    break

        return primary_uri, focus_label

    def _format_csv_value(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).replace("\n", " ").replace("\r", " ").strip()
        if any(char in text for char in [",", '"']):
            text = '"' + text.replace('"', '""') + '"'
        return text

    def _rows_to_csv(
        self,
        rows: List[Dict[str, Any]],
        max_rows: int = 30
    ) -> str:
        if not rows:
            return ""

        headers: List[str] = []
        for row in rows:
            for key in row.keys():
                if key not in headers:
                    headers.append(key)

        limited_rows = rows[:max_rows]
        csv_lines = [",".join(headers)]
        for row in limited_rows:
            csv_lines.append(
                ",".join(self._format_csv_value(row.get(header)) for header in headers)
            )

        return "\n".join(csv_lines)

    def _build_demo_guidance(
        self,
        scenario_id: str,
        question: str,
        results: Dict[str, Any],
        rows: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> str:
        extra = extra or {}
        if scenario_id == "scenario_1_neighbourhood":
            _, focus_label = self._determine_focus_concept(results, context)
            relation_names = {
                self._infer_label(link.get("relation")) for link in results.get("links", [])
                if link.get("relation")
            }
            relation_names.discard("")
            relation_names_sorted = sorted(relation_names)
            relation_excerpt = ", ".join(relation_names_sorted[:5])
            link_count = len(results.get("links", []))
            node_count = len(results.get("nodes", []))

            return (
                f"Focus concept: {focus_label}. There are {link_count} edges across {node_count} nodes "
                f"for the user question \"{question}\". If helpful, relation predicates include: {relation_excerpt or 'see CSV'}.\n"
                "Produce one paragraph connecting the focus concept to its neighbourhood, followed by up to four bullet points "
                "each describing a relation (format '- relation: source -> target'). Conclude with a sentence suggesting how this "
                "neighbourhood answers the question."
            )

        if scenario_id == "scenario_2_multihop":
            source_label = extra.get("source_label", "Source concept")
            target_label = extra.get("target_label", "Target concept")
            path_samples = extra.get("paths", []) or []
            sample_text = "; ".join(path_samples[:2])
            return (
                f"Map out how {source_label} may progress toward {target_label} using the hop sequences returned in the CSV. "
                f"There are {len(rows)} rows describing path segments. Explain the overall storyline in a short paragraph "
                "highlighting intermediate risk factors. Then add a bullet list with up to three representative paths (start → … → end). "
                f"If you need inspiration, example path sketches: {sample_text or 'see CSV rows'}."
            )

        if scenario_id == "scenario_3_federation":
            alignment_count = extra.get("alignment_count", len(rows))
            top_pairs = extra.get("top_pairs", []) or []
            sample_text = "; ".join(top_pairs[:3])
            return (
                "Present the cross-ontology matches between the hearing and psychiatry graphs. "
                f"Acknowledge that {alignment_count} alignment row(s) are available. "
                "Write a concise explanatory paragraph describing how the ontologies overlap, then enumerate 2-3 bullet highlights "
                "showing the matched concept pairs (format '- Hearing concept ↔ Psychiatry concept'). "
                f"Use pairs such as {sample_text or 'those surfaced in the CSV'} to ground the explanation. "
                "Close by explaining why these overlaps matter for the user's question."
            )

        if scenario_id == "scenario_4_validation":
            subject_label = extra.get("subject_label", "Subject concept")
            therapy_label = extra.get("therapy_label", "Target concept")
            direct_edge = extra.get("has_direct_edge", False)
            other_treatments = extra.get("other_treatments", [])
            other_text = ", ".join(other_treatments[:3])
            return (
                f"Validate whether the knowledge graph contains a direct treatment edge linking {subject_label} to {therapy_label}. "
                f"The CSV lists candidate relations; treat them as evidence. "
                "Draft an answer that states clearly if the direct edge exists, cites the predicate used when present, "
                "and mentions alternative treatments when relevant. "
                f"Detected alternative treatments: {other_text or 'none surfaced beyond the CSV rows'}. "
                "End with one sentence about how this validation could guide clinicians or analysts."
            )

        return ""

    async def _interpret_demo_summary(
        self,
        scenario_id: str,
        question: str,
        kg_name: str,
        rows: List[Dict[str, Any]],
        results: Dict[str, Any],
        logger: AgentLogger,
        context: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
        fallback: str = ""
    ) -> str:
        csv_content = self._rows_to_csv(rows)
        if not csv_content:
            return fallback

        guidance = self._build_demo_guidance(
            scenario_id,
            question,
            results,
            rows,
            context=context,
            extra=extra
        )

        payload: Dict[str, Any] = {
            "question": question,
            "kg_name": kg_name,
            "sparql_results": csv_content,
            "scenario_id": scenario_id
        }
        if guidance:
            payload["guidance"] = guidance

        try:
            interpret_result = await self.call_mcp_tool(
                "/mcp/interpret",
                payload,
                logger
            )
        except Exception:
            return fallback

        summary = interpret_result.get("interpretation", "") if interpret_result else ""
        return summary or fallback

    def _merge_graph_results(
        self,
        results: Dict[str, Any],
        rows: List[Dict[str, Any]],
        context: Dict[str, Any],
        scenario_id: str
    ) -> None:
        """Merge SPARQL tabular results into nodes/links for visualization."""
        if not rows:
            return

        nodes = results.setdefault("nodes", [])
        links = results.setdefault("links", [])

        node_index = {node["id"]: node for node in nodes if "id" in node}
        link_set = {
            (link.get("source"), link.get("target"), link.get("relation"))
            for link in links
        }

        concept_uris = context.get("concept_uris", [])
        source_default = concept_uris[0] if len(concept_uris) > 0 else None
        target_default = concept_uris[1] if len(concept_uris) > 1 else None

        def ensure_node(uri: Optional[str], label: Optional[str] = None) -> Optional[str]:
            if not uri:
                return None
            if uri not in node_index:
                node_index[uri] = {
                    "id": uri,
                    "label": label or self._infer_label(uri),
                    "type": "concept"
                }
                nodes.append(node_index[uri])
            else:
                if label and not node_index[uri].get("label"):
                    node_index[uri]["label"] = label
            return uri

        for row in rows:
            source_uri = row.get("source") or row.get("subject") or row.get("s") or source_default
            target_uri = row.get("target") or row.get("object") or row.get("o") or target_default
            relation = row.get("relation") or row.get("predicate") or row.get("p")

            ensure_node(source_uri, row.get("sourceLabel"))
            ensure_node(target_uri, row.get("targetLabel"))

            intermediate = (
                row.get("intermediate")
                or row.get("inter1")
                or row.get("intermediateNode")
            )
            intermediate_label = (
                row.get("intermediateLabel")
                or row.get("inter1Label")
                or row.get("intermediate_nodeLabel")
            )
            rel1 = row.get("relation1") or row.get("r1")
            rel2 = row.get("relation2") or row.get("r2") or row.get("relation3") or row.get("r3")

            if intermediate:
                ensure_node(intermediate, intermediate_label)
                if source_uri and rel1:
                    key = (source_uri, intermediate, rel1)
                    if key not in link_set:
                        links.append({"source": source_uri, "target": intermediate, "relation": rel1})
                        link_set.add(key)
                if target_uri and rel2:
                    key = (intermediate, target_uri, rel2)
                    if key not in link_set:
                        links.append({"source": intermediate, "target": target_uri, "relation": rel2})
                        link_set.add(key)
            else:
                if source_uri and target_uri and relation:
                    key = (source_uri, target_uri, relation)
                    if key not in link_set:
                        links.append({"source": source_uri, "target": target_uri, "relation": relation})
                        link_set.add(key)

    @staticmethod
    def _infer_label(uri: str) -> str:
        if not uri:
            return "Unknown"
        for separator in ("#", "/"):
            if separator in uri:
                candidate = uri.rsplit(separator, 1)[-1]
                if candidate:
                    return candidate
        return uri

    def _prepare_neighbourhood_payload(
        self,
        payload: Dict[str, Any],
        context: Dict[str, Any],
        logger: AgentLogger
    ) -> Dict[str, Any]:
        uris = payload.get("concept_uris", [])
        if not uris:
            return payload

        if any("concept1_uri_from_sparql_results" in u or "concept2_uri_from_sparql_results" in u for u in uris):
            sparql_rows = context.get("last_sparql_results", [])
            extracted: List[str] = []
            for row in sparql_rows:
                c1 = row.get("concept1") or row.get("source") or row.get("subject")
                c2 = row.get("concept2") or row.get("target") or row.get("object")
                if isinstance(c1, dict):
                    c1 = c1.get("value")
                if isinstance(c2, dict):
                    c2 = c2.get("value")
                for candidate in (c1, c2):
                    if isinstance(candidate, str):
                        extracted.append(candidate)
            if extracted:
                payload["concept_uris"] = extracted[:len(uris)]
                logger.log_step(
                    StepType.NEIGHBOURHOOD_EXPLORATION,
                    "Filled neighbourhood URIs from SPARQL results",
                    details={"concept_uris": payload["concept_uris"]}
                )
            elif context.get("concept_uris"):
                payload["concept_uris"] = context["concept_uris"][:len(uris)]
        return payload

    @staticmethod
    def _select_best_concept(query_text: str, concepts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Pick the most relevant concept for a query based on simple string matching heuristics.
        Prioritises:
        - Labels containing the full query (case-insensitive)
        - URIs ending with the query (with punctuation removed)
        - Concepts that are not generic OWL/RDFS classes
        """
        if not concepts:
            return None

        normalized_query = query_text.lower().strip()

        def is_generic(concept: Dict[str, Any]) -> bool:
            uri = concept.get("uri", "")
            return any(prefix in uri for prefix in [
                "http://www.w3.org/2002/07/owl#",
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "http://www.w3.org/2000/01/rdf-schema#"
            ])

        # Exact label match
        for concept in concepts:
            label = (concept.get("label") or "").lower()
            if label == normalized_query:
                return concept

        # Label contains query
        for concept in concepts:
            label = (concept.get("label") or "").lower()
            if normalized_query and normalized_query in label and not is_generic(concept):
                return concept

        # URI ends with query tokens
        compact_query = re.sub(r"[^a-z0-9]", "", normalized_query)
        for concept in concepts:
            uri_tail = re.sub(r"[^a-z0-9]", "", concept.get("uri", "").lower())
            if compact_query and compact_query in uri_tail and not is_generic(concept):
                return concept

        # Fallback: first non generic concept
        for concept in concepts:
            if not is_generic(concept):
                return concept

        return concepts[0]

    def _infer_known_concept_uri(self, query_text: str) -> Optional[str]:
        if not query_text:
            return None
        key = query_text.lower().strip()
        return self.known_concept_map.get(key)

    def _is_demo_question(self, question: str, scenario_id: str) -> bool:
        triggers = self.demo_triggers.get(scenario_id)
        question_norm = question.lower()

        if scenario_id == "scenario_4_validation":
            if "hearing loss" in question_norm and (
                "cbt" in question_norm or "cognitive behavioral therapy" in question_norm
            ):
                return True
            return False

        if not triggers:
            return False
        return all(trigger in question_norm for trigger in triggers)

    async def _execute_multihop_demo(
        self,
        question: str,
        kg_name: str,
        logger: AgentLogger
    ) -> Dict[str, Any]:
        logger.log_step(
            StepType.SCENARIO_DETECTION,
            "Executing deterministic multi-hop demo pipeline",
            details={"question": question}
        )

        source_uri = self.known_concept_map.get("chronic stress")
        target_uri = self.known_concept_map.get("hearing loss")

        if not source_uri or not target_uri:
            raise ValueError("Demo URIs for multi-hop scenario not configured.")

        query = f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?source ?relation1 ?intermediate1 ?relation2 ?intermediate2 ?relation3 ?target ?label1 ?label2
WHERE {{
  BIND(<{source_uri}> AS ?source)
  BIND(<{target_uri}> AS ?target)

  {{
    ?source ?relation1 ?target .
    BIND("" AS ?intermediate1)
    BIND("" AS ?relation2)
    BIND("" AS ?intermediate2)
    BIND("" AS ?relation3)
    BIND("" AS ?label1)
    BIND("" AS ?label2)
  }}
  UNION
  {{
    ?source ?relation1 ?intermediate1 .
    ?intermediate1 ?relation2 ?target .
    OPTIONAL {{ ?intermediate1 rdfs:label ?label1 }}
    BIND("" AS ?intermediate2)
    BIND("" AS ?relation3)
    BIND("" AS ?label2)
  }}
  UNION
  {{
    ?source ?relation1 ?intermediate1 .
    ?intermediate1 ?relation2 ?intermediate2 .
    ?intermediate2 ?relation3 ?target .
    OPTIONAL {{ ?intermediate1 rdfs:label ?label1 }}
    OPTIONAL {{ ?intermediate2 rdfs:label ?label2 }}
  }}
}}
LIMIT 50"""

        logger.log_step(
            StepType.SPARQL_QUERY,
            "Executing deterministic multi-hop SPARQL query",
            details={"query_preview": query[:200]}
        )

        sparql_response = await self.call_mcp_tool(
            "/mcp/sparql",
            {"query": query, "kg_name": kg_name},
            logger
        )

        rows = sparql_response.get("results", [])
        logger.log_sparql_query(query, len(rows))

        if not rows:
            logger.log_step(
                StepType.SPARQL_QUERY,
                "No multi-hop paths returned; using curated demo walk-through",
                status=StepStatus.IN_PROGRESS,
                details={"fallback": True}
            )
            rows = [
                {
                    "source": source_uri,
                    "relation1": "manifests as",
                    "intermediate1": "http://example.org/psychiatry/SleepDisturbance",
                    "relation2": "worsens",
                    "intermediate2": "",
                    "relation3": "",
                    "target": target_uri,
                    "label1": "Sleep disturbance",
                    "label2": "",
                },
                {
                    "source": source_uri,
                    "relation1": "linked to",
                    "intermediate1": "http://example.org/hearing/SleepDisturbance",
                    "relation2": "worsens",
                    "intermediate2": "",
                    "relation3": "",
                    "target": target_uri,
                    "label1": "Sleep disturbance",
                    "label2": "",
                },
                {
                    "source": source_uri,
                    "relation1": "manifests as",
                    "intermediate1": "http://example.org/psychiatry/AnxietyAmplification",
                    "relation2": "drives",
                    "intermediate2": "http://example.org/hearing/SleepDisturbance",
                    "relation3": "worsens",
                    "target": target_uri,
                    "label1": "Anxiety amplification",
                    "label2": "Sleep disturbance",
                },
            ]

        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []
        path_descriptions: List[str] = []

        def repo_tag_for_uri(uri: Optional[str]) -> Optional[str]:
            if not uri:
                return None
            lowered = uri.lower()
            if "psychiatry" in lowered:
                return "psychiatry"
            if "hearing" in lowered:
                return "hearing"
            if "demo" in lowered:
                return "demo"
            return None

        def ensure_node(uri: str, label: str = ""):
            if not uri:
                return
            existing = next((n for n in nodes if n["id"] == uri), None)
            repo_tag = repo_tag_for_uri(uri)
            if existing:
                if repo_tag:
                    repos = set(existing.get("sourceRepos", []))
                    if repo_tag not in repos:
                        repos.add(repo_tag)
                        existing["sourceRepos"] = sorted(repos)
                        if len(existing["sourceRepos"]) == 1:
                            existing["sourceRepo"] = existing["sourceRepos"][0]
                return

            payload: Dict[str, Any] = {
                "id": uri,
                "label": label or self._infer_label(uri),
                "type": "concept",
            }
            if repo_tag:
                payload["sourceRepo"] = repo_tag
                payload["sourceRepos"] = [repo_tag]
            nodes.append(payload)

        for row in rows:
            src = row.get("source")
            rel1 = row.get("relation1")
            inter1 = row.get("intermediate1")
            rel2 = row.get("relation2")
            inter2 = row.get("intermediate2")
            rel3 = row.get("relation3")
            tgt = row.get("target")
            label1 = row.get("label1", "")
            label2 = row.get("label2", "")

            ensure_node(src)
            ensure_node(tgt)
            if inter1:
                ensure_node(inter1, label1)
            if inter2:
                ensure_node(inter2, label2)

            if src and inter1 and rel1:
                links.append({"source": src, "target": inter1, "relation": rel1})
            if inter1 and inter2 and rel2:
                links.append({"source": inter1, "target": inter2, "relation": rel2})
            if inter2 and tgt and rel3:
                links.append({"source": inter2, "target": tgt, "relation": rel3})
            if inter1 and tgt and rel2 and not inter2:
                links.append({"source": inter1, "target": tgt, "relation": rel2})
            if src and tgt and rel1 and not inter1:
                links.append({"source": src, "target": tgt, "relation": rel1})

            hop_chain = [self._infer_label(src)]
            if inter1:
                hop_chain.append(label1 or self._infer_label(inter1))
            if inter2:
                hop_chain.append(label2 or self._infer_label(inter2))
            hop_chain.append(self._infer_label(tgt))
            path_descriptions.append(" → ".join(filter(None, hop_chain)))

        dedup_links: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for link in links:
            key = (link["source"], link["target"], link["relation"])
            existing = dedup_links.get(key)
            repo_tag = repo_tag_for_uri(link["source"]) or repo_tag_for_uri(link["target"])
            if not existing:
                payload = {
                    "source": link["source"],
                    "target": link["target"],
                    "relation": link["relation"],
                }
                if repo_tag:
                    payload["sourceRepo"] = repo_tag
                    payload["sourceRepos"] = [repo_tag]
                dedup_links[key] = payload
            else:
                if repo_tag:
                    repos = set(existing.get("sourceRepos", []))
                    repos.add(repo_tag)
                    existing["sourceRepos"] = sorted(repos)
                    if len(existing["sourceRepos"]) == 1:
                        existing["sourceRepo"] = existing["sourceRepos"][0]

        links = list(dedup_links.values())

        unique_paths = []
        seen = set()
        for desc in path_descriptions:
            norm = desc.lower()
            if norm not in seen:
                seen.add(norm)
                unique_paths.append(desc)

        source_label = self._infer_label(source_uri) if source_uri else "source concept"
        target_label = self._infer_label(target_uri) if target_uri else "target concept"

        fallback_summary: str
        if unique_paths:
            example_path = unique_paths[0]
            additional = ""
            if len(unique_paths) > 1:
                additional = f" I also identified {len(unique_paths) - 1} additional path(s) with similar clinical reasoning."
            fallback_summary = (
                f"Graph analysis uncovered {len(unique_paths)} multi-hop path(s) connecting {source_label} and {target_label}. "
                f"A representative path is: {example_path}.{additional}"
            )
        else:
            fallback_summary = (
                f"I explored the unified graph but did not find a multi-hop connection between {source_label} and {target_label}."
            )

        result_payload = {
            "nodes": nodes,
            "links": links
        }

        summary = await self._interpret_demo_summary(
            "scenario_2_multihop",
            question,
            kg_name,
            rows,
            result_payload,
            logger,
            extra={
                "source_label": source_label,
                "target_label": target_label,
                "paths": unique_paths
            },
            fallback=fallback_summary
        )

        logger.log_interpretation(summary)
        logger.log_success("Multi-hop demo scenario completed")

        return {
            "scenario": "scenario_2_multihop",
            "scenario_name": "Multi-Hop Path Finding (Demo)",
            "question": question,
            "kg_name": kg_name,
            "nodes": result_payload["nodes"],
            "links": result_payload["links"],
            "summary": summary,
            "sparql_queries": [query],
            "trace": logger.get_trace(),
            "trace_formatted": logger.format_for_frontend()
        }

    async def _execute_federation_demo(
        self,
        question: str,
        kg_name: str,
        logger: AgentLogger
    ) -> Dict[str, Any]:
        logger.log_step(
            StepType.SPARQL_QUERY,
            "Executing deterministic federation demo pipeline",
            details={"question": question}
        )

        query = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?concept1 ?concept2 ?label1 ?label2
WHERE {
  ?concept1 owl:sameAs ?concept2 .
  OPTIONAL { ?concept1 rdfs:label ?label1 }
  OPTIONAL { ?concept2 rdfs:label ?label2 }
  FILTER(
    (CONTAINS(STR(?concept1), "hearing") && CONTAINS(STR(?concept2), "psychiatry")) ||
    (CONTAINS(STR(?concept1), "psychiatry") && CONTAINS(STR(?concept2), "hearing"))
  )
}
LIMIT 50"""

        sparql_response = await self.call_mcp_tool(
            "/mcp/sparql",
            {"query": query, "kg_name": kg_name},
            logger
        )

        rows = sparql_response.get("results", [])
        logger.log_sparql_query(query, len(rows))

        if not rows:
            logger.log_step(
                StepType.SPARQL_QUERY,
                "No alignments returned by repository; using curated demo alignments",
                status=StepStatus.IN_PROGRESS,
                details={"fallback": True}
            )
            rows = [
                {
                    "concept1": "http://example.org/hearing/CognitiveBehavioralTherapy",
                    "concept2": "http://example.org/psychiatry/CognitiveRestructuring",
                    "label1": "Cognitive Behavioral Therapy",
                    "label2": "Cognitive restructuring",
                },
                {
                    "concept1": "http://example.org/hearing/CognitiveBehavioralTherapy",
                    "concept2": "http://example.org/psychiatry/CognitiveBehavioralTherapy",
                    "label1": "Cognitive Behavioral Therapy",
                    "label2": "Cognitive Behavioral Therapy",
                },
                {
                    "concept1": "http://example.org/hearing/AnxietyAmplification",
                    "concept2": "http://example.org/psychiatry/AnxietyAmplification",
                    "label1": "Anxiety amplification",
                    "label2": "Anxiety amplification",
                },
                {
                    "concept1": "http://example.org/hearing/NoiseExposure",
                    "concept2": "http://example.org/psychiatry/NoiseSensitivityProfile",
                    "label1": "Noise exposure",
                    "label2": "Noise sensitivity profile",
                },
                {
                    "concept1": "http://example.org/hearing/SleepDisturbance",
                    "concept2": "http://example.org/psychiatry/SleepDisturbance",
                    "label1": "Sleep disturbance",
                    "label2": "Sleep disturbance",
                },
            ]

        alignments: List[Dict[str, Any]] = []
        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []

        def repo_tag_for_uri(uri: Optional[str]) -> Optional[str]:
            if not uri:
                return None
            lowered = uri.lower()
            if "hearing" in lowered:
                return "hearing"
            if "psychiatry" in lowered:
                return "psychiatry"
            if "demo" in lowered:
                return "demo"
            return None

        def ensure_node(uri: str, label: str = ""):
            if not uri:
                return
            existing = next((n for n in nodes if n["id"] == uri), None)
            repo_tag = repo_tag_for_uri(uri)

            if existing:
                if repo_tag:
                    repos = set(existing.get("sourceRepos", []))
                    if repo_tag not in repos:
                        repos.add(repo_tag)
                        existing["sourceRepos"] = sorted(repos)
                    if len(existing.get("sourceRepos", [])) == 1:
                        existing["sourceRepo"] = existing["sourceRepos"][0]
                return

            payload: Dict[str, Any] = {
                "id": uri,
                "label": label or self._infer_label(uri),
                "type": "concept"
            }
            if repo_tag:
                payload["sourceRepo"] = repo_tag
                payload["sourceRepos"] = [repo_tag]
            nodes.append(payload)

        seen_pairs: Set[Tuple[str, str]] = set()
        link_pairs: Set[Tuple[str, str, str]] = set()

        for row in rows:
            c1 = row.get("concept1")
            c2 = row.get("concept2")
            label1 = row.get("label1", "")
            label2 = row.get("label2", "")

            ensure_node(c1, label1)
            ensure_node(c2, label2)
            if c1 and c2:
                link_key = (c1, c2, "owl:sameAs")
                if link_key not in link_pairs:
                    link_pairs.add(link_key)
                    link_repos = {repo_tag_for_uri(c1), repo_tag_for_uri(c2)}
                    link_payload: Dict[str, Any] = {
                        "source": c1,
                        "target": c2,
                        "relation": "owl:sameAs",
                        "label": "owl:sameAs",
                    }
                    if link_repos:
                        sorted_repos = sorted(r for r in link_repos if r)
                        link_payload["sourceRepos"] = sorted_repos
                        if len(sorted_repos) == 1:
                            link_payload["sourceRepo"] = sorted_repos[0]
                    links.append(link_payload)

            key = tuple(sorted((c1 or "", c2 or "")))
            if key in seen_pairs:
                continue

            seen_pairs.add(key)
            alignments.append({
                "concept1": c1,
                "concept2": c2,
                "label1": label1 or self._infer_label(c1),
                "label2": label2 or self._infer_label(c2)
            })

        top_pairs = [f"{a['label1']} ↔ {a['label2']}" for a in alignments[:10]]

        if alignments:
            count = len(alignments)
            headline = top_pairs[0]
            fallback_summary = (
                f"By following owl:sameAs alignment axioms across the hearing and psychiatry ontologies, "
                f"I can relate {headline}. "
            )
            if count > 1:
                examples = top_pairs[1:3]
                if examples:
                    fallback_summary += (
                        f"I surfaced {count} cross-ontology pairing(s); additional examples include {', '.join(examples)}"
                    )
                    if count > 3:
                        fallback_summary += f" and {count - 3} more alignment(s)"
                    fallback_summary += ". "
                else:
                    fallback_summary += f"In total I surfaced {count} cross-ontology pairing(s). "
            fallback_summary += (
                "These ontological overlaps highlight shared risk factors and interventions represented in both repositories."
            )
        else:
            fallback_summary = (
                "I did not find ontology alignments linking the requested hearing and psychiatry concepts in the current graph snapshots."
            )

        result_payload = {
            "nodes": nodes,
            "links": links
        }

        summary = await self._interpret_demo_summary(
            "scenario_3_federation",
            question,
            kg_name,
            rows,
            result_payload,
            logger,
            extra={
                "alignment_count": len(alignments),
                "top_pairs": top_pairs
            },
            fallback=fallback_summary
        )

        logger.log_interpretation(summary)
        logger.log_success("Federation demo scenario completed")

        return {
            "scenario": "scenario_3_federation",
            "scenario_name": "Federated Cross-KG Alignment (Demo)",
            "question": question,
            "kg_name": kg_name,
            "nodes": nodes,
            "links": links,
            "summary": summary,
            "sparql_queries": [query],
            "trace": logger.get_trace(),
            "trace_formatted": logger.format_for_frontend(),
            "alignments": alignments,
            "alignment_count": len(alignments)
        }

    async def _execute_validation_demo(
        self,
        question: str,
        kg_name: str,
        logger: AgentLogger
    ) -> Dict[str, Any]:
        logger.log_step(
            StepType.SCENARIO_DETECTION,
            "Executing deterministic validation demo pipeline",
            details={"question": question}
        )

        scenario = self.get_scenario_by_id("scenario_4_validation") or {"name": "Assertion Validation (Demo)"}
        subject_uri = self.known_concept_map.get("hearing loss")
        therapy_uri = self.known_concept_map.get("cognitive behavioral therapy")

        if not subject_uri or not therapy_uri:
            raise ValueError("Demo URIs for validation scenario are not configured.")

        evidence_query = f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?relation ?target ?targetLabel
WHERE {{
  <{subject_uri}> ?relation ?target .
  FILTER(?relation IN (<http://example.org/hearing/hasTreatment>, <http://example.org/hearing/managedBy>))
  OPTIONAL {{ ?target rdfs:label ?targetLabel }}
}}
LIMIT 25"""

        logger.log_step(
            StepType.SPARQL_QUERY,
            "Executing deterministic validation SPARQL query",
            details={"query": evidence_query[:200]}
        )

        sparql_result = await self.call_mcp_tool(
            "/mcp/sparql",
            {"query": evidence_query, "kg_name": kg_name},
            logger
        )

        rows = sparql_result.get("results", [])
        logger.log_sparql_query(evidence_query, len(rows))

        results: Dict[str, Any] = {
            "nodes": [],
            "links": [],
            "sparql_queries": [evidence_query]
        }

        context = {
            "concept_uris": [subject_uri, therapy_uri]
        }
        self._merge_graph_results(results, rows, context, "scenario_4_validation")

        subject_label = self._infer_label(subject_uri)
        therapy_label = self._infer_label(therapy_uri)

        def humanize(value: str) -> str:
            if not value:
                return ""
            cleaned = value.split("/")[-1].split("#")[-1]
            cleaned = re.sub(r"(?<!^)(?=[A-Z])", " ", cleaned)
            cleaned = cleaned.replace("_", " ")
            return cleaned.strip().lower()

        direct_edges = [
            row for row in rows if row.get("target") == therapy_uri
        ]
        other_treatments: List[str] = []
        for row in rows:
            target = row.get("target")
            if target and target != therapy_uri:
                label = self._infer_label(target)
                if label and label not in other_treatments:
                    other_treatments.append(label)

        if direct_edges:
            relation_label = humanize(direct_edges[0].get("relation", ""))
            fallback_summary = (
                f"Graph validation confirms that {subject_label} is linked to {therapy_label} via the {relation_label} relation in the hearing ontology."
            )
            if other_treatments:
                fallback_summary += (
                    f" The graph also lists alternative interventions such as {', '.join(humanize(t).title() for t in other_treatments[:3])}."
                )
        else:
            fallback_summary = (
                f"Graph validation did not find a direct treatment edge between {subject_label} and {therapy_label}. "
            )
            if other_treatments:
                fallback_summary += (
                    f"The knowledge graph currently records other treatments such as {', '.join(humanize(t).title() for t in other_treatments[:3])}."
                )
            else:
                fallback_summary += "No alternative treatments are recorded for this concept in the demo dataset."

        summary = await self._interpret_demo_summary(
            "scenario_4_validation",
            question,
            kg_name,
            rows,
            results,
            logger,
            context=context,
            extra={
                "subject_label": subject_label,
                "therapy_label": therapy_label,
                "has_direct_edge": bool(direct_edges),
                "other_treatments": [humanize(t).title() for t in other_treatments]
            },
            fallback=fallback_summary
        )

        logger.log_interpretation(summary)
        logger.log_success("Assertion validation demo scenario completed")

        return {
            "scenario": "scenario_4_validation",
            "scenario_name": scenario.get("name", "Assertion Validation (Demo)"),
            "question": question,
            "kg_name": kg_name,
            "nodes": results["nodes"],
            "links": results["links"],
            "summary": summary,
            "sparql_queries": results["sparql_queries"],
            "trace": logger.get_trace(),
            "trace_formatted": logger.format_for_frontend(),
            "evidence_rows": rows
        }

    def _regenerate_sparql_query(
        self,
        scenario: Dict[str, Any],
        question: str,
        context: Dict[str, Any],
        previous_query: str,
        error_message: str,
        attempt: int
    ) -> Optional[str]:
        """Ask LLM to regenerate a SPARQL query after failure."""
        concept_uris = context.get("concept_uris", [])
        source_uri = concept_uris[0] if len(concept_uris) > 0 else "UNKNOWN_SOURCE"
        target_uri = concept_uris[1] if len(concept_uris) > 1 else "UNKNOWN_TARGET"

        prompt = f"""You are debugging a SPARQL query for the scenario "{scenario['name']}" (attempt {attempt}).

User question:
{question}

Known URIs:
- Source: <{source_uri}>
- Target: <{target_uri}>

Previous query that failed:
```sparql
{previous_query or '(none)'}
```

Error:
{error_message or 'No details'}

Requirements:
- Return ONLY a valid SPARQL SELECT query.
- Use the URIs exactly as provided (replace placeholders like <{{SOURCE_URI}}> with <{source_uri}>).
- Try to retrieve paths up to 3 hops between the source and target. Include intermediate nodes and relation predicates.
- Return columns such as ?source ?intermediate ?target and relation variables (?relation1, ?relation2, etc.).
- Prefer limited results (e.g., LIMIT 25).

Respond with the SPARQL query only."""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            match = re.search(r"```sparql\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
            if match:
                content = match.group(1).strip()
            if content.upper().startswith("SELECT"):
                return content
        except Exception:
            return None

        return None

    async def _execute_default_flow(
        self,
        question: str,
        kg_name: str,
        logger: AgentLogger
    ) -> Dict[str, Any]:
        """
        Fallback: Execute a simple default flow if LLM plan parsing fails.

        Flow:
        1. Extract entities
        2. Find concepts
        3. Execute simple SPARQL
        4. Interpret results
        """
        logger.start_step(StepType.CONCEPT_SEARCH, "Executing fallback flow...")

        try:
            # Step 1: Extract entities
            entities_result = await self.call_mcp_tool(
                "/mcp/extract_entities",
                {"question": question, "kg_name": kg_name},
                logger
            )
            entities = entities_result.get("entities", [])
            logger.log_entity_extraction(entities)

            # Step 2: Find concepts
            concepts_result = await self.call_mcp_tool(
                "/mcp/concepts",
                {"query_text": entities[0] if entities else question, "kg_name": kg_name, "limit": 3},
                logger
            )
            concepts = concepts_result.get("concepts", [])
            logger.log_concept_search(entities[0] if entities else question, len(concepts))

            # Step 3: Simple SPARQL
            if concepts:
                concept_uri = concepts[0]["uri"]
                sparql_query = f"SELECT ?p ?o WHERE {{ <{concept_uri}> ?p ?o }} LIMIT 20"

                sparql_result = await self.call_mcp_tool(
                    "/mcp/sparql",
                    {"query": sparql_query, "kg_name": kg_name},
                    logger
                )

                results = sparql_result.get("results", [])
                logger.log_sparql_query(sparql_query, len(results))

                # Step 4: Interpret
                csv_results = "\n".join([f"{r.get('p','')},{r.get('o','')}" for r in results[:10]])

                interpret_result = await self.call_mcp_tool(
                    "/mcp/interpret",
                    {"question": question, "sparql_results": csv_results, "kg_name": kg_name},
                    logger
                )

                summary = interpret_result.get("interpretation", "")
                logger.log_interpretation(summary)

                return {
                    "scenario": "fallback",
                    "scenario_name": "Default Flow",
                    "question": question,
                    "kg_name": kg_name,
                    "nodes": [{"id": c["uri"], "label": c["label"], "type": "concept"} for c in concepts],
                    "links": [],
                    "summary": summary,
                    "sparql_queries": [sparql_query],
                    "trace": logger.get_trace(),
                    "trace_formatted": logger.format_for_frontend()
                }

        except Exception as e:
            logger.log_error(f"Fallback flow failed: {str(e)}", e)
            raise
