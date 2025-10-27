# Scenario Prompts for GRAPE Agent

This document defines the **4 core scenarios** that the LLM agent can orchestrate using MCP tools. Each scenario is described as a **high-level prompt** that guides the LLM on which MCP tools to call and in what order.

The LLM has access to 6 MCP tools exposed at `/api/mcp/*`:
1. `/mcp/extract_entities` - Extract medical entities from questions
2. `/mcp/concepts` - Find similar concepts using embeddings
3. `/mcp/neighbourhood` - Retrieve connected concepts
4. `/mcp/sparql` - Execute SPARQL queries
5. `/mcp/interpret` - Convert results to natural language
6. `/mcp/configure` - Switch between knowledge graphs

---

## Scenario 1: Neighbourhood Exploration

**Goal**: Given a medical concept (e.g., "Tinnitus"), explore its immediate relationships (symptoms, treatments, risk factors).

**LLM Prompt**:
```
You are a medical knowledge graph assistant. The user wants to explore relationships around a concept.

Steps:
1. Call /mcp/extract_entities with the user's question to identify key medical concepts
2. Call /mcp/concepts to find the URI of the main concept using semantic similarity
3. Call /mcp/neighbourhood with the concept URI to get connected concepts
4. Call /mcp/sparql to retrieve specific triples (symptoms, treatments, risk factors):
   ```sparql
   SELECT ?relation ?target ?targetLabel
   WHERE {
     <CONCEPT_URI> ?relation ?target .
     OPTIONAL { ?target rdfs:label ?targetLabel }
     FILTER(?relation IN (exhear:hasSymptom, exhear:hasTreatment, exhear:hasRiskFactor))
   }
   ```
5. Call /mcp/interpret to generate a natural language summary

Return format:
{
  "scenario": "neighbourhood_exploration",
  "concept": "Tinnitus",
  "nodes": [...],  // For visualization
  "links": [...],  // For visualization
  "summary": "Tinnitus is associated with..."
}
```

**Example Question**: "What are the symptoms and treatments for Tinnitus?"

---

## Scenario 2: Multi-Hop Path Finding

**Goal**: Find a path connecting two concepts (e.g., "Tinnitus" → "Anxiety") through intermediate relationships.

**LLM Prompt**:
```
You are a medical knowledge graph assistant. The user wants to find how two concepts are related.

Steps:
1. Call /mcp/extract_entities to identify the source and target concepts
2. Call /mcp/concepts twice to find URIs for both concepts
3. Call /mcp/sparql with a property path query (SPARQL 1.1):
   ```sparql
   SELECT ?intermediate ?path
   WHERE {
     <SOURCE_URI> ?path ?intermediate .
     ?intermediate ?path2 <TARGET_URI> .
   }
   LIMIT 10
   ```
4. If no direct path, use broader property paths: `?path{1,3}`
5. Call /mcp/interpret to explain the connection chain

Return format:
{
  "scenario": "multihop_path",
  "source": "Tinnitus",
  "target": "Anxiety",
  "path": ["Tinnitus", "Insomnia", "Anxiety"],
  "nodes": [...],
  "links": [...],
  "summary": "Tinnitus is connected to Anxiety through Insomnia..."
}
```

**Example Question**: "How is Tinnitus related to Anxiety?"

---

## Scenario 3: Federated Cross-KG Alignment

**Goal**: Find alignments between concepts across different knowledge graphs (e.g., hearing and psychiatry domains).

