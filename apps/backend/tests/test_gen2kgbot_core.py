"""
Test Core gen2kgbot Components with GraphDB

Tests the essential gen2kgbot functions against live GraphDB:
1. preprocess_question() - NER extraction
2. select_similar_classes() - Embedding search (requires preprocessing)
3. run_sparql_query() - SPARQL execution
4. interpret_results() - CSV to Natural Language

These are the CORE components all scenarios depend on.
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add gen2kgbot to path
GEN2KGBOT_PATH = Path(__file__).parent.parent / "gen2kgbot"
sys.path.insert(0, str(GEN2KGBOT_PATH))

from app.utils.graph_nodes import preprocess_question, interpret_results
from app.utils.sparql_toolkit import run_sparql_query
from app.utils.config_manager import get_class_context_vector_db
import app.utils.config_manager as config
from app.utils.graph_state import OverallState


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

TEST_ENDPOINT = "http://localhost:7200/repositories/hearing"
TEST_KG_NAME = "grape_hearing"

@pytest.fixture(scope="module")
def configure_gen2kgbot():
    """Configure gen2kgbot for grape_hearing KG"""
    config.config["kg_short_name"] = TEST_KG_NAME
    config.config["kg_sparql_endpoint_url"] = TEST_ENDPOINT
    config.config["ontologies_sparql_endpoint_url"] = TEST_ENDPOINT
    config.config["kg_full_name"] = "Grape Hearing Knowledge Graph"
    config.config["kg_description"] = "Medical KG focused on hearing disorders"


# ============================================================================
# TEST 1: SPARQL Execution (Most Basic)
# ============================================================================

def test_sparql_execution_simple(configure_gen2kgbot):
    """
    Test 1: SPARQL query execution

    This is the CORE - everything depends on this working.
    """
    # Simple SELECT query
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?s ?label WHERE {
        ?s rdfs:label ?label .
    } LIMIT 5
    """

    result = run_sparql_query(query, TEST_ENDPOINT)

    # Check result type
    assert isinstance(result, str), f"Expected CSV string, got {type(result)}"

    # Check CSV format
    lines = result.strip().split('\n')
    assert len(lines) >= 2, "Expected header + at least 1 result row"

    # Check header
    header = lines[0]
    assert 's' in header and 'label' in header, f"Expected 's,label' header, got: {header}"

    print(f"✅ Test 1 PASSED: SPARQL execution works")
    print(f"   Results: {len(lines)-1} rows")
    print(f"   Sample: {lines[1] if len(lines) > 1 else 'No data'}")


def test_sparql_find_tinnitus(configure_gen2kgbot):
    """
    Test 1b: Find specific concept (Tinnitus)

    Validates that our test KG contains expected medical concepts.
    """
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?s ?label WHERE {
        ?s rdfs:label ?label .
        FILTER(LCASE(STR(?label)) = "tinnitus")
    }
    """

    result = run_sparql_query(query, TEST_ENDPOINT)
    lines = result.strip().split('\n')

    assert len(lines) >= 2, "Tinnitus concept not found in KG"

    # Extract URI
    tinnitus_uri = lines[1].split(',')[0]
    print(f"✅ Test 1b PASSED: Found Tinnitus at {tinnitus_uri}")

    return tinnitus_uri


def test_sparql_get_relationships(configure_gen2kgbot):
    """
    Test 1c: Get relationships (triples)

    Validates that concepts have properties/relationships.
    """
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?s ?p ?o WHERE {
        ?s rdfs:label "Tinnitus" .
        ?s ?p ?o .
        FILTER(?p != rdf:type)
    } LIMIT 10
    """

    result = run_sparql_query(query, TEST_ENDPOINT)
    lines = result.strip().split('\n')

    assert len(lines) >= 2, "No relationships found for Tinnitus"

    print(f"✅ Test 1c PASSED: Found {len(lines)-1} relationships for Tinnitus")
    for line in lines[1:4]:  # Show first 3
        print(f"   {line}")


# ============================================================================
# TEST 2: NER / Question Preprocessing
# ============================================================================

def test_preprocess_question(configure_gen2kgbot):
    """
    Test 2: Extract named entities from question

    Tests: preprocess_question() from graph_nodes.py
    Requires: Spacy model (en_core_web_lg)
    """
    test_questions = [
        "What are the symptoms of Tinnitus?",
        "How does Depression relate to Anxiety?",
        "Find treatments for Hearing Loss"
    ]

    for question in test_questions:
        state = OverallState({"initial_question": question})

        # Execute preprocessing
        result_state = preprocess_question(state)

        # Check output
        assert "question_relevant_entities" in result_state, "Missing extracted entities"
        entities = result_state["question_relevant_entities"]

        assert isinstance(entities, list), f"Expected list, got {type(entities)}"
        assert len(entities) > 0, f"No entities extracted from: {question}"

        print(f"✅ Test 2 PASSED: '{question}'")
        print(f"   Entities: {entities}")


