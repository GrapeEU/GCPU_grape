import pytest

from core.agent_executor import AgentExecutor
from core.agent_logger import AgentLogger


class DummyLLM:
    def invoke(self, *_args, **_kwargs):
        raise RuntimeError("LLM should not be invoked during template tests")


@pytest.fixture()
def executor() -> AgentExecutor:
    return AgentExecutor(llm=DummyLLM())


def test_select_best_concept_returns_first(executor: AgentExecutor):
    concepts = [
        {"uri": "http://example.org/hearing/Tinnitus", "label": "Tinnitus"},
        {"uri": "http://example.org/hearing/HearingLoss", "label": "Hearing Loss"},
    ]

    logger = AgentLogger()
    selected = executor._select_best_concept("tinnitus", concepts, logger)

    assert selected is concepts[0]


def test_neighbourhood_template_requires_focus(executor: AgentExecutor):
    payload = {"query": ""}
    context = {"concept_uris": ["http://example.org/hearing/Tinnitus"]}

    prepared = executor._prepare_sparql_payload(payload, context, "grape_hearing", "scenario_1_neighbourhood")

    query = prepared["query"]
    assert "VALUES ?source { <http://example.org/hearing/Tinnitus> }" in query
    assert query.strip().upper().startswith("PREFIX")


def test_multihop_template_uses_both_uris(executor: AgentExecutor):
    payload = {"query": ""}
    context = {"concept_uris": [
        "http://example.org/psychiatry/ChronicStress",
        "http://example.org/hearing/HearingLoss",
    ]}

    prepared = executor._prepare_sparql_payload(payload, context, "grape_unified", "scenario_2_multihop")

    query = prepared["query"]
    assert "BIND(<http://example.org/psychiatry/ChronicStress> AS ?source)" in query
    assert "BIND(<http://example.org/hearing/HearingLoss> AS ?target)" in query


def test_federation_template_supports_bridge(executor: AgentExecutor):
    payload = {"query": ""}
    context = {"concept_uris": [
        "http://example.org/hearing/Tinnitus",
        "http://example.org/psychiatry/AnxietyDisorder",
    ]}

    prepared = executor._prepare_sparql_payload(payload, context, "grape_unified", "scenario_3_federation")

    query = prepared["query"]
    assert "VALUES ?concept1 { <http://example.org/hearing/Tinnitus> }" in query
    assert "VALUES ?concept2 { <http://example.org/psychiatry/AnxietyDisorder> }" in query
    assert "owl:sameAs" in query


def test_validation_template_filters_treatments(executor: AgentExecutor):
    payload = {"query": ""}
    context = {"concept_uris": [
        "http://example.org/hearing/HearingLoss",
        "http://example.org/hearing/CognitiveBehavioralTherapy",
    ]}

    prepared = executor._prepare_sparql_payload(payload, context, "grape_hearing", "scenario_4_validation")

    query = prepared["query"]
    assert "<http://example.org/hearing/HearingLoss>" in query
    assert "<http://example.org/hearing/CognitiveBehavioralTherapy>" not in query.split("FILTER", 1)[0]
    assert "FILTER(?relation IN" in query
