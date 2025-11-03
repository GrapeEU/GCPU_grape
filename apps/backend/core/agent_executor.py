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
from typing import Callable, Dict, Any, List, Optional, Set, Tuple
from langchain_core.messages import HumanMessage

from core.config import settings
from core.agent_logger import AgentLogger, StepType, StepStatus
from core.vertex_ai_config import get_vertex_ai_chat_model
import core.demo_pipelines as demo_pipelines


class AgentExecutor:
    """
    Executes scenarios by orchestrating MCP tool calls.

    The executor:
    - Loads scenario prompts from JSON files
    - Uses Gemini LLM to decide which MCP tools to call
    - Executes MCP tools via HTTP
    - Logs each step for debugging and UX display
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        llm: Optional[Any] = None,
    ):
        self.base_url = base_url
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        self.scenarios = self._load_scenarios()

        self.scenarios = {
            sid: data for sid, data in self.scenarios.items()
            if sid != "scenario_3_federation"
        }
        if "scenario_4_validation" in self.scenarios:
            self.scenarios["scenario_4_validation"]["name"] = "S3 – Validation ontologique"

        self.scenario_templates: Dict[str, Callable[[Dict[str, Any]], Optional[str]]] = {
            "scenario_1_neighbourhood": self._template_neighbourhood_query,
            "scenario_2_multihop": self._template_multihop_query,
            "scenario_4_validation": self._template_validation_query,
        }

        self.known_concept_map = {
            "chronic stress": "http://example.org/psychiatry/ChronicStress",
            "hearing loss": "http://example.org/hearing/HearingLoss",
            "tinnitus": "http://example.org/hearing/Tinnitus",
            "generalized anxiety disorder": "http://example.org/psychiatry/GeneralizedAnxietyDisorder",
            "hyperacusis": "http://example.org/hearing/Hyperacusis",
            "cognitive behavioral therapy": "http://example.org/hearing/CognitiveBehavioralTherapy",
            "cbt": "http://example.org/hearing/CognitiveBehavioralTherapy",
        }

        self.demo_questions: Dict[str, str] = {}

        self.prefix_map = {
            "exhear": "http://example.org/hearing/",
            "expsych": "http://example.org/psychiatry/",
            "exmed": "http://example.org/medical/",
            "excommon": "http://example.org/common/",
        }

        # Initialize Vertex AI LLM for orchestration
        self.llm = llm or get_vertex_ai_chat_model(
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
        logger: Optional[AgentLogger] = None,
        demo_id: Optional[str] = None,
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
            "question": question,
            "demo_id": demo_id,
        }

        demo_response = self._handle_demo_request(
            demo_id=demo_id,
            scenario_id=scenario_id,
            question=question,
            kg_name=kg_name,
            logger=logger,
        )
        if demo_response:
            return demo_response

        scenario = self.get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_id}")

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
                if isinstance(payload, dict):
                    payload.setdefault("kg_name", kg_name)

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
                        if tool == "/mcp/interpret":
                            tool_result = await self._handle_interpret_request(
                                payload,
                                question,
                                results,
                                context,
                                scenario_id,
                                kg_name,
                                logger,
                            )
                            break

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

                        best_concept = self._select_best_concept(query_text, concepts, logger)
                        if best_concept:
                            best_uri = self._expand_uri(best_concept.get("uri"))
                            if best_uri and best_uri not in context["concept_uris"]:
                                context["concept_uris"].append(best_uri)
                                logger.log_step(
                                    StepType.CONCEPT_SEARCH,
                                    f"Selected concept for '{query_text}'",
                                    details={"uri": best_uri, "label": best_concept.get("label")}
                                )
                        else:
                            logger.log_step(
                                StepType.CONCEPT_SEARCH,
                                f"No confident concept match for '{query_text}'",
                                details={"candidates": len(concepts)}
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

            logger.log_success(f"Scenario '{scenario['name']}' completed successfully")

            final_payload = {
                "scenario": scenario_id,
                "scenario_name": scenario["name"],
                "question": question,
                "kg_name": kg_name,
                **results,
                "trace": logger.get_trace(),
                "trace_formatted": logger.format_for_frontend()
            }
            return final_payload

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

    def _handle_demo_request(
        self,
        demo_id: Optional[str],
        scenario_id: str,
        question: str,
        kg_name: str,
        logger: AgentLogger,
    ) -> Optional[Dict[str, Any]]:
        """Handle new hard-coded demo pipelines (S1/S2/S3/Wow)."""
        if not demo_id:
            return None

        repo_key = (kg_name or "grape_unified").replace("grape_", "")
        if repo_key not in {"demo", "hearing", "psychiatry", "unified"}:
            repo_key = "unified"

        base_payload = {
            "scenario": demo_id,
            "scenario_name": demo_id,
            "question": question,
            "kg_name": kg_name,
            "nodes": [],
            "links": [],
            "sparql_queries": [],
            "repo": repo_key,
        }

        if demo_id == "S1_PATIENT":
            logger.log_step(
                StepType.SCENARIO_DETECTION,
                "Demo guidee selectionnee : Vue Patient (S1)",
                details={"demo_id": demo_id},
            )
            results, trace, queries = demo_pipelines.run_s1_patient_explore(
                "expat:PatientJohn", repo_key=repo_key
            )
            nodes, links = self._graph_s1_patient()
            summary = self._llm_demo_summary(
                logger,
                title="Patient overview",
                instructions=(
                    "Structure the response as four numbered bullet points: "
                    "(1) recap who the patient is, "
                    "(2) list the key history and current treatments, "
                    "(3) highlight the present symptom, "
                    "(4) end with the clinical question to investigate. "
                    "Keep the tone concise and professional."
                ),
                structured_payload={"patient_uri": "expat:PatientJohn", "facts": results},
                fallback=self._summarize_patient_results(results, "expat:PatientJohn"),
                question=question,
            )
            logger.log_success("Demo S1 terminee")
            return {
                **base_payload,
                "scenario": "DEMO_S1_PATIENT",
                "scenario_name": "1. Vue Patient",
                "summary": summary,
                "sparql_queries": queries,
                "nodes": nodes,
                "links": links,
                "trace": logger.get_trace(),
                "trace_formatted": logger.format_for_frontend(),
            }

        if demo_id == "S2_PATHFINDING":
            logger.log_step(
                StepType.SCENARIO_DETECTION,
                "Demo guidee selectionnee : Liens caches (S2)",
                details={"demo_id": demo_id},
            )
            paths, trace, queries = demo_pipelines.run_s2_pathfinding(
                "exdrug:E27B", "excommon:AbdominalPain", repo_key=repo_key
            )
            nodes, links = self._graph_s2_pathfinding()
            summary = self._llm_demo_summary(
                logger,
                title="Hidden path analysis",
                instructions=(
                    "Begin with a short paragraph describing how substance E27B may lead to abdominal pain. "
                    "Then list both discovered paths as bullet points (format '- Path: node1 → relation → node2 → …'). "
                    "Finish with one sentence identifying which path is most critical for the patient."
                ),
                structured_payload={
                    "substance": "exdrug:E27B",
                    "symptom": "excommon:AbdominalPain",
                    "paths": paths,
                },
                fallback=self._summarize_path_results(paths, "exdrug:E27B", "excommon:AbdominalPain"),
                question=question,
            )
            logger.log_success("Demo S2 terminee")
            return {
                **base_payload,
                "scenario": "DEMO_S2_PATHFINDING",
                "scenario_name": "2. Liens Caches",
                "summary": summary,
                "sparql_queries": queries,
                "nodes": nodes,
                "links": links,
                "trace": logger.get_trace(),
                "trace_formatted": logger.format_for_frontend(),
            }

        if demo_id == "S3_VALIDATION":
            logger.log_step(
                StepType.SCENARIO_DETECTION,
                "Demo guidee selectionnee : Validation (S3)",
                details={"demo_id": demo_id},
            )
            result, trace, queries = demo_pipelines.run_s3_validation(
                "expat:PatientJohn", "exmed:Metamorphine", repo_key=repo_key
            )
            nodes, links = self._graph_s3_validation()
            summary = self._llm_demo_summary(
                logger,
                title="Ontology validation",
                instructions=(
                    "State clearly whether Metamorphine is contraindicated for the patient. "
                    "In no more than two sentences, explain how the propertyChainAxiom propagates the contraindication from substance E27B to the drug. "
                    "Conclude with the recommended alternative and, if relevant, a brief clinical recommendation."
                ),
                structured_payload={
                    "patient": "expat:PatientJohn",
                    "drug": "exmed:Metamorphine",
                    "result": result,
                    "trace": trace,
                },
                fallback=self._summarize_validation(result, "exmed:Metamorphine"),
                question=question,
            )
            logger.log_success("Demo S3 terminee")
            return {
                **base_payload,
                "scenario": "DEMO_S3_VALIDATION",
                "scenario_name": "3. Validation",
                "summary": summary,
                "sparql_queries": queries,
                "nodes": nodes,
                "links": links,
                "trace": logger.get_trace(),
                "trace_formatted": logger.format_for_frontend(),
            }

        if demo_id == "AUTONOMOUS_DEMO":
            logger.log_step(
                StepType.SCENARIO_DETECTION,
                "Demo autonome complete declenchee",
                details={"demo_id": demo_id, "scenario_id": scenario_id},
            )
            fallback_summary, trace_list, queries, storyboard = demo_pipelines.run_autonomous_demo(
                "expat:PatientJohn", repo_key=repo_key
            )
            llm_summary = self._llm_demo_summary(
                logger,
                title="Autonomous analysis",
                instructions=(
                    "Narrate the investigation in three titled sections (e.g. 'Phase 1 – Patient', 'Phase 2 – Substance', 'Phase 3 – Verdict'), each limited to two sentences. "
                    "Highlight the pharmacological conflict and finish with the proposed alternative."
                ),
                structured_payload=storyboard,
                fallback=fallback_summary,
                question=question,
            )
            logger.log_success("Demo autonome terminee")
            nodes, links = self._build_graph_from_sparql(queries, repo_key)
            if not nodes or len(nodes) == 0:
                nodes, links = self._demo_full_graph()
            return {
                **base_payload,
                "scenario": "DEMO_AUTONOMOUS",
                "scenario_name": "Analyse Complete",
                "summary": llm_summary,
                "sparql_queries": queries,
                "nodes": nodes,
                "links": links,
                "trace": logger.get_trace(),
                "trace_formatted": logger.format_for_frontend(),
            }

        if demo_id == "DEEP_REASONING":
            logger.log_step(
                StepType.SCENARIO_DETECTION,
                "Pipeline Deep Reasoning déclenchée",
                details={"demo_id": demo_id},
            )
            fallback_summary, trace_list, queries, storyboard = demo_pipelines.run_deep_reasoning_demo(
                "expat:PatientJohn", repo_key=repo_key
            )

            # Générer la liste de graphes pour le slider
            graph_steps = self._generate_deep_reasoning_steps()

            # Le graphe principal est le dernier de la liste
            nodes = graph_steps[-1]["nodes"]
            links = graph_steps[-1]["links"]

            llm_summary = self._llm_demo_summary(
                logger,
                title="Deep Reasoning Pipeline",
                instructions=(
                    "Present the reasoning as six numbered steps: "
                    "(1) patient profile, (2) current medication, (3) substance analysis, "
                    "(4) symptom pathways, (5) contraindication validation, (6) final recommendation. "
                    "Each step should fit in a single short sentence and end with the substitution advice."
                ),
                structured_payload=storyboard,
                fallback=fallback_summary,
                question=question,
            )

            logger.log_success("Deep Reasoning demo terminée")
            return {
                **base_payload,
                "scenario": "DEMO_DEEP_REASONING",
                "scenario_name": "Deep Reasoning",
                "summary": llm_summary,
                "sparql_queries": queries,
                "nodes": nodes,
                "links": links,
                "graph_steps": graph_steps,
                "trace": logger.get_trace(),
                "trace_formatted": logger.format_for_frontend(),
            }

        return None

    @staticmethod
    def _summarize_patient_results(results: List[Dict[str, str]], patient_uri: str) -> str:
        """Format patient neighbourhood results into a short markdown summary."""
        if not results:
            return f"### Vue Patient ({patient_uri})\nAucun fait n'a ete retrouve."

        lines = [
            f"- **{row.get('prop_label', '').strip()}** : {row.get('value_label', '').strip()}"
            for row in results
            if row
        ]
        body = "\n".join(lines)
        return f"### Vue Patient ({patient_uri})\n{body}"

    @staticmethod
    def _summarize_path_results(paths: List[str], substance_uri: str, symptom_uri: str) -> str:
        """Format multi-hop paths for display."""
        if not paths:
            return f"Aucun chemin detecte entre `{substance_uri}` et `{symptom_uri}`."

        body = "\n".join(f"- {path}" for path in paths)
        return (
            f"### Liens detectes entre `{substance_uri}` et `{symptom_uri}`\n"
            f"{body}"
        )

    @staticmethod
    def _summarize_validation(result: Dict[str, str], drug_uri: str) -> str:
        """Format validation outcome and alternative recommendation."""
        status = result.get("validation", "INCONNU")
        reason = result.get("reason", "Aucune justification disponible.")
        alternative = result.get("alternative", "Aucune alternative trouvee.")
        return (
            f"### Validation ontologique pour `{drug_uri}`\n"
            f"- Statut : **{status}**\n"
            f"- Justification : {reason}\n"
            f"- Alternative proposee : {alternative}\n"
        )

    def _llm_demo_summary(
        self,
        logger: AgentLogger,
        title: str,
        instructions: str,
        structured_payload: Dict[str, Any],
        fallback: str = "",
        question: str = ""
    ) -> str:
        """Use the LLM to craft a rich narrative for demo outputs."""
        try:
            prompt = (
                "You are Grape, the semantic medical agent. Follow the instructions exactly.\n"
                f"Expected title: {title}.\n"
                f"Instructions: {instructions}\n"
                f"Original question: {question or 'Not provided'}\n"
                "Language rule: answer in the same language as the question if it is identifiable; otherwise respond in English.\n"
                "Raw data (JSON follows):\n"
                f"{json.dumps(structured_payload, ensure_ascii=False, indent=2)}\n"
            )
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = (response.content or "").strip()
            if content:
                logger.log_interpretation(content)
                return content
        except Exception as exc:  # pragma: no cover - defensive
            logger.log_step(
                StepType.RESULT_INTERPRETATION,
                "LLM indisponible pour la synthese demo, utilisation du fallback",
                status=StepStatus.IN_PROGRESS,
                details={"error": str(exc)}
            )
        return fallback or "Summary unavailable for this demo."

    @staticmethod
    def _build_patient_graph(
        results: List[Dict[str, str]],
        central_uri: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not results:
            return [], []
        nodes: Dict[str, Dict[str, Any]] = {
            central_uri: {"id": central_uri, "label": "PatientJohn", "type": "patient"}
        }
        links: List[Dict[str, Any]] = []
        for idx, row in enumerate(results, start=1):
            relation_label = row.get("prop_label", f"relation_{idx}")
            target_label = row.get("value_label", f"valeur_{idx}")
            target_id = row.get("value") or f"{central_uri}::{idx}"
            nodes[target_id] = {
                "id": target_id,
                "label": target_label,
                "type": "concept",
            }
            links.append({
                "source": central_uri,
                "target": target_id,
                "label": relation_label,
            })
        return list(nodes.values()), links

    def _build_graph_from_sparql(
        self,
        queries: List[str],
        repo_key: str = "unified"
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Construit un graphe à partir des requêtes SPARQL en exécutant des requêtes
        de voisinage autour des concepts mentionnés.
        """
        from core.sparql_utils import run_sparql_query
        import re

        nodes_dict: Dict[str, Dict[str, Any]] = {}
        links_list: List[Dict[str, Any]] = []

        # Extraire tous les URIs des requêtes
        focus_uris = set()

        # Préfixes de base
        prefix_map = {
            "expat": "http://example.org/patient/",
            "exmed": "http://example.org/medication/",
            "exdrug": "http://example.org/drug/",
            "excond": "http://example.org/condition/",
            "excommon": "http://example.org/common/"
        }

        for query in queries:
            # Chercher les URIs dans la forme <http://...>
            for match in re.finditer(r'<(http://example\.org/[^>]+)>', query):
                focus_uris.add(f"<{match.group(1)}>")
            # Chercher les préfixes (expat:, exmed:, etc.)
            for match in re.finditer(r'\b(expat|exmed|exdrug|excond|excommon):([A-Za-z0-9_]+)', query):
                prefix = match.group(1)
                local_name = match.group(2)
                # Convertir en URI complet
                if prefix in prefix_map:
                    full_uri = f"<{prefix_map[prefix]}{local_name}>"
                    focus_uris.add(full_uri)

        # Pour chaque URI, récupérer ses voisins
        for uri in focus_uris:
            # Requête pour les relations sortantes
            neighbourhood_query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?source ?relation ?target ?sourceLabel ?targetLabel ?relationLabel
            WHERE {{
              {{
                {uri} ?relation ?target .
                FILTER(isURI(?target))
                BIND({uri} AS ?source)
              }}
              UNION
              {{
                ?source ?relation {uri} .
                FILTER(isURI(?source))
                BIND({uri} AS ?target)
              }}
              OPTIONAL {{ ?source rdfs:label ?sourceLabel }}
              OPTIONAL {{ ?target rdfs:label ?targetLabel }}
              OPTIONAL {{ ?relation rdfs:label ?relationLabel }}
            }}
            LIMIT 50
            """

            try:
                results = run_sparql_query(repo_key, neighbourhood_query)
                if isinstance(results, list):
                    for row in results:
                        source = row.get("source", "")
                        target = row.get("target", "")
                        relation = row.get("relation", "")

                        if not source or not target or not relation:
                            continue

                        # Ajouter les nœuds
                        if source not in nodes_dict:
                            nodes_dict[source] = {
                                "id": source,
                                "label": row.get("sourceLabel") or source.split("/")[-1].split(":")[-1],
                                "type": self._infer_node_type(source)
                            }
                        if target not in nodes_dict:
                            nodes_dict[target] = {
                                "id": target,
                                "label": row.get("targetLabel") or target.split("/")[-1].split(":")[-1],
                                "type": self._infer_node_type(target)
                            }

                        # Ajouter le lien
                        relation_label = row.get("relationLabel") or relation.split("/")[-1].split(":")[-1]
                        links_list.append({
                            "source": source,
                            "target": target,
                            "label": relation_label,
                            "relation": relation
                        })
            except Exception as e:
                print(f"[WARN] Failed to fetch neighbourhood for {uri}: {e}")
                continue

        return list(nodes_dict.values()), links_list

    def _infer_node_type(self, uri: str) -> str:
        """Inférer le type de nœud à partir de l'URI."""
        if "patient" in uri.lower():
            return "patient"
        elif "medication" in uri.lower() or "med:" in uri:
            return "medication"
        elif "drug:" in uri or "substance" in uri.lower():
            return "substance"
        elif "condition" in uri.lower() or "cond:" in uri:
            return "condition"
        elif "symptom" in uri.lower() or "pain" in uri.lower() or "discomfort" in uri.lower():
            return "symptom"
        elif "procedure" in uri.lower() or "ectomy" in uri.lower():
            return "procedure"
        elif "organ" in uri.lower() or "kidney" in uri.lower() or "liver" in uri.lower():
            return "organ"
        return "entity"

    def _graph_s1_patient(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Graphe S1 : Vue complète du patient John"""
        nodes: Dict[str, Dict[str, Any]] = {
            "expat:PatientJohn": {"id": "expat:PatientJohn", "label": "Patient John", "type": "patient"},
            "excond:DiabetesMellitus": {"id": "excond:DiabetesMellitus", "label": "Diabetes Mellitus", "type": "condition"},
            "excond:Hypertension": {"id": "excond:Hypertension", "label": "Hypertension", "type": "condition"},
            "excond:ChronicKidneyDisease": {"id": "excond:ChronicKidneyDisease", "label": "Chronic Kidney Disease", "type": "condition"},
            "excond:Nephrectomy2005": {"id": "excond:Nephrectomy2005", "label": "Nephrectomy (2005)", "type": "procedure"},
            "excommon:AbdominalPain": {"id": "excommon:AbdominalPain", "label": "Abdominal Pain", "type": "symptom"},
            "excommon:Fatigue": {"id": "excommon:Fatigue", "label": "Fatigue", "type": "symptom"},
            "exmed:Metamorphine": {"id": "exmed:Metamorphine", "label": "Metamorphine", "type": "medication"},
            "exmed:Lisinopril": {"id": "exmed:Lisinopril", "label": "Lisinopril", "type": "medication"},
            "exmed:Atorvastatin": {"id": "exmed:Atorvastatin", "label": "Atorvastatin", "type": "medication"},
        }

        def edge(source: str, relation: str, target: str) -> Dict[str, Any]:
            return {"source": source, "target": target, "label": relation}

        links: List[Dict[str, Any]] = [
            edge("expat:PatientJohn", "hasCondition", "excond:DiabetesMellitus"),
            edge("expat:PatientJohn", "hasCondition", "excond:Hypertension"),
            edge("expat:PatientJohn", "hasCondition", "excond:ChronicKidneyDisease"),
            edge("expat:PatientJohn", "hasProcedure", "excond:Nephrectomy2005"),
            edge("expat:PatientJohn", "hasSymptom", "excommon:AbdominalPain"),
            edge("expat:PatientJohn", "hasSymptom", "excommon:Fatigue"),
            edge("expat:PatientJohn", "takesMedication", "exmed:Metamorphine"),
            edge("expat:PatientJohn", "takesMedication", "exmed:Lisinopril"),
            edge("expat:PatientJohn", "takesMedication", "exmed:Atorvastatin"),
        ]

        return list(nodes.values()), links

    def _graph_s2_pathfinding(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Graphe S2 : Les 2 chemins entre E27B et AbdominalPain"""
        nodes: Dict[str, Dict[str, Any]] = {
            "exdrug:E27B": {"id": "exdrug:E27B", "label": "Substance E27B", "type": "substance"},
            "excommon:StomachDiscomfort": {"id": "excommon:StomachDiscomfort", "label": "Stomach Discomfort", "type": "symptom"},
            "excommon:AbdominalPain": {"id": "excommon:AbdominalPain", "label": "Abdominal Pain", "type": "symptom"},
            "excond:PostNephrectomyStatus": {"id": "excond:PostNephrectomyStatus", "label": "Post-Nephrectomy Status", "type": "condition"},
        }

        def edge(source: str, relation: str, target: str) -> Dict[str, Any]:
            return {"source": source, "target": target, "label": relation}

        links: List[Dict[str, Any]] = [
            # Chemin 1: E27B → causesSymptom → StomachDiscomfort → semanticallySimilarTo → AbdominalPain
            edge("exdrug:E27B", "causesSymptom", "excommon:StomachDiscomfort"),
            edge("excommon:StomachDiscomfort", "semanticallySimilarTo", "excommon:AbdominalPain"),
            # Chemin 2: E27B → contraindicatedFor → PostNephrectomyStatus → typicalSymptom → AbdominalPain
            edge("exdrug:E27B", "contraindicatedFor", "excond:PostNephrectomyStatus"),
            edge("excond:PostNephrectomyStatus", "typicalSymptom", "excommon:AbdominalPain"),
        ]

        return list(nodes.values()), links

    def _graph_s3_validation(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Graphe S3 : Validation + alternative"""
        nodes: Dict[str, Dict[str, Any]] = {
            "expat:PatientJohn": {"id": "expat:PatientJohn", "label": "Patient John", "type": "patient"},
            "excond:Nephrectomy2005": {"id": "excond:Nephrectomy2005", "label": "Nephrectomy (2005)", "type": "procedure"},
            "excond:PostNephrectomyStatus": {"id": "excond:PostNephrectomyStatus", "label": "Post-Nephrectomy Status", "type": "condition"},
            "exmed:Metamorphine": {"id": "exmed:Metamorphine", "label": "Metamorphine ⚠️", "type": "medication"},
            "exdrug:E27B": {"id": "exdrug:E27B", "label": "Substance E27B", "type": "substance"},
            "excond:DiabetesMellitus": {"id": "excond:DiabetesMellitus", "label": "Diabetes Mellitus", "type": "condition"},
            "exmed:Glucorin": {"id": "exmed:Glucorin", "label": "Glucorin ✓", "type": "medication"},
        }

        def edge(source: str, relation: str, target: str) -> Dict[str, Any]:
            return {"source": source, "target": target, "label": relation}

        links: List[Dict[str, Any]] = [
            # Patient status
            edge("expat:PatientJohn", "hasProcedure", "excond:Nephrectomy2005"),
            edge("excond:Nephrectomy2005", "resultsInCondition", "excond:PostNephrectomyStatus"),
            edge("expat:PatientJohn", "hasCondition", "excond:DiabetesMellitus"),
            # Metamorphine contraindication
            edge("exmed:Metamorphine", "hasActiveSubstance", "exdrug:E27B"),
            edge("exdrug:E27B", "contraindicatedFor", "excond:PostNephrectomyStatus"),
            edge("exmed:Metamorphine", "contraindicatedFor", "excond:PostNephrectomyStatus"),
            edge("exmed:Metamorphine", "indicatedFor", "excond:DiabetesMellitus"),
            # Alternative
            edge("exmed:Glucorin", "indicatedFor", "excond:DiabetesMellitus"),
        ]

        return list(nodes.values()), links

    def _demo_full_graph(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Graphe hardcodé (fallback)."""
        nodes: Dict[str, Dict[str, Any]] = {
            "expat:PatientJohn": {"id": "expat:PatientJohn", "label": "Patient John", "type": "patient"},
            "exmed:Metamorphine": {"id": "exmed:Metamorphine", "label": "Metamorphine", "type": "medication"},
            "exdrug:E27B": {"id": "exdrug:E27B", "label": "Substance E27B", "type": "substance"},
            "excond:PostNephrectomyStatus": {"id": "excond:PostNephrectomyStatus", "label": "Post-Nephrectomy Status", "type": "condition"},
            "excommon:StomachDiscomfort": {"id": "excommon:StomachDiscomfort", "label": "Stomach Discomfort", "type": "symptom"},
            "excommon:AbdominalPain": {"id": "excommon:AbdominalPain", "label": "Abdominal Pain", "type": "symptom"},
            "excond:Nephrectomy2005": {"id": "excond:Nephrectomy2005", "label": "Nephrectomy (2005)", "type": "procedure"},
            "excond:DiabetesMellitus": {"id": "excond:DiabetesMellitus", "label": "Diabetes Mellitus", "type": "condition"},
            "exmed:Glucorin": {"id": "exmed:Glucorin", "label": "Glucorin", "type": "medication"},
        }

        def edge(source: str, relation: str, target: str) -> Dict[str, Any]:
            return {"source": source, "target": target, "label": relation}

        links: List[Dict[str, Any]] = [
            edge("expat:PatientJohn", "hasCondition", "excond:DiabetesMellitus"),
            edge("expat:PatientJohn", "hasProcedure", "excond:Nephrectomy2005"),
            edge("expat:PatientJohn", "hasSymptom", "excommon:AbdominalPain"),
            edge("expat:PatientJohn", "takesMedication", "exmed:Metamorphine"),
            edge("excond:Nephrectomy2005", "resultsInCondition", "excond:PostNephrectomyStatus"),
            edge("exmed:Metamorphine", "hasActiveSubstance", "exdrug:E27B"),
            edge("exmed:Metamorphine", "indicatedFor", "excond:DiabetesMellitus"),
            edge("exdrug:E27B", "causesSymptom", "excommon:StomachDiscomfort"),
            edge("excommon:StomachDiscomfort", "semanticallySimilarTo", "excommon:AbdominalPain"),
            edge("exdrug:E27B", "contraindicatedFor", "excond:PostNephrectomyStatus"),
            edge("excond:PostNephrectomyStatus", "typicalSymptom", "excommon:AbdominalPain"),
            edge("exmed:Metamorphine", "contraindicatedFor", "excond:PostNephrectomyStatus"),
            edge("exmed:Glucorin", "indicatedFor", "excond:DiabetesMellitus"),
        ]

        return list(nodes.values()), links

    def _generate_deep_reasoning_steps(self) -> List[Dict[str, Any]]:
        """Génère la liste de graphes pour le Deep Reasoning (slider)"""

        # Étape 1: Patient John
        step1_nodes, step1_links = self._graph_s1_patient()

        # Étape 2: Médicament Metamorphine
        step2_nodes = [
            {"id": "exmed:Metamorphine", "label": "Metamorphine", "type": "medication"},
            {"id": "exdrug:E27B", "label": "Substance E27B", "type": "substance"},
            {"id": "excond:DiabetesMellitus", "label": "Diabetes Mellitus", "type": "condition"},
        ]
        step2_links = [
            {"source": "exmed:Metamorphine", "target": "exdrug:E27B", "label": "hasActiveSubstance"},
            {"source": "exmed:Metamorphine", "target": "excond:DiabetesMellitus", "label": "indicatedFor"},
        ]

        # Étape 3: Substance E27B et effets
        step3_nodes = [
            {"id": "exdrug:E27B", "label": "Substance E27B", "type": "substance"},
            {"id": "excommon:StomachDiscomfort", "label": "Stomach Discomfort", "type": "symptom"},
            {"id": "excommon:Nausea", "label": "Nausea", "type": "symptom"},
            {"id": "excond:PostNephrectomyStatus", "label": "Post-Nephrectomy Status", "type": "condition"},
            {"id": "excommon:Kidney", "label": "Kidney", "type": "organ"},
        ]
        step3_links = [
            {"source": "exdrug:E27B", "target": "excommon:StomachDiscomfort", "label": "causesSymptom"},
            {"source": "exdrug:E27B", "target": "excommon:Nausea", "label": "causesSymptom"},
            {"source": "exdrug:E27B", "target": "excond:PostNephrectomyStatus", "label": "contraindicatedFor"},
            {"source": "exdrug:E27B", "target": "excommon:Kidney", "label": "affectsOrgan"},
        ]

        # Étape 4: Chemins E27B → AbdominalPain
        step4_nodes, step4_links = self._graph_s2_pathfinding()

        # Étape 5: Validation avec contre-indication
        step5_nodes, step5_links = self._graph_s3_validation()

        # Étape 6: Graphe final avec alternative
        step6_nodes = [
            {"id": "expat:PatientJohn", "label": "Patient John", "type": "patient"},
            {"id": "excond:DiabetesMellitus", "label": "Diabetes Mellitus", "type": "condition"},
            {"id": "exmed:Metamorphine", "label": "Metamorphine ⚠️", "type": "medication"},
            {"id": "exmed:Glucorin", "label": "Glucorin ✓ SAFE", "type": "medication"},
            {"id": "excond:PostNephrectomyStatus", "label": "Post-Nephrectomy Status", "type": "condition"},
        ]
        step6_links = [
            {"source": "expat:PatientJohn", "target": "excond:DiabetesMellitus", "label": "hasCondition"},
            {"source": "expat:PatientJohn", "target": "excond:PostNephrectomyStatus", "label": "hasCondition"},
            {"source": "exmed:Metamorphine", "target": "excond:DiabetesMellitus", "label": "indicatedFor"},
            {"source": "exmed:Metamorphine", "target": "excond:PostNephrectomyStatus", "label": "CONTRAINDICATED"},
            {"source": "exmed:Glucorin", "target": "excond:DiabetesMellitus", "label": "indicatedFor"},
        ]

        return [
            {"title": "Step 1: Patient John Medical Record", "nodes": step1_nodes, "links": step1_links},
            {"title": "Step 2: Current Medication (Metamorphine)", "nodes": step2_nodes, "links": step2_links},
            {"title": "Step 3: Substance E27B Analysis", "nodes": step3_nodes, "links": step3_links},
            {"title": "Step 4: Paths to Abdominal Pain", "nodes": step4_nodes, "links": step4_links},
            {"title": "Step 5: Validation and Contraindication", "nodes": step5_nodes, "links": step5_links},
            {"title": "Step 6: Final Recommendation", "nodes": step6_nodes, "links": step6_links},
        ]

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

        upper_query = query.upper()
        if "CONSTRUCT" in upper_query and "SELECT" not in upper_query:
            fallback_query = self._build_fallback_sparql(scenario_id, context, kg_name)
            if fallback_query:
                query = fallback_query

        if self._should_apply_template(query):
            template_fn = self.scenario_templates.get(scenario_id)
            if template_fn:
                template_query = template_fn({
                    "concept_uris": concept_uris,
                    "payload": payload,
                    "kg_name": kg_name,
                    "context": context,
                })
                if template_query:
                    query = template_query

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

    @staticmethod
    def _should_apply_template(query: str) -> bool:
        if not query or not query.strip():
            return True

        template_markers = (
            "{{SOURCE_URI}}",
            "{{TARGET_URI}}",
            "{{CONCEPT_URI}}",
            "<SOURCE_URI>",
            "<TARGET_URI>",
            "<CONCEPT_URI>",
            "__USE_TEMPLATE__",
        )
        if any(marker in query for marker in template_markers):
            return True

        stripped = query.lstrip()
        upper = stripped.upper()
        if not upper.startswith("SELECT") and not upper.startswith("ASK") and not upper.startswith("CONSTRUCT"):
            return True

        return False

    def _template_neighbourhood_query(self, data: Dict[str, Any]) -> Optional[str]:
        concept_uris = data.get("concept_uris", [])
        if not concept_uris:
            return None

        focus_uri = concept_uris[0]
        return f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?source ?relation ?target ?sourceLabel ?targetLabel
WHERE {{
  VALUES ?source {{ <{focus_uri}> }}
  ?source ?relation ?target .
  OPTIONAL {{ ?source rdfs:label ?sourceLabel }}
  OPTIONAL {{ ?target rdfs:label ?targetLabel }}
}}
LIMIT 100"""

    def _template_multihop_query(self, data: Dict[str, Any]) -> Optional[str]:
        concept_uris = data.get("concept_uris", [])
        if len(concept_uris) < 2:
            return None

        source_uri, target_uri = concept_uris[0], concept_uris[1]
        return f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
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

    def _template_federation_query(self, data: Dict[str, Any]) -> Optional[str]:
        concept_uris = data.get("concept_uris", [])
        if len(concept_uris) >= 2:
            concept1, concept2 = concept_uris[0], concept_uris[1]
            return f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?concept1 ?concept2 ?bridge ?label1 ?label2 ?bridgeLabel
WHERE {{
  VALUES ?concept1 {{ <{concept1}> }}
  VALUES ?concept2 {{ <{concept2}> }}

  {{
    ?concept1 owl:sameAs ?concept2 .
    BIND(?concept2 AS ?bridge)
  }}
  UNION
  {{
    ?concept1 owl:sameAs ?bridge .
    ?concept2 owl:sameAs ?bridge .
  }}

  OPTIONAL {{ ?concept1 rdfs:label ?label1 }}
  OPTIONAL {{ ?concept2 rdfs:label ?label2 }}
  OPTIONAL {{ ?bridge rdfs:label ?bridgeLabel }}
}}
LIMIT 50"""

        return """PREFIX owl: <http://www.w3.org/2002/07/owl#>
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

    def _template_validation_query(self, data: Dict[str, Any]) -> Optional[str]:
        concept_uris = data.get("concept_uris", [])
        if len(concept_uris) < 2:
            return None

        subject_uri, object_uri = concept_uris[0], concept_uris[1]
        return f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?relation ?target ?targetLabel ?matchesAssertion
WHERE {{
  <{subject_uri}> ?relation ?target .
  FILTER(?relation IN (
    <http://example.org/hearing/hasTreatment>,
    <http://example.org/hearing/managedBy>,
    <http://example.org/hearing/requiresTreatment>,
    <http://example.org/hearing/recommendedTreatment>
  ))
  OPTIONAL {{ ?target rdfs:label ?targetLabel }}
  BIND((?target = <{object_uri}>) AS ?matchesAssertion)
}}
LIMIT 50"""

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
        max_rows: int = 100
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

    async def _handle_interpret_request(
        self,
        payload: Dict[str, Any],
        question: str,
        results: Dict[str, Any],
        context: Dict[str, Any],
        scenario_id: str,
        kg_name: str,
        logger: AgentLogger,
    ) -> Dict[str, Any]:
        guidance = payload.get("guidance")
        sparql_rows = context.get("last_sparql_results", [])
        if sparql_rows:
            csv_content = self._rows_to_csv(sparql_rows)
        else:
            csv_content = payload.get("sparql_results", "").strip()

        if not csv_content:
            return {
                "interpretation": (
                    "Aucune donnée exploitable n'a été renvoyée. Reformulez la question ou vérifiez les concepts sélectionnés."
                )
            }

        row_count = max(len(sparql_rows), csv_content.count("\n"))

        prompt_lines = [
            "Tu es l'agent Grape qui doit résumer les résultats d'une requête SPARQL.",
            f"Question utilisateur : {question}",
            f"Scénario : {scenario_id}",
            f"Graph évalué : {kg_name}",
            f"Nombre de lignes récupérées : {row_count}",
        ]
        if guidance:
            prompt_lines.append(f"Directives supplémentaires : {guidance}")
        prompt_lines.extend([
            "Résultats CSV :",
            "```csv",
            csv_content,
            "```",
            "Donne une réponse concise en français : un paragraphe clair, puis si pertinent une courte liste à puces.",
        ])

        prompt = "\n".join(prompt_lines)

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            interpretation = (response.content or "").strip()
            if not interpretation:
                interpretation = "Impossible de générer une synthèse à partir des données fournies."
        except Exception as exc:
            logger.log_step(
                StepType.RESULT_INTERPRETATION,
                "Synthèse LLM indisponible, message de secours",
                status=StepStatus.IN_PROGRESS,
                details={"error": str(exc)}
            )
            interpretation = "Une erreur est survenue pendant la synthèse. Merci de réessayer ultérieurement."

        return {"interpretation": interpretation}

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

    def _select_best_concept(
        self,
        query_text: str,
        concepts: List[Dict[str, Any]],
        logger: AgentLogger,
    ) -> Optional[Dict[str, Any]]:
        if not concepts:
            return None

        blacklist_prefixes = (
            "http://www.w3.org/",
            "https://www.w3.org/",
        )
        preferred_prefixes = (
            "http://example.org/",
            "https://example.org/",
        )

        filtered = [c for c in concepts if not any((c.get("uri", "") or "").startswith(prefix) for prefix in blacklist_prefixes)]
        if filtered:
            concepts = filtered

        if not concepts:
            return None

        preferred = [c for c in concepts if (c.get("uri", "") or "").startswith(preferred_prefixes)]
        if len(concepts) == 1:
            concepts[0]["uri"] = self._expand_uri(concepts[0].get("uri"))
            return concepts[0]

        if preferred:
            concepts = preferred

        choice = self._choose_best_concept_with_llm(query_text, concepts, logger)
        if choice:
            choice["uri"] = self._expand_uri(choice.get("uri"))
            return choice

        concepts[0]["uri"] = self._expand_uri(concepts[0].get("uri"))
        return concepts[0]

    def _choose_best_concept_with_llm(
        self,
        query_text: str,
        concepts: List[Dict[str, Any]],
        logger: AgentLogger,
    ) -> Optional[Dict[str, Any]]:
        top_k = concepts[:5]
        candidate_payload = []
        for idx, concept in enumerate(top_k, start=1):
            expanded_uri = self._expand_uri(concept.get("uri"))
            concept["uri"] = expanded_uri
            candidate_payload.append({
                "rank": idx,
                "uri": expanded_uri,
                "label": concept.get("label", ""),
                "description": concept.get("description", ""),
            })

        prompt = (
            "Tu es un assistant qui doit choisir l'URI de concept la plus pertinente pour une requête.\n"
            f"Question utilisateur : {query_text}\n"
            "Candidats (JSON) :\n"
            f"{json.dumps(candidate_payload, ensure_ascii=False, indent=2)}\n"
            "Réponds uniquement avec l'URI exacte du meilleur candidat. Si tu n'es pas sûr, renvoie 'UNKNOWN'."
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = (response.content or "").strip()
            if not content or content.upper() == "UNKNOWN":
                return None
            for concept in top_k:
                expanded_uri = self._expand_uri(concept.get("uri"))
                if content in {expanded_uri, concept.get("uri") or ""}:
                    concept["uri"] = expanded_uri
                    logger.log_step(
                        StepType.CONCEPT_SEARCH,
                        f"LLM a sélectionné l'URI '{content}'",
                        details={"query": query_text}
                    )
                    return concept
        except Exception as exc:
            logger.log_step(
                StepType.CONCEPT_SEARCH,
                "Sélection LLM de concept impossible, fallback",
                status=StepStatus.IN_PROGRESS,
                details={"error": str(exc)}
            )
        return None

    def _expand_uri(self, uri: Optional[str]) -> Optional[str]:
        if not uri:
            return uri
        if uri.startswith("http://") or uri.startswith("https://"):
            return uri
        if ":" in uri:
            prefix, local = uri.split(":", 1)
            base = self.prefix_map.get(prefix)
            if base:
                return f"{base}{local}"
        return uri

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
