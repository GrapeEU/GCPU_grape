
# Hearing & Tinnitus KG

Evidence base (examples):
- Tinnitus is associated with depression, anxiety, stress, and insomnia (systematic reviews & cohort studies).
- Sleep problems are frequently reported with tinnitus.

Suggested SPARQL:
```sparql
PREFIX exhear: <http://example.org/hearing/>
PREFIX exmed: <http://example.org/med/>
SELECT ?p WHERE {
  ?p exmed:hasSymptom exhear:Insomnia .
}
```

Reasoning rule (OWL property chain idea to try in a reasoner):
- If a Person hasSymptom Insomnia and Insomnia isSymptomOf Tinnitus, infer the Person related to Tinnitus.
You can implement this as a property chain (hasSymptom o isSymptomOf) → relatedCondition in the generic ontology.
