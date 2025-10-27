#!/bin/bash
set -e

# Grape GraphDB Setup Script
# This script initializes GraphDB repositories and loads knowledge graphs

GRAPHDB_URL="http://localhost:7200"
REPO_CONFIG_DIR="./scripts/graphdb-configs"

echo "🍇 Grape GraphDB Setup"
echo "======================"

# Wait for GraphDB to be ready
echo "⏳ Waiting for GraphDB to be ready..."
for i in {1..30}; do
  if curl -sf "${GRAPHDB_URL}/rest/repositories" > /dev/null 2>&1; then
    echo "✅ GraphDB is ready!"
    break
  fi
  echo "   Attempt $i/30..."
  sleep 2
done

# Check if still not ready
if ! curl -sf "${GRAPHDB_URL}/rest/repositories" > /dev/null 2>&1; then
  echo "❌ GraphDB failed to start after 60 seconds"
  exit 1
fi

echo ""
echo "📦 Creating repositories..."

# Function to create a repository
create_repository() {
  local REPO_NAME=$1
  local REPO_LABEL=$2

  echo "  Creating repository: ${REPO_NAME}"

  # Check if repository already exists
  if curl -sf "${GRAPHDB_URL}/rest/repositories/${REPO_NAME}" > /dev/null 2>&1; then
    echo "    ⚠️  Repository ${REPO_NAME} already exists, skipping"
    return
  fi

  # Create repository config
  cat > "/tmp/${REPO_NAME}-config.ttl" <<EOF
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix owlim: <http://www.ontotext.com/trree/owlim#>.

[] a rep:Repository ;
    rep:repositoryID "${REPO_NAME}" ;
    rdfs:label "${REPO_LABEL}" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:FreeSailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:FreeSail" ;
            owlim:ruleset "owl2-rl-optimized" ;
            owlim:base-URL "http://example.org/grape#" ;
            owlim:defaultNS "" ;
            owlim:entity-index-size "10000000" ;
            owlim:entity-id-size  "32" ;
            owlim:imports "" ;
            owlim:repository-type "file-repository" ;
            owlim:storage-folder "storage" ;
            owlim:enable-context-index "true" ;
            owlim:enablePredicateList "true" ;
            owlim:in-memory-literal-properties "true" ;
            owlim:enable-literal-index "true" ;
            owlim:check-for-inconsistencies "false" ;
            owlim:disable-sameAs  "false" ;
            owlim:query-timeout  "0" ;
            owlim:query-limit-results  "0" ;
            owlim:throw-QueryEvaluationException-on-timeout "false" ;
            owlim:read-only "false" ;
        ]
    ].
EOF

  # Create the repository
  curl -X POST \
    -H "Content-Type: application/x-turtle" \
    --data-binary "@/tmp/${REPO_NAME}-config.ttl" \
    "${GRAPHDB_URL}/rest/repositories"

  if [ $? -eq 0 ]; then
    echo "    ✅ Repository ${REPO_NAME} created successfully"
  else
    echo "    ❌ Failed to create repository ${REPO_NAME}"
    exit 1
  fi
}

# Create repositories for each KG
create_repository "demo" "Demo Medical KG"
create_repository "hearing" "Hearing & Tinnitus KG"
create_repository "psychiatry" "Psychiatry & Depression KG"
create_repository "unified" "Unified Medical KG (All graphs + alignment)"

echo ""
echo "📥 Loading knowledge graphs..."

# Function to load Turtle into a repository
load_turtle() {
  local REPO_NAME=$1
  local FILE_PATH=$2
  local GRAPH_URI=$3

  echo "  Loading $(basename ${FILE_PATH}) into ${REPO_NAME}..."

  curl -X POST \
    -H "Content-Type: text/turtle" \
    --data-binary "@${FILE_PATH}" \
    "${GRAPHDB_URL}/repositories/${REPO_NAME}/statements?context=%3C${GRAPH_URI}%3E"

  if [ $? -eq 0 ]; then
    echo "    ✅ Loaded successfully"
  else
    echo "    ❌ Failed to load $(basename ${FILE_PATH})"
    exit 1
  fi
}

# Load hearing KG (TTL)
load_turtle "hearing" "./kg_example/final_demo/hearing_graph.ttl" "http://example.org/hearing/data"

# Load psychiatry KG (TTL)
load_turtle "psychiatry" "./kg_example/final_demo/psyche_graph.ttl" "http://example.org/psych/data"

# Load unified repository (both TTLs)
echo ""
echo "🔗 Creating unified repository with alignment..."
load_turtle "unified" "./kg_example/final_demo/hearing_graph.ttl" "http://example.org/hearing/data"
load_turtle "unified" "./kg_example/final_demo/psyche_graph.ttl" "http://example.org/psych/data"

echo ""
echo "✅ GraphDB setup complete!"
echo ""
echo "📊 Summary:"
echo "   • GraphDB Workbench: ${GRAPHDB_URL}"
echo "   • Repositories created: 4"
echo "     - demo (http://localhost:7200/repositories/demo)"
echo "     - hearing (http://localhost:7200/repositories/hearing)"
echo "     - psychiatry (http://localhost:7200/repositories/psychiatry)"
echo "     - unified (http://localhost:7200/repositories/unified)"
echo ""
echo "🔍 Test SPARQL query:"
echo "   curl -X POST -H 'Accept: application/sparql-results+json' \\"
echo "     --data-urlencode 'query=SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10' \\"
echo "     ${GRAPHDB_URL}/repositories/demo"
echo ""
