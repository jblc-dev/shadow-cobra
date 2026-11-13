#!/usr/bin/env python3
"""Build the cleaned Musicmap graph used for genre filtering.

The default ``musicmap-graph.json`` keeps the human-readable labels used for
display (for example "CHICAGO HOUSE & GARAGE HOUSE"). This script creates a
second graph that keeps the same node ids but adds normalized, filter-ready
genre terms for each node.

For every node it writes:

* ``genres``            - cleaned terms from the node's own label
* ``supergenre_genres`` - cleaned terms from its supergenre
* ``filter_genres``     - ``genres`` + ``supergenre_genres``, deduplicated

``GraphController`` can then display labels from the default graph and simply
look up ``filter_genres`` in this cleaned graph.

Usage:
    python3 tools/build_cleaned_graph.py
    python3 tools/build_cleaned_graph.py --input path/to/graph.json \
        --output path/to/graph-cleaned.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_INPUT = DATA_DIR / "musicmap-graph.json"
DEFAULT_OUTPUT = DATA_DIR / "musicmap-graph-cleaned.json"


def clean_genre(value: str) -> str:
    """Normalize a single genre label into a lowercase filter term."""
    value = str(value).strip().lower()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\bn\b", "and", value)
    value = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"\s+(music|genre)$", "", value)


def genre_terms(label: str | None) -> list[str]:
    """Expand one graph label into cleaned genre terms.

    The full label and each ``&`` / ``/`` component are included so compound
    labels keep their meaning:

        "CHICAGO HOUSE & GARAGE HOUSE"
        -> ["chicago house garage house", "chicago house", "garage house"]

    Notice that "garage" alone is intentionally not produced.
    """
    terms: list[str] = []
    if not label:
        return terms

    without_parens = re.sub(r"\([^)]*\)", " ", label)
    for candidate in [without_parens] + re.split(r"[&/]", without_parens):
        term = clean_genre(candidate)
        if term and term not in terms:
            terms.append(term)
    return terms


def dedupe(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def build_cleaned_graph(graph: dict) -> dict:
    nodes = graph.get("nodes", [])
    own_genres = {
        node["id"]: genre_terms(node.get("label"))
        for node in nodes
    }

    cleaned_nodes = []
    for node in nodes:
        supergenre_id = node.get("supergenre")
        supergenre_genres = own_genres.get(supergenre_id, []) if supergenre_id else []
        genres = own_genres[node["id"]]

        cleaned_nodes.append({
            "id": node["id"],
            "label": node.get("label"),
            "type": node.get("type"),
            "supergenre": supergenre_id,
            "year": node.get("year"),
            "members": node.get("members", []),
            "genres": genres,
            "supergenre_genres": supergenre_genres,
            "filter_genres": dedupe(genres + supergenre_genres),
        })

    return {
        "source": graph.get("source"),
        "based_on": "musicmap-graph.json",
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "stats": {
            "nodes": len(cleaned_nodes),
            "nodes_with_genres": sum(1 for node in cleaned_nodes if node["genres"]),
            "nodes_with_filter_genres": sum(
                1 for node in cleaned_nodes if node["filter_genres"]
            ),
        },
        "nodes": cleaned_nodes,
        "edges": [
            {
                "source": edge["source"],
                "target": edge["target"],
                "type": edge.get("type"),
            }
            for edge in graph.get("edges", [])
        ],
        "hierarchy_edges": [
            {
                "source": edge["source"],
                "target": edge["target"],
                "type": edge.get("type"),
            }
            for edge in graph.get("hierarchy_edges", [])
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        graph = json.load(f)

    cleaned = build_cleaned_graph(graph)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"wrote {args.output}")
    print(json.dumps(cleaned["stats"], indent=2))


if __name__ == "__main__":
    main()
