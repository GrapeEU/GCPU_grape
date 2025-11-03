#!/usr/bin/env python3
"""
Load every Turtle/OWL/RDF file from a directory into a GraphDB repository.

Usage:
    python scripts/kg_load_dir.py <directory> <repository_id>
        [--graphdb-url URL] [--graph-base BASE]

Environment variables (optional):
    GRAPHDB_URL         Base GraphDB URL (default: http://localhost:7200)
    GRAPHDB_USERNAME    Basic auth username
    GRAPHDB_PASSWORD    Basic auth password
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Iterable

import httpx


SUPPORTED_EXTENSIONS = (".ttl", ".rdf", ".owl", ".nt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load RDF files into GraphDB.")
    parser.add_argument(
        "directory",
        help="Directory containing RDF files (e.g. kg_example/GCPU_demo)",
    )
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
        "--graph-base",
        default="http://example.org/demo/",
        help="Base IRI used to derive graph contexts (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds (default: 60.0)",
    )
    return parser.parse_args()


def resolve_repository_id(repo: str) -> str:
    if repo.startswith("grape_"):
        repo = repo.replace("grape_", "", 1)
    return repo


def iter_rdf_files(directory: Path) -> Iterable[Path]:
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def context_from_path(graph_base: str, file_path: Path) -> str:
    safe_name = "_".join(file_path.parts[-2:]) if len(file_path.parts) >= 2 else file_path.name
    return f"{graph_base.rstrip('/')}/{safe_name}"


def main() -> int:
    args = parse_args()
    repo_id = resolve_repository_id(args.repository)
    directory = Path(args.directory).expanduser().resolve()

    if not directory.exists() or not directory.is_dir():
        print(f"❌ Directory not found: {directory}")
        return 1

    files = list(iter_rdf_files(directory))
    if not files:
        print(f"[WARN] No RDF files found under {directory} (extensions: {SUPPORTED_EXTENSIONS})")
        return 0

    username = os.environ.get("GRAPHDB_USERNAME")
    password = os.environ.get("GRAPHDB_PASSWORD")
    auth = (username, password) if username and password else None

    endpoint_base = f"{args.graphdb_url.rstrip('/')}/repositories/{repo_id}/statements"

    print(f"[INFO] Loading {len(files)} file(s) into repository '{repo_id}' from {directory}")
    with httpx.Client(timeout=args.timeout) as client:
        for file_path in files:
            graph_uri = context_from_path(args.graph_base, file_path.relative_to(directory))
            endpoint = f"{endpoint_base}?context=<{graph_uri}>"

            print(f"  - {file_path.name} -> {graph_uri}")
            content_type = "application/trig" if file_path.suffix.lower() == ".owl" else "text/turtle"
            try:
                response = client.post(
                    endpoint,
                    headers={"Content-Type": content_type},
                    content=file_path.read_bytes(),
                    auth=auth,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                print(f"    [ERROR] HTTP {exc.response.status_code}: {exc.response.text}")
                return 1
            except Exception as exc:  # pragma: no cover - defensive
                print(f"    [ERROR] Failed to load {file_path}: {exc}")
                return 1

    print("[OK] All files loaded successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
