"""
Lightweight SPARQL helpers for demo pipelines.

Provides a thin wrapper around the GraphDB HTTP endpoint so deterministic
pipelines can issue SELECT / ASK queries without going through the MCP stack.
"""

from __future__ import annotations

from typing import Any, Dict, List, Union

import httpx

from core.config import settings


class SparqlQueryError(RuntimeError):
    """Raised when a SPARQL query fails to execute."""


def _resolve_endpoint(repo_key: str) -> str:
    """
    Resolve a repository key (e.g. "unified" or "grape_unified") to an endpoint URL.
    """
    if not repo_key:
        repo_key = "unified"

    normalized = repo_key.lower().replace("grape_", "")
    endpoint_map = {
        "demo": settings.graphdb_repo_demo,
        "hearing": settings.graphdb_repo_hearing,
        "psychiatry": settings.graphdb_repo_psychiatry,
        "unified": settings.graphdb_repo_unified,
    }

    endpoint = endpoint_map.get(normalized)
    if not endpoint:
        raise SparqlQueryError(f"Unknown GraphDB repository: {repo_key}")
    return endpoint


def run_sparql_query(repo_key: str, query: str) -> Union[bool, List[Dict[str, Any]]]:
    """
    Execute a SPARQL query against the configured GraphDB repository.

    Returns:
        - list of bindings (List[Dict[str, str]]) for SELECT queries
        - boolean for ASK queries
        - raises SparqlQueryError for failures
    """
    if not isinstance(query, str) or not query.strip():
        raise SparqlQueryError("SPARQL query cannot be empty.")

    endpoint = _resolve_endpoint(repo_key)
    headers = {"Accept": "application/sparql-results+json"}
    auth = None
    if settings.graphdb_username and settings.graphdb_password:
        auth = (settings.graphdb_username, settings.graphdb_password)

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                endpoint,
                data={"query": query},
                headers=headers,
                auth=auth,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise SparqlQueryError(f"SPARQL query failed: {exc}") from exc
    except ValueError as exc:
        raise SparqlQueryError("Failed to decode SPARQL response as JSON.") from exc

    if "boolean" in data:
        return bool(data["boolean"])

    head = data.get("head", {})
    result_section = data.get("results", {})
    variables = head.get("vars", [])
    bindings = result_section.get("bindings", [])

    rows: List[Dict[str, Any]] = []
    for binding in bindings:
        row = {}
        for var in variables:
            cell = binding.get(var)
            if cell is not None:
                row[var] = cell.get("value")
        rows.append(row)

    return rows

