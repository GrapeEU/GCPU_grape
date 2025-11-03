from fastapi import APIRouter, HTTPException, Query
from core.config import settings
from app.utils.sparql_toolkit import run_sparql_query
from typing import Dict, Any, List, Tuple
import csv
import io

router = APIRouter(prefix="/graph", tags=["Graph"])

# Aliases to aggregate multiple repositories into a single response (e.g., unified view)
REPO_ALIASES: Dict[str, List[str]] = {}


@router.get("/{repo}/data")
def get_graph_data(repo: str, limit: int = 500):
    repo = repo.lower()
    repo_map = settings.get_repo_endpoint
    target_repos = REPO_ALIASES.get(repo, [repo])

    invalid = [r for r in target_repos if r not in repo_map]
    if invalid:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown repository{'ies' if len(invalid) > 1 else ''}: {', '.join(invalid)}"
        )

    combined_nodes: Dict[str, Dict[str, Any]] = {}
    combined_links: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for target in target_repos:
        endpoint_url = repo_map[target]
        rows = _fetch_repo_rows(endpoint_url, limit)
        _merge_rows_into_graph(rows, target, combined_nodes, combined_links)

    nodes_response: List[Dict[str, Any]] = []
    for node_id, record in combined_nodes.items():
        repos = sorted(record.pop("sourceRepos"))
        node_payload = {
            "id": node_id,
            "label": record["label"],
            "type": record["type"],
            "sourceRepo": repos[0] if len(repos) == 1 else None,
            "sourceRepos": repos,
        }
        nodes_response.append(node_payload)

    links_response: List[Dict[str, Any]] = []
    for (src, tgt, rel), record in combined_links.items():
        repos = sorted(record["sourceRepos"])
        links_response.append({
            "source": src,
            "target": tgt,
            "relation": rel,
            "label": rel,
            "sourceRepo": repos[0] if len(repos) == 1 else None,
            "sourceRepos": repos,
        })

    return {
        "repo": repo,
        "nodes": nodes_response,
        "links": links_response,
    }


def _fetch_repo_rows(endpoint_url: str, limit: int) -> List[Dict[str, str]]:
    query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?source ?relation ?target ?sourceLabel ?targetLabel ?relationLabel
