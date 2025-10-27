#!/usr/bin/env python3
"""
Test GraphDB connectivity for all Grape repositories

This script verifies that:
1. GraphDB is running on localhost:7200
2. All 4 repositories (demo, hearing, psychiatry, unified) are accessible
3. Each repository contains RDF triples
4. SPARQL queries can be executed

Usage:
    python scripts/test_graphdb_connection.py

Exit codes:
    0 - All tests passed
    1 - Some tests failed
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

try:
    from pipelines.sparql_query_executor import SPARQLExecutor
except ImportError:
    print("❌ ERROR: Failed to import SPARQLExecutor")
    print("   Make sure backend dependencies are installed:")
    print("   cd apps/backend && uv pip install -r requirements.txt")
    sys.exit(1)

# Test configurations
TEST_REPOS = [
    {
        "name": "demo",
        "endpoint": "http://localhost:7200/repositories/demo",
        "description": "General medical conditions",
        "expected_concepts": ["Asthma", "Anxiety", "Hypertension"]
    },
    {
        "name": "hearing",
        "endpoint": "http://localhost:7200/repositories/hearing",
        "description": "Hearing & Tinnitus disorders",
        "expected_concepts": ["Tinnitus", "HearingLoss", "Hyperacusis"]
    },
    {
        "name": "psychiatry",
        "endpoint": "http://localhost:7200/repositories/psychiatry",
        "description": "Mental health disorders",
        "expected_concepts": ["Depression", "Anxiety", "PTSD"]
    },
    {
        "name": "unified",
        "endpoint": "http://localhost:7200/repositories/unified",
        "description": "All KGs + alignments",
        "expected_concepts": ["Tinnitus", "Depression", "Asthma"]
    }
]


async def test_basic_connectivity(endpoint):
    """
    Test basic SPARQL connectivity

    Args:
        endpoint: SPARQL endpoint URL

    Returns:
        tuple: (success: bool, triple_count: int, error: str)
    """
    try:
        executor = SPARQLExecutor(endpoint)
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
        results = await executor.execute(query)

        # results is already a list of dicts from SPARQLExecutor
        triple_count = len(results)

        return True, triple_count, None
    except Exception as e:
        return False, 0, str(e)


async def test_owl_classes(endpoint):
    """
    Test retrieval of OWL classes

    Args:
        endpoint: SPARQL endpoint URL

    Returns:
        tuple: (success: bool, class_count: int, error: str)
    """
    try:
        executor = SPARQLExecutor(endpoint)
        query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?class ?label WHERE {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:label ?label }
        } LIMIT 50
        """
        results = await executor.execute(query)

        # results is already a list of dicts
        class_count = len(results)

        return True, class_count, None
    except Exception as e:
        return False, 0, str(e)


