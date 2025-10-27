
# Medical KG demo (JSON-LD + OWL)

This package contains three knowledge graph folders:
1. `kg_demo_simple/` — generic medical ontology + a tiny graph (~25 relations) to test tools/LLM reasoning.
2. `kg_hearing_tinnitus/` — hearing & tinnitus-focused ontology + dataset (includes sleep and mood symptoms).
3. `kg_psychiatry_depression/` — psychiatry & depression-focused ontology + dataset.
A cross-graph `alignment.jsonld` maps shared concepts (e.g., SleepDisturbance) to enable bridging inferences.

## Files
- `ontology.jsonld`: OWL terms in JSON-LD (classes, properties, property chains, equivalences).
- `data.jsonld`: instance-level triples for demos.
- `alignment.jsonld` at the root connects graphs.

## Quick start
- Load in Protégé (JSON-LD), GraphDB, Stardog, or RDFLib.
- Try SPARQL (suggestions in each folder README).

## Reasoning idea (your A→B→C vs E→F→G→C→P)
- Both hearing and psych KGs declare `SleepDisturbance` (C) as equivalent. If your reasoner accepts `owl:equivalentClass` / `owl:sameAs`, you can traverse across graphs to relate, e.g., **Tinnitus (A)** to **MajorDepression (P)** via **C** with supporting symptoms.