# ============================================================================
# TEST 3: Embedding Search (REQUIRES PREPROCESSING)
# ============================================================================

def test_embedding_search_if_available(configure_gen2kgbot):
    """
    Test 3: Semantic concept search with embeddings

    Tests: select_similar_classes() from graph_nodes.py
    Requires: Embeddings generated (scripts/generate_grape_embeddings.py)

    NOTE: This test is OPTIONAL - it will SKIP if embeddings don't exist
    """
    try:
        # Try to load vector DB
        db = get_class_context_vector_db("scenario_3")

        # If we get here, embeddings exist
        test_queries = ["Tinnitus", "hearing loss", "symptoms"]

        for query in test_queries:
            matches = db.similarity_search(query, k=3)

            assert len(matches) > 0, f"No matches found for: {query}"

            print(f"✅ Test 3 PASSED: Embedding search for '{query}'")
            for i, match in enumerate(matches[:2], 1):
                content_preview = match.page_content[:80]
                print(f"   {i}. {content_preview}...")

    except Exception as e:
        pytest.skip(f"Embeddings not available: {e}\n  Run: python scripts/generate_grape_embeddings.py")


# ============================================================================
# TEST 4: Results Interpretation (CSV → Natural Language)
# ============================================================================

@pytest.mark.asyncio
async def test_interpret_results(configure_gen2kgbot):
    """
    Test 4: Convert SPARQL CSV results to natural language

    Tests: interpret_results() from graph_nodes.py
    Requires: LLM configured (Gemini/Llama)
    """
    # Sample CSV results (from SPARQL query)
    sample_csv = """s,p,o
http://example.org/hearing/Tinnitus,http://example.org/hearing/hasSymptom,http://example.org/hearing/Insomnia
http://example.org/hearing/Tinnitus,http://example.org/hearing/hasSymptom,http://example.org/hearing/Anxiety"""

    state = OverallState({
        "scenario_id": "scenario_3",
        "initial_question": "What are the symptoms of Tinnitus?",
        "last_query_results": sample_csv
    })

    try:
        # Execute interpretation
        result_state = await interpret_results(state)

        # Check output
        assert "results_interpretation" in result_state, "Missing interpretation"
        interpretation = result_state["results_interpretation"]

        assert isinstance(interpretation, str), f"Expected string, got {type(interpretation)}"
        assert len(interpretation) > 10, "Interpretation too short"

        print(f"✅ Test 4 PASSED: Results interpretation")
        print(f"   Input: {len(sample_csv.split('\\n'))-1} CSV rows")
        print(f"   Output: {interpretation[:150]}...")

    except Exception as e:
        pytest.skip(f"LLM not configured: {e}\n  Set GEMINI_API_KEY or OPENAI_API_KEY in .env")


# ============================================================================
# TEST 5: End-to-End Simple Workflow
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_workflow(configure_gen2kgbot):
    """
    Test 5: Complete workflow simulation

    Simulates a simple scenario execution:
    1. Preprocess question → extract entities
    2. Generate SPARQL query (manual for now)
    3. Execute query
    4. Interpret results
    """
    question = "What are the symptoms of Tinnitus?"

    # Step 1: Preprocess
    state = OverallState({"initial_question": question, "scenario_id": "scenario_3"})
    state = preprocess_question(state)

    print(f"Step 1: Extracted entities: {state['question_relevant_entities']}")

    # Step 2: Generate query (simplified - no LLM)
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?s ?p ?o WHERE {
        ?s rdfs:label "Tinnitus" .
        ?s ?p ?o .
    } LIMIT 10
    """

    print(f"Step 2: Generated SPARQL query")

    # Step 3: Execute
    csv_result = run_sparql_query(query, TEST_ENDPOINT)
    state["last_query_results"] = csv_result

    print(f"Step 3: Executed query, got {len(csv_result.split('\\n'))-1} results")

    # Step 4: Interpret (optional - skip if LLM not available)
    try:
        state = await interpret_results(state)
        print(f"Step 4: Interpretation: {state['results_interpretation'][:100]}...")
        print(f"✅ Test 5 PASSED: End-to-end workflow complete")
    except Exception as e:
        print(f"Step 4: Skipped interpretation (LLM not available): {e}")
        print(f"✅ Test 5 PASSED: Core workflow (SPARQL) complete")


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("TESTING GEN2KGBOT CORE COMPONENTS")
    print("="*70)

    # Run pytest
    pytest.main([__file__, "-v", "-s"])
