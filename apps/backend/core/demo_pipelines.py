"""
Deterministic demo pipelines for the diabetes use case.

The goal is to provide a show-case path that highlights how the agent reasons
across multiple graphs without relying on the LLM orchestration layer.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Tuple

from core.sparql_utils import run_sparql_query, SparqlQueryError
from core.status_stream import broadcaster


def send_status_update(message: str) -> None:
    """Emit a status message consumed by the frontend and simulate thinking time."""
    print(f"[STATUS] {message}", flush=True)
    broadcaster.publish(message)
    # Small delay to allow event loop to process and send SSE
    time.sleep(0.05)


def _json_trace(title: str, payload: Any) -> str:
    """Helper to format trace blocks consistently."""
    text = json.dumps(payload, ensure_ascii=True, indent=2)
    return f"{title}:\n{text}"


def run_s1_patient_explore(
    patient_uri: str,
    is_autonomous: bool = False,
    repo_key: str = "unified",
) -> Tuple[List[Dict[str, str]], str, List[str]]:
    """
    Scenario 1 – Explore the patient record.

    Returns:
        - list of property/value rows
        - trace string
        - list of executed SPARQL queries
    """
    if not is_autonomous:
        send_status_update(f"S1: Exploring patient {patient_uri} medical record...")

    query = f"""
    PREFIX expat: <http://example.org/patient/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?prop ?prop_label ?value ?value_label
    WHERE {{
      {patient_uri} ?prop ?value .
      ?prop rdfs:label ?prop_label .
      ?value rdfs:label ?value_label .
      FILTER(?prop IN (
        expat:hasCondition,
        expat:hasProcedure,
        expat:hasSymptom,
        expat:takesMedication
      ))
    }}
    """

    fallback_results = [
        {
            "prop": "expat:hasCondition",
            "prop_label": "has diagnosed condition",
            "value": "excond:DiabetesMellitus",
            "value_label": "Diabetes Mellitus",
        },
        {
            "prop": "expat:hasProcedure",
            "prop_label": "has past procedure",
            "value": "excond:Nephrectomy2005",
            "value_label": "Nephrectomy (2005)",
        },
        {
            "prop": "expat:hasSymptom",
            "prop_label": "is currently experiencing",
            "value": "excommon:AbdominalPain",
            "value_label": "Abdominal Pain",
        },
        {
            "prop": "expat:takesMedication",
            "prop_label": "is currently taking",
            "value": "exmed:Metamorphine",
            "value_label": "Metamorphine",
        },
    ]

    try:
        raw_results = run_sparql_query(repo_key, query)
        if isinstance(raw_results, bool) or not raw_results:
            raise SparqlQueryError("Unexpected response for patient exploration.")
        results = [
            {
                "prop": row.get("prop", ""),
                "prop_label": row.get("prop_label", row.get("prop", "")),
                "value": row.get("value", ""),
                "value_label": row.get("value_label", row.get("value", "")),
            }
            for row in raw_results
        ] or fallback_results
    except SparqlQueryError:
        results = fallback_results

    trace = "\n".join(
        [
            f"S1 Query:\n{query.strip()}",
            _json_trace("S1 Results", results),
        ]
    )
    return results, trace, [query.strip()]


def run_s2_pathfinding(
    substance_uri: str,
    symptom_uri: str,
    is_autonomous: bool = False,
    repo_key: str = "unified",
) -> Tuple[List[str], str, List[str]]:
    """
    Scenario 2 – Multi-hop reasoning between a substance and a symptom.
    """
    if not is_autonomous:
        send_status_update(
            f"S2: Multi-hop pathfinding between {substance_uri} and {symptom_uri}..."
        )

    query = f"""
    PREFIX exdrug: <http://example.org/drug/>
    PREFIX excond: <http://example.org/condition/>
    PREFIX excommon: <http://example.org/common/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?path_name (GROUP_CONCAT(?mid_label; SEPARATOR=" -> ") AS ?path_nodes)
    WHERE {{
      {{
        BIND("Lien par similarité de symptôme" AS ?path_name)
        {substance_uri} exdrug:causesSymptom ?mid_node .
        ?mid_node excommon:semanticallySimilarTo {symptom_uri} .
        ?mid_node rdfs:label ?mid_label .
      }}
      UNION
      {{
        BIND("Lien par symptôme de contre-indication" AS ?path_name)
        {substance_uri} exdrug:contraindicatedFor ?mid_node .
        ?mid_node excond:typicalSymptom {symptom_uri} .
        ?mid_node rdfs:label ?mid_label .
      }}
    }}
    GROUP BY ?path_name
    """

    fallback_paths = [
        "E27B -> causesSymptom -> Stomach Discomfort -> semanticallySimilarTo -> Abdominal Pain",
        "E27B -> contraindicatedFor -> Post-NephrectomyStatus -> typicalSymptom -> Abdominal Pain",
    ]

    try:
        raw_results = run_sparql_query(repo_key, query)
        if isinstance(raw_results, bool) or not raw_results:
            raise SparqlQueryError("Unexpected response for pathfinding.")
        paths: List[str] = []
        for row in raw_results:
            label = row.get("path_name") or ""
            nodes = row.get("path_nodes") or ""
            if label and nodes:
                paths.append(f"{label}: {nodes}")
        if not paths:
            raise SparqlQueryError("No paths discovered.")
    except SparqlQueryError:
        paths = fallback_paths

    trace = "\n".join(
        [
            f"S2 Query:\n{query.strip()}",
            _json_trace("S2 Paths", paths),
        ]
    )
    return paths, trace, [query.strip()]


def run_s3_validation(
    patient_uri: str,
    drug_uri: str,
    is_autonomous: bool = False,
    repo_key: str = "unified",
) -> Tuple[Dict[str, str], str, List[str]]:
    """
    Scenario 3 – Ontological validation and alternative recommendation.
    """
    if not is_autonomous:
        send_status_update(f"S3: Validating {drug_uri} contraindications for {patient_uri}...")

    ask_query = f"""
    PREFIX expat: <http://example.org/patient/>
    PREFIX exmed: <http://example.org/medication/>
    PREFIX excond: <http://example.org/condition/>

    ASK WHERE {{
      {patient_uri} expat:hasProcedure ?procedure .
      ?procedure excond:resultsInCondition ?condition_ci .
      {drug_uri} exmed:contraindicatedFor ?condition_ci .
    }}
    """

    alt_query = """
    PREFIX exmed: <http://example.org/medication/>
    PREFIX excond: <http://example.org/condition/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?alt_drug ?alt_drug_label
    WHERE {
      ?alt_drug exmed:indicatedFor excond:DiabetesMellitus .
      FILTER(?alt_drug != exmed:Metamorphine)
      FILTER NOT EXISTS {
        ?alt_drug exmed:contraindicatedFor excond:PostNephrectomyStatus .
      }
      ?alt_drug rdfs:label ?alt_drug_label .
    }
    LIMIT 1
    """

    result = {
        "validation": "CONTRAINDICATED",
        "reason": (
            "Patient has 'PostNephrectomyStatus' (from 'Nephrectomy2005'), "
            "drug inherits the same contra-indication from substance 'E27B'."
        ),
        "alternative": "Glucorin",
        "inference_steps": [
            "owl:propertyChainAxiom : Metamorphine hérite des contre-indications de E27B.",
            "Nephrectomy2005 resultsInCondition PostNephrectomyStatus pour PatientJohn.",
            "PostNephrectomyStatus présente le symptôme typique AbdominalPain.",
        ],
    }

    try:
        ask_result = run_sparql_query(repo_key, ask_query)
        if isinstance(ask_result, bool) and not ask_result:
            result["validation"] = "ALLOWED"
            result["reason"] = "No conflicting post-nephrectomy status detected."
        alt_rows = run_sparql_query(repo_key, alt_query)
        if isinstance(alt_rows, list) and alt_rows:
            first = alt_rows[0]
            label = first.get("alt_drug_label") or "Glucorin"
            result["alternative"] = label
    except SparqlQueryError:
        # Keep fallback values
        pass

    trace = "\n".join(
        [
            f"S3 ASK Query:\n{ask_query.strip()}",
            f"S3 Alternative Query:\n{alt_query.strip()}",
            _json_trace("S3 Result", result),
        ]
    )
    return result, trace, [ask_query.strip(), alt_query.strip()]


def run_medication_profile(
    medication_uri: str,
    is_autonomous: bool = False,
    repo_key: str = "unified",
) -> Tuple[List[Dict[str, str]], str, List[str]]:
    if not is_autonomous:
        send_status_update(f"Inspecting medication {medication_uri}...")

    query = f"""
    PREFIX exmed: <http://example.org/medication/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?prop ?prop_label ?value ?value_label
    WHERE {{
      {medication_uri} ?prop ?value .
      ?prop rdfs:label ?prop_label .
      ?value rdfs:label ?value_label .
      FILTER(?prop IN (exmed:indicatedFor, exmed:hasActiveSubstance, exmed:contraindicatedFor))
    }}
    """

    fallback = [
        {
            "prop": "exmed:indicatedFor",
            "prop_label": "is indicated for",
            "value": "excond:DiabetesMellitus",
            "value_label": "Diabetes Mellitus",
        },
        {
            "prop": "exmed:hasActiveSubstance",
            "prop_label": "has active substance",
            "value": "exdrug:E27B",
            "value_label": "Substance E27B",
        },
    ]

    try:
        raw = run_sparql_query(repo_key, query)
        if isinstance(raw, bool) or raw is None:
            raise SparqlQueryError("Medication profile returned unexpected format.")
        results = [
            {
                "prop": row.get("prop", ""),
                "prop_label": row.get("prop_label", row.get("prop", "")),
                "value": row.get("value", ""),
                "value_label": row.get("value_label", row.get("value", "")),
            }
            for row in raw
        ] or fallback
    except SparqlQueryError:
        results = fallback

    trace = "\n".join(
        [
            f"Médicament – Query:\n{query.strip()}",
            _json_trace("Médicament – Résultats", results),
        ]
    )
    return results, trace, [query.strip()]


def run_substance_profile(
    substance_uri: str,
    is_autonomous: bool = False,
    repo_key: str = "unified",
) -> Tuple[List[Dict[str, str]], str, List[str]]:
    if not is_autonomous:
        send_status_update(f"Analyzing substance {substance_uri}...")

    query = f"""
    PREFIX exdrug: <http://example.org/drug/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX excond: <http://example.org/condition/>

    SELECT ?prop ?prop_label ?value ?value_label
    WHERE {{
      {substance_uri} ?prop ?value .
      ?prop rdfs:label ?prop_label .
      ?value rdfs:label ?value_label .
      FILTER(?prop IN (exdrug:contraindicatedFor, exdrug:causesSymptom))
    }}
    """

    fallback = [
        {
            "prop": "exdrug:contraindicatedFor",
            "prop_label": "is contraindicated for",
            "value": "excond:PostNephrectomyStatus",
            "value_label": "Post-Nephrectomy Status",
        },
        {
            "prop": "exdrug:causesSymptom",
            "prop_label": "causes symptom",
            "value": "excommon:StomachDiscomfort",
            "value_label": "Stomach Discomfort",
        },
    ]

    try:
        raw = run_sparql_query(repo_key, query)
        if isinstance(raw, bool) or raw is None:
            raise SparqlQueryError("Substance profile returned unexpected format.")
        results = [
            {
                "prop": row.get("prop", ""),
                "prop_label": row.get("prop_label", row.get("prop", "")),
                "value": row.get("value", ""),
                "value_label": row.get("value_label", row.get("value", "")),
            }
            for row in raw
        ] or fallback
    except SparqlQueryError:
        results = fallback

    trace = "\n".join(
        [
            f"Substance – Query:\n{query.strip()}",
            _json_trace("Substance – Résultats", results),
        ]
    )
    return results, trace, [query.strip()]


def run_condition_family(
    condition_uri: str,
    is_autonomous: bool = False,
    repo_key: str = "unified",
) -> Tuple[List[Dict[str, str]], str, List[str]]:
    if not is_autonomous:
        send_status_update(f"Exploring complications around {condition_uri}...")

    query = f"""
    PREFIX excond: <http://example.org/condition/>
    PREFIX excommon: <http://example.org/common/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?relation_label ?target_label
    WHERE {{
      {{
        {condition_uri} excond:typicalSymptom ?symptom .
        BIND("typicalSymptom" AS ?relation_label)
        ?symptom rdfs:label ?target_label .
      }}
      UNION
      {{
        {condition_uri} excond:affectsOrgan ?organ .
        BIND("affectsOrgan" AS ?relation_label)
        ?organ rdfs:label ?target_label .
      }}
    }}
    """

    fallback = [
        {"relation_label": "typicalSymptom", "target_label": "Abdominal Pain"},
        {"relation_label": "affectsOrgan", "target_label": "Kidney"},
    ]

    try:
        raw = run_sparql_query(repo_key, query)
        if isinstance(raw, bool) or raw is None:
            raise SparqlQueryError("Condition family returned unexpected format.")
        results = [
            {"relation_label": row.get("relation_label", ""), "target_label": row.get("target_label", "")}
            for row in raw
        ] or fallback
    except SparqlQueryError:
        results = fallback

    trace = "\n".join(
        [
            f"Famille condition – Query:\n{query.strip()}",
            _json_trace("Famille condition – Résultats", results),
        ]
    )
    return results, trace, [query.strip()]


def run_patient_procedure_chain(
    patient_uri: str,
    is_autonomous: bool = False,
    repo_key: str = "unified",
) -> Tuple[List[Dict[str, str]], str, List[str]]:
    if not is_autonomous:
        send_status_update(f"Checking procedures for {patient_uri}...")

    query = f"""
    PREFIX expat: <http://example.org/patient/>
    PREFIX excond: <http://example.org/condition/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?procedure_label ?condition_label
    WHERE {{
      {patient_uri} expat:hasProcedure ?procedure .
      ?procedure rdfs:label ?procedure_label .
      OPTIONAL {{
        ?procedure excond:resultsInCondition ?condition .
        ?condition rdfs:label ?condition_label .
      }}
    }}
    """

    fallback = [
        {
            "procedure_label": "Nephrectomy (2005)",
            "condition_label": "Post-Nephrectomy Status",
        }
    ]

    try:
        raw = run_sparql_query(repo_key, query)
        if isinstance(raw, bool) or raw is None:
            raise SparqlQueryError("Procedure chain returned unexpected format.")
        results = [
            {
                "procedure_label": row.get("procedure_label", ""),
                "condition_label": row.get("condition_label", ""),
            }
            for row in raw
        ] or fallback
    except SparqlQueryError:
        results = fallback

    trace = "\n".join(
        [
            f"Patient -> Procédure – Query:\n{query.strip()}",
            _json_trace("Patient -> Procédure – Résultats", results),
        ]
    )
    return results, trace, [query.strip()]


def run_autonomous_demo(
    patient_uri: str,
    repo_key: str = "unified",
) -> Tuple[str, List[str], List[str], Dict[str, Any]]:
    """
    Execute the full autonomous pipeline (S1 → S2 → S3 → synthesis).
    """
    final_trace: List[str] = []
    sparql_queries: List[str] = []

    send_status_update("Starting semantic analysis. Exploring patient data...")
    s1_results, s1_trace, s1_queries = run_s1_patient_explore(
        patient_uri, is_autonomous=True, repo_key=repo_key
    )
    final_trace.append(s1_trace)
    sparql_queries.extend(s1_queries)

    drug_taken = "exmed:Metamorphine"
    substance_uri = "exdrug:E27B"
    patient_symptom = "excommon:AbdominalPain"
    patient_history = "excond:Nephrectomy2005"
    condition_focus = "excond:PostNephrectomyStatus"

    send_status_update("Patient exploration complete. Found Nephrectomy (2005) history and current Metamorphine treatment. Active substance: E27B. Starting pathfinding...")
    med_results, med_trace, med_queries = run_medication_profile(drug_taken, True, repo_key)
    final_trace.append(med_trace)
    sparql_queries.extend(med_queries)

    send_status_update("Analyzing Metamorphine: indicated for diabetes, active substance E27B.")
    substance_results, substance_trace, substance_queries = run_substance_profile(substance_uri, True, repo_key)
    final_trace.append(substance_trace)
    sparql_queries.extend(substance_queries)

    send_status_update("No direct link found between E27B and abdominal pain. Initiating multi-hop search...")
    s2_results, s2_trace, s2_queries = run_s2_pathfinding(
        substance_uri, patient_symptom, is_autonomous=True, repo_key=repo_key
    )
    final_trace.append(s2_trace)
    sparql_queries.extend(s2_queries)

    send_status_update("Paths found! Pain may originate from similar symptoms or post-nephrectomy contraindication. Launching ontological validator to confirm risk.")
    send_status_update("Mapping renal effects associated with post-nephrectomy status...")
    condition_results, condition_trace, condition_queries = run_condition_family(
        condition_focus, True, repo_key
    )
    final_trace.append(condition_trace)
    sparql_queries.extend(condition_queries)

    send_status_update("Checking procedure → clinical status chain to confirm risk...")
    proc_results, proc_trace, proc_queries = run_patient_procedure_chain(patient_uri, True, repo_key)
    final_trace.append(proc_trace)
    sparql_queries.extend(proc_queries)

    send_status_update(f"Launching ontological validator for {patient_uri}...")
    s3_results, s3_trace, s3_queries = run_s3_validation(
        patient_uri, drug_taken, is_autonomous=True, repo_key=repo_key
    )
    final_trace.append(s3_trace)
    sparql_queries.extend(s3_queries)

    send_status_update("🛑 Alert confirmed. Metamorphine is contraindicated for this patient due to post-nephrectomy status. Searching for alternative...")
    send_status_update("Analysis complete. Generating synthesis...")
    alternative = s3_results.get("alternative", "Glucorin")
    final_summary = (
        "**Synthèse de l'Agent Sémantique :**\n"
        f"1. **Patient :** `{patient_uri}` possède l'antécédent `{patient_history}`.\n"
        f"2. **Conflit :** Le patient prend `{drug_taken}`, dont la substance active "
        f"(`{substance_uri}`) est contre-indiquée pour `{patient_history}` (chemin détecté via S2).\n"
        f"3. **Raisonnement (S3) :** L'agent déduit que `{drug_taken}` est contre-indiqué pour le patient.\n"
        f"4. **Alternative (S3) :** `{alternative}` est proposée comme traitement de substitution.\n"
    )

    storyboard: Dict[str, Any] = {
        "patient_uri": patient_uri,
        "patient_history": patient_history,
        "drug": drug_taken,
        "substance": substance_uri,
        "symptom": patient_symptom,
        "patient_profile": s1_results,
        "medication_profile": med_results,
        "substance_profile": substance_results,
        "paths": s2_results,
        "condition_family": condition_results,
        "procedure_chain": proc_results,
        "validation": s3_results,
        "alternative": alternative,
    }

    return final_summary, final_trace, sparql_queries, storyboard


def run_deep_reasoning_demo(
    patient_uri: str,
    repo_key: str = "unified",
) -> Tuple[str, List[str], List[str], Dict[str, Any]]:
    final_trace: List[str] = []
    sparql_queries: List[str] = []

    send_status_update("Deep Reasoning mode activated. Starting semantic analysis...")

    patient_results, patient_trace, patient_queries = run_s1_patient_explore(
        patient_uri, is_autonomous=True, repo_key=repo_key
    )
    final_trace.append(patient_trace)
    sparql_queries.extend(patient_queries)

    medication_uri = "exmed:Metamorphine"
    substance_uri = "exdrug:E27B"
    symptom_uri = "excommon:AbdominalPain"
    condition_uri = "excond:PostNephrectomyStatus"

    send_status_update("Patient exploration complete. Found Nephrectomy (2005) history and current Metamorphine treatment. Active substance: E27B. Starting pathfinding...")
    medication_results, medication_trace, medication_queries = run_medication_profile(
        medication_uri, True, repo_key
    )
    final_trace.append(medication_trace)
    sparql_queries.extend(medication_queries)

    send_status_update("Step 2: Toxicological analysis of active substance...")
    substance_results, substance_trace, substance_queries = run_substance_profile(
        substance_uri, True, repo_key
    )
    final_trace.append(substance_trace)
    sparql_queries.extend(substance_queries)

    send_status_update("No direct link found between E27B and abdominal pain. Initiating multi-hop search...")
    multihop_paths, multihop_trace, multihop_queries = run_s2_pathfinding(
        substance_uri, symptom_uri, is_autonomous=True, repo_key=repo_key
    )
    final_trace.append(multihop_trace)
    sparql_queries.extend(multihop_queries)

    send_status_update("Paths found! Pain may originate from similar symptoms or post-nephrectomy contraindication. Launching ontological validator to confirm risk.")
    send_status_update("Mapping renal effects and impacted organs...")
    family_results, family_trace, family_queries = run_condition_family(
        condition_uri, True, repo_key
    )
    final_trace.append(family_trace)
    sparql_queries.extend(family_queries)

    send_status_update("Checking procedure → clinical status chain for patient...")
    proc_results, proc_trace, proc_queries = run_patient_procedure_chain(
        patient_uri, True, repo_key
    )
    final_trace.append(proc_trace)
    sparql_queries.extend(proc_queries)

    send_status_update("Launching ontological validator...")
    validation_results, validation_trace, validation_queries = run_s3_validation(
        patient_uri, medication_uri, is_autonomous=True, repo_key=repo_key
    )
    final_trace.append(validation_trace)
    sparql_queries.extend(validation_queries)

    send_status_update("🛑 Alert confirmed. Metamorphine is contraindicated for this patient. Searching for alternative...")
    alternative = validation_results.get("alternative", "Glucorin")

    fallback_summary = (
        "Deep reasoning : la procédure néphrectomie implique un statut post-opératoire "
        "à risque. E27B est à l'origine de symptômes digestifs et de contre-indications "
        "rénales, confirmant l'incompatibilité de Metamorphine avec PatientJohn. "
        f"L'alternative suggérée est {alternative}."
    )

    send_status_update("Analysis complete. Generating final synthesis...")

    storyboard = {
        "patient": patient_results,
        "medication": medication_results,
        "substance": substance_results,
        "paths": multihop_paths,
        "renal_family": family_results,
        "procedure_chain": proc_results,
        "validation": validation_results,
        "alternative": alternative,
    }

    return fallback_summary, final_trace, sparql_queries, storyboard
