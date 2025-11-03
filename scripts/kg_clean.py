#!/usr/bin/env python3
"""
Utility script to clear all statements from a GraphDB repository.

Usage:
    python scripts/kg_clean.py <repository_id> [--graphdb-url URL]

Environment variables (optional):
    GRAPHDB_URL         Base GraphDB URL (default: http://localhost:7200)
    GRAPHDB_USERNAME    Basic auth username
    GRAPHDB_PASSWORD    Basic auth password
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clear a GraphDB repository.")
    parser.add_argument(
        "repository",
        help="Repository identifier (e.g. unified, hearing, grape_unified)",
    )
    parser.add_argument(
        "--graphdb-url",
        default=os.environ.get("GRAPHDB_URL", "http://localhost:7200"),
        help="Base GraphDB URL (default: %(default)s or GRAPHDB_URL env)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default: 30.0)",
    )
    return parser.parse_args()


def resolve_repository_id(repo: str) -> str:
    if repo.startswith("grape_"):
        repo = repo.replace("grape_", "", 1)
    return repo


def main() -> int:
    args = parse_args()
    repo_id = resolve_repository_id(args.repository)

    username = os.environ.get("GRAPHDB_USERNAME")
    password = os.environ.get("GRAPHDB_PASSWORD")
    auth = (username, password) if username and password else None

    endpoint = f"{args.graphdb_url.rstrip('/')}/repositories/{repo_id}/statements"

    print(f"[INFO] Clearing repository '{repo_id}' at {endpoint}")
    try:
        with httpx.Client(timeout=args.timeout) as client:
            response = client.delete(endpoint, auth=auth)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(f"[ERROR] GraphDB returned HTTP {exc.response.status_code}: {exc.response.text}")
        return 1
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[ERROR] Failed to clear repository: {exc}")
        return 1

    print("[OK] Repository cleared successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