WHERE {{
  ?source ?relation ?target .
  FILTER(isURI(?target))
  FILTER(!STRSTARTS(STR(?relation), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
  FILTER(!STRSTARTS(STR(?relation), "http://www.w3.org/2000/01/rdf-schema#"))
  FILTER(!STRSTARTS(STR(?relation), "http://www.w3.org/2002/07/owl#"))
  FILTER(?target != <http://www.w3.org/2002/07/owl#Thing>)
  OPTIONAL {{ ?source rdfs:label ?sourceLabel }}
  OPTIONAL {{ ?target rdfs:label ?targetLabel }}
  OPTIONAL {{ ?relation rdfs:label ?relationLabel }}
}}
LIMIT {limit}
"""

    try:
        csv_result = run_sparql_query(query, endpoint_url=endpoint_url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {exc}")

    reader = csv.DictReader(io.StringIO(csv_result))
    return list(reader)


def _merge_rows_into_graph(
    rows: List[Dict[str, str]],
    repo: str,
    nodes: Dict[str, Dict[str, Any]],
    links: Dict[Tuple[str, str, str], Dict[str, Any]]
) -> None:
    for row in rows:
        source = row.get("source")
        relation = row.get("relation")
        target = row.get("target")
        if not source or not relation or not target:
            continue

        source_label = row.get("sourceLabel") or _short_label(source)
        target_label = row.get("targetLabel") or _short_label(target)
        relation_label = row.get("relationLabel") or _short_label(relation)

        source_entry = nodes.setdefault(
            source,
            {
                "id": source,
                "label": source_label,
                "type": _infer_node_type(source),
                "sourceRepos": set(),  # type: ignore[assignment]
            },
        )
        source_entry["label"] = source_entry.get("label") or source_label
        source_entry["sourceRepos"].add(repo)  # type: ignore[attr-defined]

        target_entry = nodes.setdefault(
            target,
            {
                "id": target,
                "label": target_label,
                "type": _infer_node_type(target),
                "sourceRepos": set(),  # type: ignore[assignment]
            },
        )
        target_entry["label"] = target_entry.get("label") or target_label
        target_entry["sourceRepos"].add(repo)  # type: ignore[attr-defined]

        link_key = (source, target, relation_label)
        link_entry = links.setdefault(
            link_key,
            {
                "source": source,
                "target": target,
                "relation": relation_label,
                "sourceRepos": set(),  # type: ignore[assignment]
            },
        )
        link_entry["sourceRepos"].add(repo)  # type: ignore[attr-defined]

@router.get("/{repo}/node")
def get_node_details(repo: str, id: str = Query(...)):
    repo = repo.lower()
    repo_map = settings.get_repo_endpoint
    if repo not in repo_map:
        raise HTTPException(status_code=404, detail=f"Unknown repository: {repo}")

    endpoint_url = repo_map[repo]

    def run(query: str) -> list[dict]:
        try:
            csv_result = run_sparql_query(query, endpoint_url=endpoint_url)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to retrieve node details: {exc}")
        return list(csv.DictReader(io.StringIO(csv_result)))

    types_query = f"SELECT ?type WHERE {{ <{id}> a ?type }} LIMIT 25"

    outgoing_query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?predicate ?target ?predicateLabel ?targetLabel
WHERE {{
  <{id}> ?predicate ?target .
  FILTER(isURI(?target))
  FILTER(!STRSTARTS(STR(?predicate), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
  FILTER(!STRSTARTS(STR(?predicate), "http://www.w3.org/2000/01/rdf-schema#"))
  FILTER(!STRSTARTS(STR(?predicate), "http://www.w3.org/2002/07/owl#"))
  OPTIONAL {{ ?predicate rdfs:label ?predicateLabel }}
  OPTIONAL {{ ?target rdfs:label ?targetLabel }}
}}
LIMIT 25
"""

    incoming_query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?source ?predicate ?predicateLabel ?sourceLabel
WHERE {{
  ?source ?predicate <{id}> .
  FILTER(isURI(?source))
  FILTER(!STRSTARTS(STR(?predicate), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
  FILTER(!STRSTARTS(STR(?predicate), "http://www.w3.org/2000/01/rdf-schema#"))
  FILTER(!STRSTARTS(STR(?predicate), "http://www.w3.org/2002/07/owl#"))
  OPTIONAL {{ ?predicate rdfs:label ?predicateLabel }}
  OPTIONAL {{ ?source rdfs:label ?sourceLabel }}
}}
LIMIT 25
"""

    type_rows = run(types_query)
    outgoing_rows = run(outgoing_query)
    incoming_rows = run(incoming_query)

    types = [row["type"] for row in type_rows if row.get("type")]

    outgoing = [
        {
            "predicate": row.get("predicate"),
            "target": row.get("target"),
            "predicateLabel": row.get("predicateLabel") or _short_label(row.get("predicate")),
            "targetLabel": row.get("targetLabel") or _short_label(row.get("target")),
        }
        for row in outgoing_rows
        if row.get("target")
    ]

    incoming = [
        {
            "source": row.get("source"),
            "predicate": row.get("predicate"),
            "predicateLabel": row.get("predicateLabel") or _short_label(row.get("predicate")),
            "sourceLabel": row.get("sourceLabel") or _short_label(row.get("source")),
        }
        for row in incoming_rows
        if row.get("source")
    ]

    return {
        "id": id,
        "types": types,
        "outgoing": outgoing,
        "incoming": incoming,
    }


def _infer_node_type(uri: str) -> str:
    fragment = uri.split("/")[-1]
    if "#" in fragment:
        fragment = fragment.split("#")[-1]
    if ":" in fragment:
        return fragment.split(":")[0]
    return fragment


def _short_label(uri: str | None) -> str:
    if not uri:
        return ""
    fragment = uri.split("/")[-1]
    if "#" in fragment:
        fragment = fragment.split("#")[-1]
    return fragment
