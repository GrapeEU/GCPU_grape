#!/usr/bin/env python3
"""
Test SPARQL queries against GraphDB repositories
"""

import requests
import json
from typing import Dict, Any

GRAPHDB_URL = "http://localhost:7200"
REPOSITORIES = ["demo", "hearing", "psychiatry", "unified", "socrates"]


def execute_sparql_query(repo: str, query: str) -> Dict[str, Any]:
    """Execute a SPARQL query against a repository"""
    endpoint = f"{GRAPHDB_URL}/repositories/{repo}"

    headers = {
        "Accept": "application/sparql-results+json"
    }

    data = {
        "query": query
    }

    try:
        response = requests.post(endpoint, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error querying {repo}: {e}")
        return None


def test_repository(repo: str):
    """Test basic queries on a repository"""
    print(f"\n{'='*60}")
    print(f"Testing repository: {repo}")
    print(f"{'='*60}")

    # Query 1: Count triples
    print("\n📊 Query 1: Count total triples")
    query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
    result = execute_sparql_query(repo, query)
    if result:
        count = result['results']['bindings'][0]['count']['value']
        print(f"   Total triples: {count}")

    # Query 2: List classes
    print("\n📋 Query 2: List OWL classes")
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?class ?label WHERE {
      ?class a owl:Class .
      OPTIONAL { ?class rdfs:label ?label }
    } LIMIT 10
    """
    result = execute_sparql_query(repo, query)
    if result and result['results']['bindings']:
        print("   Classes found:")
        for binding in result['results']['bindings']:
            class_uri = binding['class']['value']
            label = binding.get('label', {}).get('value', 'N/A')
            print(f"     • {label} ({class_uri})")

    # Query 3: List properties
    print("\n🔗 Query 3: List object properties")
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?property ?label WHERE {
      ?property a owl:ObjectProperty .
      OPTIONAL { ?property rdfs:label ?label }
    } LIMIT 10
    """
    result = execute_sparql_query(repo, query)
    if result and result['results']['bindings']:
        print("   Properties found:")
        for binding in result['results']['bindings']:
            prop_uri = binding['property']['value']
            label = binding.get('label', {}).get('value', 'N/A')
            print(f"     • {label} ({prop_uri})")


def test_reasoning():
    """Test reasoning capabilities on unified repository"""
    print(f"\n{'='*60}")
    print("🧠 Testing OWL reasoning (unified repository)")
    print(f"{'='*60}")

    # Query for cross-KG equivalences
    print("\n🔍 Query: Find equivalent classes across KGs")
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?class1 ?class2 ?label1 ?label2 WHERE {
      ?class1 owl:equivalentClass ?class2 .
      FILTER(?class1 != ?class2)
      OPTIONAL { ?class1 rdfs:label ?label1 }
      OPTIONAL { ?class2 rdfs:label ?label2 }
    }
    """
    result = execute_sparql_query("unified", query)
    if result and result['results']['bindings']:
        print("   Equivalent classes:")
        for binding in result['results']['bindings']:
            c1 = binding.get('label1', {}).get('value', binding['class1']['value'])
            c2 = binding.get('label2', {}).get('value', binding['class2']['value'])
            print(f"     • {c1} ≡ {c2}")
    else:
        print("   No equivalences found (check if reasoner is enabled)")

    # Query for symptoms shared across conditions
    print("\n🔍 Query: Find symptoms across all KGs")
    query = """
    PREFIX exmed: <http://example.org/med/>
    PREFIX exhear: <http://example.org/hearing/>
    PREFIX expsych: <http://example.org/psych/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?condition ?symptom ?cLabel ?sLabel WHERE {
      {
        ?condition exmed:hasSymptom ?symptom .
      } UNION {
        ?condition exhear:hasSymptom ?symptom .
      } UNION {
        ?condition expsych:hasSymptom ?symptom .
      }
      OPTIONAL { ?condition rdfs:label ?cLabel }
      OPTIONAL { ?symptom rdfs:label ?sLabel }
    } LIMIT 20
    """
    result = execute_sparql_query("unified", query)
    if result and result['results']['bindings']:
        print("   Condition → Symptom relationships:")
        for binding in result['results']['bindings']:
            c = binding.get('cLabel', {}).get('value', 'Unknown condition')
            s = binding.get('sLabel', {}).get('value', 'Unknown symptom')
            print(f"     • {c} → {s}")


def main():
    print("🍇 Grape Knowledge Graph - SPARQL Test Suite")
    print("=" * 60)

    # Test each repository
    for repo in REPOSITORIES:
        test_repository(repo)

    # Test reasoning on unified
    test_reasoning()

    print("\n" + "=" * 60)
    print("✅ Test suite complete!")
    print(f"   GraphDB Workbench: {GRAPHDB_URL}")
    print("=" * 60)


if __name__ == "__main__":
    main()