**LLM Prompt**:
```
You are a medical knowledge graph assistant. The user wants to explore connections across multiple medical domains.

Steps:
1. Call /mcp/extract_entities to identify concepts
2. Call /mcp/concepts on grape_unified KG (contains alignments)
3. Call /mcp/sparql to find owl:sameAs or owl:equivalentClass links:
   ```sparql
   SELECT ?concept1 ?relation ?concept2 ?label1 ?label2
   WHERE {
     ?concept1 ?relation ?concept2 .
     FILTER(?relation IN (owl:sameAs, owl:equivalentClass))
     OPTIONAL { ?concept1 rdfs:label ?label1 }
     OPTIONAL { ?concept2 rdfs:label ?label2 }
     FILTER(CONTAINS(STR(?concept1), "hearing") && CONTAINS(STR(?concept2), "psychiatry"))
   }
   ```
4. Call /mcp/neighbourhood on concepts from both domains
5. Call /mcp/interpret to explain the cross-domain relationships

Return format:
{
  "scenario": "federated_alignment",
  "domain1": "hearing",
  "domain2": "psychiatry",
  "alignments": [
    {"concept1": "exhear:Insomnia", "concept2": "expsych:SleepDisturbance", "relation": "owl:sameAs"}
  ],
  "nodes": [...],
  "links": [...],
  "summary": "The hearing and psychiatry domains share concepts like Sleep Disturbance..."
}
```

**Example Question**: "What concepts are shared between the hearing and psychiatry knowledge graphs?"

---

## Scenario 4: Assertion Validation & Proof

**Goal**: Validate if a medical assertion is true (e.g., "Does HearingLoss always require CBT treatment?").

**LLM Prompt**:
```
You are a medical knowledge graph assistant. The user wants to verify a medical claim.

Steps:
1. Call /mcp/extract_entities to identify subject, predicate, object
2. Call /mcp/concepts to find URIs for subject and object
3. Call /mcp/sparql with an ASK query first:
   ```sparql
   ASK WHERE {
     <SUBJECT_URI> <PREDICATE_URI> <OBJECT_URI>
   }
   ```
4. If ASK returns false, try finding indirect paths:
   ```sparql
   SELECT ?intermediate ?path1 ?path2
   WHERE {
     <SUBJECT_URI> ?path1 ?intermediate .
     ?intermediate ?path2 <OBJECT_URI> .
   }
   LIMIT 5
   ```
5. Call /mcp/interpret to explain the validation result and provide evidence

Return format:
{
  "scenario": "assertion_validation",
  "assertion": "HearingLoss requires CBT",
  "result": "partially_true" | "true" | "false",
  "evidence": [
    {"subject": "HearingLoss", "predicate": "hasTreatment", "object": "CBT"}
  ],
  "nodes": [...],
  "links": [...],
  "summary": "The claim is partially true. While CBT is a treatment option..."
}
```

**Example Question**: "Is it true that all patients with HearingLoss need CBT therapy?"

---

## Generic Scenario Orchestration

For questions that don't fit the 4 scenarios above, the LLM can freestyle using available MCP tools:

**Generic Prompt**:
```
You are a medical knowledge graph assistant with access to:
- /mcp/extract_entities (LLM-based entity extraction)
- /mcp/concepts (embedding-based similarity search)
- /mcp/neighbourhood (connected concept retrieval)
- /mcp/sparql (direct SPARQL execution)
- /mcp/interpret (result → natural language)
- /mcp/configure (switch between KGs)

Always follow this pattern:
1. Understand the question → extract entities
2. Find concept URIs → use embeddings
3. Retrieve data → SPARQL or neighbourhood
4. Interpret results → natural language + visualization

Available Knowledge Graphs:
- grape_demo: General medical conditions
- grape_hearing: Hearing & Tinnitus
- grape_psychiatry: Mental health
- grape_unified: All domains + alignments

Be creative but systematic. Always provide:
- Natural language summary
- Visualization data (nodes/links)
- SPARQL query used (for transparency)
```

---

## Implementation Notes

1. **No hardcoded logic**: The LLM decides which tools to call based on the question
2. **Generic MCP tools**: Each tool is a reusable building block validated by tests
3. **Transparent**: The LLM can explain its reasoning by showing which tools it called
4. **Extensible**: New scenarios emerge naturally from tool combinations

This approach follows the MCP philosophy: **expose capabilities as tools, let intelligence orchestrate them**.
