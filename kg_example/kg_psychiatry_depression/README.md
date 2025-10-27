
# Psychiatry & Depression KG

Key links:
- Depression often co-occurs with insomnia; CBT/SSRIs common interventions.
- Shares `SleepDisturbance` with hearing KG for cross-graph inference.

Suggested SPARQL (find conditions connected via shared symptoms):
```sparql
PREFIX expsych: <http://example.org/psych/>
PREFIX exmed: <http://example.org/med/>
SELECT ?cond WHERE {
  ?cond expsych:hasSymptom expsych:Insomnia .
}
```
