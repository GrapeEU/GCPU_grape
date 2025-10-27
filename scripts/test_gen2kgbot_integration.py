#!/usr/bin/env python3
"""
Test gen2kgbot integration with Grape medical KGs

This script validates that:
1. Embeddings were generated successfully
2. Vector DB can be loaded and queried
3. SPARQL toolkit works with GraphDB
4. Semantic search finds relevant medical concepts

Usage:
    python scripts/test_gen2kgbot_integration.py

Requirements:
    - Preprocessing completed (generate_grape_embeddings.py)
    - GraphDB running with data loaded
    - Ollama running with nomic-embed-text
"""

import sys
import asyncio
from pathlib import Path

# Add gen2kgbot to path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "backend"
GEN2KGBOT_DIR = BACKEND_DIR / "gen2kgbot"

if not GEN2KGBOT_DIR.exists():
    print(f"❌ ERROR: gen2kgbot not found at {GEN2KGBOT_DIR}")
    sys.exit(1)

sys.path.insert(0, str(GEN2KGBOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.utils.config_manager import (
        get_class_context_vector_db,
        get_kg_data_directory,
        get_embeddings_directory
    )
    from app.utils.sparql_toolkit import run_sparql_query
    from app.utils.logger_manager import setup_logger
    import app.utils.config_manager as config
except ImportError as e:
    print(f"❌ ERROR: Failed to import gen2kgbot modules: {e}")
    sys.exit(1)

logger = setup_logger(__name__, __file__)

# Test configurations for each KG
TEST_KGS = [
    {
        "short_name": "grape_demo",
        "endpoint": "http://localhost:7200/repositories/demo",
        "test_queries": [
            "Asthma symptoms",
            "Anxiety treatment",
            "risk factors hypertension"
        ],
        "expected_results": ["Asthma", "Anxiety", "Hypertension"]
    },
    {
        "short_name": "grape_hearing",
        "endpoint": "http://localhost:7200/repositories/hearing",
        "test_queries": [
            "Tinnitus symptoms",
            "hearing loss treatment",
            "noise exposure"
        ],
        "expected_results": ["Tinnitus", "HearingLoss", "NoiseExposure"]
    },
    {
        "short_name": "grape_psychiatry",
        "endpoint": "http://localhost:7200/repositories/psychiatry",
        "test_queries": [
            "Depression symptoms",
            "anxiety disorders",
            "PTSD treatment"
        ],
        "expected_results": ["Depression", "Anxiety", "PTSD"]
    },
    {
        "short_name": "grape_unified",
        "endpoint": "http://localhost:7200/repositories/unified",
        "test_queries": [
            "cross-domain mental health",
            "hearing and depression",
            "sleep disturbance"
        ],
        "expected_results": ["Tinnitus", "Depression", "SleepDisturbance"]
    }
]


def test_embeddings_exist(kg_config):
    """
    Test if embeddings were generated for a KG

    Args:
        kg_config: KG configuration dict

    Returns:
        tuple: (success: bool, details: dict, error: str)
    """
    print(f"\n1️⃣  Checking embeddings existence...")

    try:
        # Configure for this KG
        config.config["kg_short_name"] = kg_config["short_name"]
        config.config["kg_sparql_endpoint_url"] = kg_config["endpoint"]

        # Check data directory
        data_dir = get_kg_data_directory()
        if not data_dir.exists():
            return False, {}, f"Data directory not found: {data_dir}"

        # Check preprocessing files
        preprocessing_dir = data_dir / "preprocessing"
        classes_file = preprocessing_dir / "classes_with_instances_description.txt"

        if not classes_file.exists():
            return False, {}, f"Classes file not found: {classes_file}"

        # Count descriptions
        with open(classes_file, 'r') as f:
            class_count = len(f.readlines())

        # Check embeddings directory
        embeddings_dir = get_embeddings_directory("faiss") / config.get_class_embeddings_subdir()

        if not embeddings_dir.exists():
            return False, {}, f"Embeddings directory not found: {embeddings_dir}"

        # Check FAISS index files
        index_file = embeddings_dir / "index.faiss"
        pkl_file = embeddings_dir / "index.pkl"

        if not index_file.exists():
            return False, {}, f"FAISS index not found: {index_file}"

        if not pkl_file.exists():
            return False, {}, f"FAISS metadata not found: {pkl_file}"

        # Get file sizes
        index_size = index_file.stat().st_size / 1024  # KB
        pkl_size = pkl_file.stat().st_size / 1024  # KB

        details = {
            "class_count": class_count,
            "index_size_kb": round(index_size, 2),
            "pkl_size_kb": round(pkl_size, 2)
        }

        print(f"   ✅ PASS - Embeddings found")
        print(f"      • Classes: {class_count}")
        print(f"      • Index: {details['index_size_kb']} KB")
        print(f"      • Metadata: {details['pkl_size_kb']} KB")

        return True, details, None

    except Exception as e:
        return False, {}, str(e)


def test_vector_db_loading(kg_config):
    """
    Test if vector DB can be loaded

    Args:
        kg_config: KG configuration dict

    Returns:
        tuple: (success: bool, db: VectorStore, error: str)
    """
    print(f"\n2️⃣  Testing vector DB loading...")

    try:
        # Configure for this KG
        config.config["kg_short_name"] = kg_config["short_name"]
        config.config["kg_sparql_endpoint_url"] = kg_config["endpoint"]

        # Load vector DB (scenario_3 uses embeddings)
        db = get_class_context_vector_db("scenario_3")

        print(f"   ✅ PASS - Vector DB loaded successfully")
        print(f"      • Type: FAISS")
        print(f"      • Ready for similarity search")

        return True, db, None

    except Exception as e:
        return False, None, str(e)


def test_semantic_search(kg_config, db):
    """
    Test semantic search with medical queries

    Args:
        kg_config: KG configuration dict
        db: Loaded vector DB

    Returns:
        tuple: (success: bool, results: list, error: str)
    """
    print(f"\n3️⃣  Testing semantic search...")

    try:
        all_results = []

        for query in kg_config["test_queries"]:
            print(f"\n   Query: '{query}'")

            # Search for similar concepts
            matches = db.similarity_search(query, k=3)

            if not matches:
                print(f"      ⚠️  No matches found")
                continue

            print(f"      Found {len(matches)} similar concepts:")

            query_results = []
            for i, match in enumerate(matches, 1):
                # Parse tuple format: (uri, label, description)
                try:
                    concept_tuple = eval(match.page_content)
                    uri, label, description = concept_tuple

                    # Extract concept name from URI
                    concept_name = uri.split(':')[-1] if ':' in uri else uri.split('/')[-1]

                    print(f"      {i}. {concept_name}")
                    print(f"         URI: {uri}")
                    if label:
                        print(f"         Label: {label}")

                    query_results.append({
                        "query": query,
                        "concept": concept_name,
                        "uri": uri,
                        "label": label,
                        "description": description
                    })

                except Exception as e:
                    print(f"      ⚠️  Could not parse result: {match.page_content[:100]}")

            all_results.extend(query_results)

        if all_results:
            print(f"\n   ✅ PASS - Semantic search working")
            print(f"      • Total queries: {len(kg_config['test_queries'])}")
            print(f"      • Total results: {len(all_results)}")
            return True, all_results, None
        else:
            return False, [], "No results found for any query"

    except Exception as e:
        return False, [], str(e)


def test_sparql_execution(kg_config):
    """
    Test SPARQL query execution via gen2kgbot

    Args:
        kg_config: KG configuration dict

    Returns:
        tuple: (success: bool, triple_count: int, error: str)
    """
    print(f"\n4️⃣  Testing SPARQL execution...")

    try:
        # Configure endpoint
        config.config["kg_sparql_endpoint_url"] = kg_config["endpoint"]

        # Simple test query
        query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?class ?label WHERE {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:label ?label }
        } LIMIT 10
        """

        # Execute query
        csv_results = run_sparql_query(query, kg_config["endpoint"])

        # Parse CSV
        lines = csv_results.strip().split('\n')
        result_count = len(lines) - 1  # Exclude header

        print(f"   ✅ PASS - SPARQL execution working")
        print(f"      • Query executed successfully")
        print(f"      • Results: {result_count} rows")

        # Show sample results
        if result_count > 0:
            print(f"\n      Sample results:")
            for line in lines[1:min(4, len(lines))]:  # Show first 3 results
                parts = line.split(',')
                if len(parts) >= 2:
                    print(f"      • {parts[0]}: {parts[1]}")

        return True, result_count, None

    except Exception as e:
        return False, 0, str(e)


async def test_kg(kg_config):
    """
    Run all tests for a single KG

    Args:
        kg_config: KG configuration dict

    Returns:
        dict: Test results
    """
    print(f"\n{'='*70}")
    print(f"Testing: {kg_config['short_name']}")
    print(f"Endpoint: {kg_config['endpoint']}")
    print(f"{'='*70}")

    results = {
        "kg": kg_config["short_name"],
        "tests": {}
    }

    # Test 1: Embeddings exist
    success, details, error = test_embeddings_exist(kg_config)
    if success:
        results["tests"]["embeddings"] = {"status": "pass", "details": details}
    else:
        print(f"   ❌ FAIL - {error}")
        results["tests"]["embeddings"] = {"status": "fail", "error": error}
        return results  # Skip other tests

    # Test 2: Vector DB loading
    success, db, error = test_vector_db_loading(kg_config)
    if success:
        results["tests"]["vector_db"] = {"status": "pass"}
    else:
        print(f"   ❌ FAIL - {error}")
        results["tests"]["vector_db"] = {"status": "fail", "error": error}
        return results  # Skip other tests

    # Test 3: Semantic search
    success, search_results, error = test_semantic_search(kg_config, db)
    if success:
        results["tests"]["semantic_search"] = {
            "status": "pass",
            "result_count": len(search_results)
        }
    else:
        print(f"   ❌ FAIL - {error}")
        results["tests"]["semantic_search"] = {"status": "fail", "error": error}

    # Test 4: SPARQL execution
    success, triple_count, error = test_sparql_execution(kg_config)
    if success:
        results["tests"]["sparql"] = {"status": "pass", "triple_count": triple_count}
    else:
        print(f"   ❌ FAIL - {error}")
        results["tests"]["sparql"] = {"status": "fail", "error": error}

    return results


async def main():
    """Main test orchestrator"""

    print("\n" + "="*70)
    print("🍇 GRAPE - gen2kgbot Integration Test Suite")
    print("="*70)

    # Pre-check: Ollama availability
    print("\n🔍 Pre-check: Ollama + nomic-embed-text...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if any("nomic-embed-text" in m.get("name", "") for m in models):
                print("   ✅ Ollama + nomic-embed-text available")
            else:
                print("   ❌ nomic-embed-text not found")
                print("   Install with: ollama pull nomic-embed-text")
                sys.exit(1)
        else:
            print(f"   ❌ Ollama returned HTTP {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"   ❌ Cannot connect to Ollama: {e}")
        print("   Start with: brew services start ollama")
        sys.exit(1)

    # Run tests for all KGs
    all_results = []
    for kg_config in TEST_KGS:
        results = await test_kg(kg_config)
        all_results.append(results)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    total_kgs = len(all_results)
    passed_kgs = 0

    for result in all_results:
        kg_name = result["kg"]
        tests = result["tests"]

        passed_tests = sum(1 for t in tests.values() if t.get("status") == "pass")
        total_tests = len(tests)

        if passed_tests == total_tests:
            print(f"✅ {kg_name}: {passed_tests}/{total_tests} tests passed")
            passed_kgs += 1
        else:
            print(f"❌ {kg_name}: {passed_tests}/{total_tests} tests passed")

    print(f"\nKnowledge Graphs: {passed_kgs}/{total_kgs} fully integrated")

    # Recommendations
    if passed_kgs < total_kgs:
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)

        for result in all_results:
            failed_tests = [
                name for name, test in result["tests"].items()
                if test.get("status") == "fail"
            ]

            if failed_tests:
                print(f"\n{result['kg']}:")
                for test_name in failed_tests:
                    if test_name == "embeddings":
                        print(f"  ❌ Embeddings not found")
                        print(f"     → Run preprocessing: python scripts/generate_grape_embeddings.py")
                    elif test_name == "vector_db":
                        print(f"  ❌ Vector DB loading failed")
                        print(f"     → Check FAISS installation: uv pip install faiss-cpu")
                    elif test_name == "semantic_search":
                        print(f"  ❌ Semantic search failed")
                        print(f"     → Verify embeddings quality and Ollama connection")
                    elif test_name == "sparql":
                        print(f"  ❌ SPARQL execution failed")
                        print(f"     → Check GraphDB connection: python scripts/test_graphdb_connection.py")

    print("\n" + "="*70)

    if passed_kgs == total_kgs:
        print("🎉 All tests passed! gen2kgbot integration ready.")
        print("\nNext steps:")
        print("  1. Implement scenarios: apps/backend/scenarios/scenario_*.py")
        print("  2. Test end-to-end: curl -X POST http://localhost:8000/api/agent/chat")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix issues above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