async def test_specific_concepts(endpoint, expected_concepts):
    """
    Test if specific medical concepts exist in the KG

    Args:
        endpoint: SPARQL endpoint URL
        expected_concepts: List of concept names to search for

    Returns:
        tuple: (success: bool, found_concepts: list, error: str)
    """
    try:
        executor = SPARQLExecutor(endpoint)

        found_concepts = []
        for concept in expected_concepts:
            query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX schema: <http://schema.org/>

            SELECT ?s WHERE {{
                ?s ?p ?o .
                FILTER(
                    CONTAINS(STR(?s), "{concept}") ||
                    (isLiteral(?o) && CONTAINS(LCASE(STR(?o)), LCASE("{concept}")))
                )
            }} LIMIT 1
            """

            results = await executor.execute(query)
            if len(results) > 0:  # Found at least one result
                found_concepts.append(concept)

        return True, found_concepts, None
    except Exception as e:
        return False, [], str(e)


async def test_repository(repo_config):
    """
    Run all tests for a single repository

    Args:
        repo_config: Repository configuration dict

    Returns:
        dict: Test results
    """
    print(f"\n{'='*70}")
    print(f"Testing: {repo_config['name']} - {repo_config['description']}")
    print(f"Endpoint: {repo_config['endpoint']}")
    print(f"{'='*70}")

    results = {
        "name": repo_config["name"],
        "endpoint": repo_config["endpoint"],
        "tests": {}
    }

    # Test 1: Basic connectivity
    print("\n1️⃣  Testing basic SPARQL connectivity...")
    success, triple_count, error = await test_basic_connectivity(repo_config["endpoint"])

    if success:
        print(f"   ✅ PASS - Retrieved {triple_count} sample triples")
        results["tests"]["connectivity"] = {"status": "pass", "triple_count": triple_count}
    else:
        print(f"   ❌ FAIL - {error}")
        results["tests"]["connectivity"] = {"status": "fail", "error": error}
        return results  # Skip other tests if connectivity fails

    # Test 2: OWL classes
    print("\n2️⃣  Testing OWL class retrieval...")
    success, class_count, error = await test_owl_classes(repo_config["endpoint"])

    if success:
        print(f"   ✅ PASS - Found {class_count} OWL classes")
        results["tests"]["owl_classes"] = {"status": "pass", "class_count": class_count}
    else:
        print(f"   ❌ FAIL - {error}")
        results["tests"]["owl_classes"] = {"status": "fail", "error": error}

    # Test 3: Specific concepts
    print("\n3️⃣  Testing specific medical concepts...")
    print(f"   Looking for: {', '.join(repo_config['expected_concepts'])}")

    success, found_concepts, error = await test_specific_concepts(
        repo_config["endpoint"],
        repo_config["expected_concepts"]
    )

    if success:
        if found_concepts:
            print(f"   ✅ PASS - Found {len(found_concepts)}/{len(repo_config['expected_concepts'])} concepts")
            for concept in found_concepts:
                print(f"      ✓ {concept}")
            results["tests"]["concepts"] = {
                "status": "pass",
                "found": found_concepts,
                "expected": repo_config["expected_concepts"]
            }
        else:
            print(f"   ⚠️  WARN - No expected concepts found (KG might be empty)")
            results["tests"]["concepts"] = {
                "status": "warn",
                "found": [],
                "expected": repo_config["expected_concepts"]
            }
    else:
        print(f"   ❌ FAIL - {error}")
        results["tests"]["concepts"] = {"status": "fail", "error": error}

    return results


async def main():
    """Main test orchestrator"""

    print("\n" + "="*70)
    print("🍇 GRAPE - GraphDB Connection Test Suite")
    print("="*70)

    # Pre-check: Is GraphDB running?
    print("\n🔍 Pre-check: GraphDB availability...")
    try:
        import requests
        response = requests.get("http://localhost:7200/protocol", timeout=5)
        if response.status_code == 200:
            print("   ✅ GraphDB is running")
        else:
            print(f"   ❌ GraphDB returned HTTP {response.status_code}")
            print("\n💡 Start GraphDB with: docker-compose -f docker-compose.graphdb.yml up -d")
            sys.exit(1)
    except Exception as e:
        print(f"   ❌ Cannot connect to GraphDB: {e}")
        print("\n💡 Start GraphDB with: docker-compose -f docker-compose.graphdb.yml up -d")
        sys.exit(1)

    # Run tests for all repositories
    all_results = []
    for repo_config in TEST_REPOS:
        results = await test_repository(repo_config)
        all_results.append(results)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    total_repos = len(all_results)
    passed_repos = 0

    for result in all_results:
        repo_name = result["name"]
        tests = result["tests"]

        # Count passed tests
        passed_tests = sum(1 for t in tests.values() if t.get("status") == "pass")
        total_tests = len(tests)

        if passed_tests == total_tests:
            print(f"✅ {repo_name}: {passed_tests}/{total_tests} tests passed")
            passed_repos += 1
        else:
            print(f"❌ {repo_name}: {passed_tests}/{total_tests} tests passed")

    print(f"\nRepositories: {passed_repos}/{total_repos} fully operational")

    # Detailed recommendations
    if passed_repos < total_repos:
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)

        for result in all_results:
            failed_tests = [
                name for name, test in result["tests"].items()
                if test.get("status") in ["fail", "warn"]
            ]

            if failed_tests:
                print(f"\n{result['name']}:")
                for test_name in failed_tests:
                    test_result = result["tests"][test_name]

                    if test_name == "connectivity":
                        print(f"  ❌ Connectivity failed")
                        print(f"     → Check repository exists: {result['endpoint']}")
                        print(f"     → Verify GraphDB logs: docker logs graphdb")

                    elif test_name == "owl_classes":
                        print(f"  ❌ No OWL classes found")
                        print(f"     → Import RDF data: scripts/import_kg_data.sh")

                    elif test_name == "concepts":
                        if test_result.get("status") == "warn":
                            print(f"  ⚠️  Expected concepts not found")
                            print(f"     → Repository might be empty or data not imported")
                        else:
                            print(f"  ❌ Concept search failed: {test_result.get('error')}")

    print("\n" + "="*70)

    if passed_repos == total_repos:
        print("🎉 All tests passed! GraphDB is ready.")
        print("\nNext step:")
        print("  python scripts/generate_grape_embeddings.py")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix issues above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
