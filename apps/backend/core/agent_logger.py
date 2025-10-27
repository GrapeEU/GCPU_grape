"""
Agent Logger - Structured logging for agent execution traces

Provides step-by-step logging that can be displayed in both:
- Backend: Python logs for debugging
- Frontend: Structured events for UX display
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class StepType(str, Enum):
    """Types of agent execution steps."""
    SCENARIO_DETECTION = "scenario_detection"
    ENTITY_EXTRACTION = "entity_extraction"
    CONCEPT_SEARCH = "concept_search"
    NEIGHBOURHOOD_EXPLORATION = "neighbourhood_exploration"
    SPARQL_QUERY = "sparql_query"
    RESULT_INTERPRETATION = "result_interpretation"
    ERROR = "error"
    SUCCESS = "success"


class StepStatus(str, Enum):
    """Status of execution step."""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentLogger:
    """
    Structured logger for agent execution traces.

    Captures each step of the agent pipeline with:
    - Timestamp
    - Step type
    - Description (user-friendly message)
    - Technical details (for debugging)
    - Status
    """

    def __init__(self, session_id: str = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(f"agent.{self.session_id}")
        self.steps: List[Dict[str, Any]] = []

    def log_step(
        self,
        step_type: StepType,
        message: str,
        status: StepStatus = StepStatus.COMPLETED,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log a single execution step.

        Args:
            step_type: Type of step (scenario_detection, concept_search, etc.)
            message: User-friendly message for frontend display
            status: Status of the step
            details: Technical details for debugging

        Returns:
            Step dictionary that was logged
        """
        step = {
            "timestamp": datetime.now().isoformat(),
            "step_type": step_type.value,
            "message": message,
            "status": status.value,
            "details": details or {}
        }

        self.steps.append(step)

        # Backend logging
        log_level = logging.ERROR if status == StepStatus.FAILED else logging.INFO
        self.logger.log(
            log_level,
            f"[{step_type.value}] {message}",
            extra={"details": details}
        )

        return step

    def start_step(self, step_type: StepType, message: str) -> Dict[str, Any]:
        """Log the start of a step."""
        return self.log_step(step_type, message, StepStatus.STARTED)

    def complete_step(self, step_type: StepType, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Log the completion of a step."""
        return self.log_step(step_type, message, StepStatus.COMPLETED, details)

    def fail_step(self, step_type: StepType, message: str, error: Exception = None) -> Dict[str, Any]:
        """Log a failed step."""
        details = {"error": str(error)} if error else {}
        return self.log_step(step_type, message, StepStatus.FAILED, details)

    def log_scenario_detection(self, question: str, detected_scenario: str) -> Dict[str, Any]:
        """Log scenario detection."""
        return self.complete_step(
            StepType.SCENARIO_DETECTION,
            f"Identified scenario: {detected_scenario}",
            {"question": question, "scenario": detected_scenario}
        )

    def log_entity_extraction(self, entities: List[str]) -> Dict[str, Any]:
        """Log entity extraction."""
        entities_str = ", ".join(entities) if entities else "none"
        return self.complete_step(
            StepType.ENTITY_EXTRACTION,
            f"Extracted entities: {entities_str}",
            {"entities": entities, "count": len(entities)}
        )

    def log_concept_search(self, query: str, concepts_found: int) -> Dict[str, Any]:
        """Log semantic concept search."""
        return self.complete_step(
            StepType.CONCEPT_SEARCH,
            f"Found {concepts_found} similar concepts for '{query}'",
            {"query": query, "concepts_found": concepts_found}
        )

    def log_sparql_query(self, query: str, results_count: int) -> Dict[str, Any]:
        """Log SPARQL query execution."""
        return self.complete_step(
            StepType.SPARQL_QUERY,
            f"Executed SPARQL query: {results_count} results",
            {"query": query[:200] + "..." if len(query) > 200 else query, "results_count": results_count}
        )

    def log_interpretation(self, summary: str) -> Dict[str, Any]:
        """Log result interpretation."""
        return self.complete_step(
            StepType.RESULT_INTERPRETATION,
            "Generated natural language explanation",
            {"summary": summary[:150] + "..." if len(summary) > 150 else summary}
        )

    def log_success(self, message: str = "Agent execution completed successfully") -> Dict[str, Any]:
        """Log successful completion."""
        return self.log_step(StepType.SUCCESS, message, StepStatus.COMPLETED)

    def log_error(self, message: str, error: Exception = None) -> Dict[str, Any]:
        """Log an error."""
        return self.fail_step(StepType.ERROR, message, error)

    def get_trace(self) -> List[Dict[str, Any]]:
        """Get all logged steps as a list."""
        return self.steps

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        total_steps = len(self.steps)
        completed = sum(1 for s in self.steps if s["status"] == StepStatus.COMPLETED.value)
        failed = sum(1 for s in self.steps if s["status"] == StepStatus.FAILED.value)

        return {
            "session_id": self.session_id,
            "total_steps": total_steps,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total_steps if total_steps > 0 else 0,
            "steps": self.steps
        }

    def format_for_frontend(self) -> List[Dict[str, str]]:
        """
        Format logs for frontend display.

        Returns simplified messages like:
        - "🔍 Identified scenario: Neighbourhood Exploration"
        - "📝 Extracted entities: Tinnitus, symptoms"
        - "🔎 Found 3 similar concepts for 'Tinnitus'"
        - "⚡ Executed SPARQL query: 12 results"
        - "💬 Generated natural language explanation"
        """
        icons = {
            StepType.SCENARIO_DETECTION: "🎯",
            StepType.ENTITY_EXTRACTION: "📝",
            StepType.CONCEPT_SEARCH: "🔎",
            StepType.NEIGHBOURHOOD_EXPLORATION: "🌐",
            StepType.SPARQL_QUERY: "⚡",
            StepType.RESULT_INTERPRETATION: "💬",
            StepType.ERROR: "❌",
            StepType.SUCCESS: "✅"
        }

        formatted = []
        for step in self.steps:
            icon = icons.get(StepType(step["step_type"]), "▪️")
            formatted.append({
                "message": f"{icon} {step['message']}",
                "status": step["status"],
                "timestamp": step["timestamp"]
            })

        return formatted
