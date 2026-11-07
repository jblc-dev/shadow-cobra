#!/usr/bin/env python3
"""
Extract the Musicmap genre graph from https://musicmap.info/ into JSON + GraphML.

The site is a static single-page app:
  * index.html contains the full inline SVG map. The genre *nodes* are
    <text data-code="..."> elements and the *edges* are <path> elements inside
    <g id="connection-lines">, grouped by relation type.
  * master-genrelist.json contains per-genre metadata (name, year, description,
    playlists) and the super-genre -> genre hierarchy.

Nothing on the site is an actual graph database; the graph is encoded visually
in the SVG. This script reconstructs it as machine-readable data.

Usage:
    python3 tools/fetch_musicmap_graph.py
    python3 tools/fetch_musicmap_graph.py --cache-dir /tmp/mm --out-dir data/musicmap
    python3 tools/fetch_musicmap_graph.py --offline --cache-dir /tmp/mm
    python3 tools/fetch_musicmap_graph.py --include-descriptions
    python3 tools/fetch_musicmap_graph.py --include-media

NOTE: musicmap.info content is copyright (c) Kwinten Crauwels, all rights
reserved. Use the extracted data for personal study/research only and ask the
author for permission before redistributing it.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from html.parser import HTMLParser

SITE = "https://musicmap.info"
INDEX_URL = f"{SITE}/"
MASTER_URL = f"{SITE}/master-genrelist.json"
UA = "Mozilla/5.0"

# Relation groups in the map's SVG, in the order shown in the legend.
CONNECTION_TYPES = {
    "primary": "primary influence/derivative",
    "secondary": "secondary influence/derivative",
    "backlash": "backlash/anti-influence",
}

# Codes used by the map for origin/context nodes that are not in
# master-genrelist.json. Labels are taken from the visible static map labels.
EXTERNAL_LABELS = {
    "folk": "FOLK MUSIC",
    "class": "CLASSICAL MUSIC",
    "util01": "UTILITY MUSIC",
    "util02": "UTILITY MUSIC",
    "util03": "UTILITY MUSIC",
    "util3": "UTILITY MUSIC",
    "static1": "TIN PAN ALLEY POP MUSIC",
    "static2": "JUG BANDS & SKIFFLE",
    "static3": "ELECTRONIC SOUND",
}


def _label_from_world_code(code: str) -> str:
    """Best-effort label for world-music origin nodes (worldA13, worldC08...)."""
    return f"WORLD ({code})"


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.parent = parent
        self.text = []


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = Node(tag, dict(attrs), self.stack[-1])
        self.stack[-1].children.append(n)
        self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        n = Node(tag, dict(attrs), self.stack[-1])
        self.stack[-1].children.append(n)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].text.append(data)


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def full_text(node) -> str:
    parts = []

    def rec(n):
        parts.append("".join(n.text))
        for c in n.children:
            rec(c)

    rec(node)
    return clean_label(" ".join(parts))


def clean_label(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def find_by_id(root, element_id):
    for n in walk(root):
        if n.attrs.get("id") == element_id:
            return n
    return None


def parse_xy(transform: str | None):
    if not transform:
        return None, None
    m = re.search(
        r"matrix\(\s*[-\d.eE]+\s+[-\d.eE]+\s+[-\d.eE]+\s+[-\d.eE]+\s+"
        r"([-\d.eE]+)\s+([-\d.eE]+)\s*\)",
        transform,
    )
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"translate\(\s*([-\d.eE]+)[ ,]+([-\d.eE]+)\s*\)", transform)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def code_from_tag(tag: str | None):
    if not tag:
        return None
    m = re.search(r"data-code\s*=\s*['\"]([^'\"]+)['\"]", tag)
    return html.unescape(m.group(1)) if m else None


def fetch(url: str, path: str, offline: bool) -> str:
    if offline:
        if not os.path.exists(path):
            sys.exit(f"offline mode: missing cached file {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Connection": "close",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except Exception as exc:  # noqa: BLE001 - fall back to system tools
        # Some TLS/anti-bot setups reset urllib connections; wget/curl often
        # work. Keep the script usable on such hosts.
        import shutil
        import subprocess
        import tempfile

        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        try:
            if shutil.which("wget"):
                subprocess.run(
                    ["wget", "-q", "--no-check-certificate", "-U", UA,
                     "-O", tmp.name, url],
                    check=True, timeout=120,
                )
            elif shutil.which("curl"):
                subprocess.run(
                    ["curl", "-fsSL", "--http1.1", "-A", UA,
                     "-o", tmp.name, url],
                    check=True, timeout=120,
                )
            else:
                raise exc
            with open(tmp.name, "rb") as fh:
                raw = fh.read()
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(raw)
    return raw.decode("utf-8", errors="replace")


def extract(html_text: str, master: dict, include_descriptions=False,
            include_media=False):
    parser = TreeParser()
    parser.feed(html_text)
    root = parser.root
    nodes = {}
    edge_markers = defaultdict(lambda: {"various_influences": False,
                                        "various_derivatives": False,
                                        "divisible_into_subgenres": False})

    def ensure_node(code, label=None, ntype="genre"):
        if code not in nodes:
            nodes[code] = {
                "id": code,
                "label": label or code,
                "type": ntype,
                "supergenre": None,
                "year": None,
                "x": None,
                "y": None,
                "members": [],
            }
        elif label and (nodes[code]["label"] == code or not nodes[code]["label"]):
            nodes[code]["label"] = label
        return nodes[code]

    # 1. Genre nodes from the inline SVG (positions + visible labels).
    for n in walk(root):
        if n.tag != "text":
            continue
        raw_codes = n.attrs.get("data-code")
        if not raw_codes:
            continue
        # One map label can carry two codes ("con05 dtp14").
        codes = [c for c in re.split(r"\s+", raw_codes) if c]
        label = full_text(n)
        x, y = parse_xy(n.attrs.get("transform"))
        for code in codes:
            node = ensure_node(code, label)
            if node["x"] is None and x is not None:
                node["x"], node["y"] = x, y

    # 2. Super-genre areas (nodes) from the SVG.
    for n in walk(root):
        classes = (n.attrs.get("class") or "").split()
        if n.tag == "g" and "supergenre-area" in classes and n.attrs.get("data-code"):
            code = n.attrs["data-code"]
            node = ensure_node(code, ntype="supergenre")
            node["type"] = "supergenre"

    # 3. Metadata + hierarchy from master-genrelist.json.
    for code, meta in master.items():
        is_super = bool(meta.get("supergenre"))
        node = ensure_node(code, ntype="supergenre" if is_super else "genre")
        node["type"] = "supergenre" if is_super else "genre"
        node["label"] = clean_label(meta.get("name", code)) or code
        if not is_super:
            node["year"] = meta.get("year")
            primary = code_from_tag(meta.get("supergenre-first-tag"))
            if primary:
                node["supergenre"] = primary
            secondary = []
            for tag in meta.get("supergenre-second-tag") or []:
                c = code_from_tag(tag)
                if c:
                    secondary.append(c)
            node["secondary_supergenres"] = secondary
            if include_media:
                node["playlist_youtube"] = meta.get("playlist-link")
                node["playlist_spotify"] = meta.get("spotify-playlist-link")
                node["songlist"] = meta.get("songlist", [])
            if include_descriptions:
                node["description"] = meta.get("description")

    # 4. Edges from #connection-lines.
    connection_lines = find_by_id(root, "connection-lines")
    if connection_lines is None:
        sys.exit("could not find #connection-lines in index.html")
    edges = []
    for group in connection_lines.children:
        rel = (group.attrs.get("class") or "").strip()
        for path in group.children:
            if path.tag != "path":
                continue
            pid = path.attrs.get("id")
            classes = (path.attrs.get("class") or "").split()
            d = path.attrs.get("d")
            if rel in CONNECTION_TYPES:
                # The two class tokens are the endpoint codes.
                if len(classes) < 2:
                    continue
                src, dst = classes[0], classes[1]
                for code in (src, dst):
                    if code not in nodes:
                        label = EXTERNAL_LABELS.get(code)
                        if not label and code.startswith("world"):
                            label = _label_from_world_code(code)
                        ensure_node(code, label, ntype="external")
                edges.append({
                    "id": pid,
                    "source": src,
                    "target": dst,
                    "type": rel,
                    "label": CONNECTION_TYPES[rel],
                    "path_d": d,
                })
            elif rel in ("various-influences", "various-derivatives", "subgenres"):
                code = classes[0] if classes else None
                if not code:
                    continue
                if code not in nodes:
                    label = EXTERNAL_LABELS.get(code)
                    if not label and code.startswith("world"):
                        label = _label_from_world_code(code)
                    ensure_node(code, label, ntype="external")
                key = {
                    "various-influences": "various_influences",
                    "various-derivatives": "various_derivatives",
                    "subgenres": "divisible_into_subgenres",
                }[rel]
                edge_markers[code][key] = True

    # 5. Super-genre membership. master-genrelist's genrelist is authoritative;
    #    fall back to each genre's first supergenre tag.
    hierarchy_edges = []
    for code, meta in master.items():
        if not meta.get("supergenre"):
            continue
        for item in meta.get("genrelist", []):
            member = code_from_tag(item)
            if member:
                ensure_node(member)
                nodes[code]["members"].append(member)
                hierarchy_edges.append({
                    "id": f"{code}-{member}",
                    "source": code,
                    "target": member,
                    "type": "supergenre_member",
                    "label": "super-genre contains genre",
                    "path_d": None,
                })
    seen = {(e["source"], e["target"]) for e in hierarchy_edges}
    for code, node in nodes.items():
        parent = node.get("supergenre")
        if parent and (parent, code) not in seen and parent in nodes:
            nodes[parent]["members"].append(code)
            hierarchy_edges.append({
                "id": f"{parent}-{code}",
                "source": parent,
                "target": code,
                "type": "supergenre_member",
                "label": "super-genre contains genre",
                "path_d": None,
            })
            seen.add((parent, code))

    # Context/origin nodes that appear in the SVG but not in master-genrelist.
    for code, node in nodes.items():
        if code in master:
            continue
        if code in EXTERNAL_LABELS or code.startswith("world"):
            node["type"] = "external"
            if not node.get("label") or node["label"] == code:
                node["label"] = EXTERNAL_LABELS.get(code) or _label_from_world_code(code)

    for code, markers in edge_markers.items():
        if code in nodes:
            nodes[code].update(markers)

    # Deduplicate member lists.
    for node in nodes.values():
        node["members"] = sorted(set(node["members"]))

    return nodes, edges, hierarchy_edges


def write_json(path, nodes, edges, hierarchy_edges, stats):
    payload = {
        "source": {
            "name": "Musicmap",
            "url": SITE,
            "genre_metadata": MASTER_URL,
            "graph_encoding": "inline SVG in index.html (#connection-lines)",
            "copyright": (
                "Musicmap content (c) Kwinten Crauwels, all rights reserved. "
                "Extracted for personal study/research; ask the author before "
                "redistributing."
            ),
        },
        "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "stats": stats,
        "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
        "edges": edges,
        "hierarchy_edges": hierarchy_edges,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_graphml(path, nodes, edges, hierarchy_edges):
    ns = "http://graphml.graphdrawing.org/xmlns"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}graphml")
    keys = [
        ("label", "node", "string"),
        ("type", "node", "string"),
        ("supergenre", "node", "string"),
        ("year", "node", "string"),
        ("x", "node", "double"),
        ("y", "node", "double"),
        ("relation", "edge", "string"),
    ]
    for kid, target, typ in keys:
        ET.SubElement(root, f"{{{ns}}}key", {
            "id": kid, "for": target, "attr.name": kid, "attr.type": typ,
        })
    graph = ET.SubElement(root, f"{{{ns}}}graph", {
        "id": "musicmap", "edgedefault": "directed",
    })

    def add_node(node, node_id, node_type, label, parent=None):
        el = ET.SubElement(graph, f"{{{ns}}}node", {"id": node_id})
        for kid, val in (("label", label), ("type", node_type),
                         ("supergenre", parent)):
            if val is not None:
                e = ET.SubElement(el, f"{{{ns}}}data", {"key": kid})
                e.text = str(val)
        if node and node.get("year") is not None:
            e = ET.SubElement(el, f"{{{ns}}}data", {"key": "year"})
            e.text = str(node["year"])
        if node and node.get("x") is not None:
            for kid, val in (("x", node["x"]), ("y", node["y"])):
                e = ET.SubElement(el, f"{{{ns}}}data", {"key": kid})
                e.text = str(val)

    for node in sorted(nodes.values(), key=lambda n: n["id"]):
        add_node(node, node["id"], node["type"], node["label"],
                 node.get("supergenre"))

    def add_edges(items):
        for edge in items:
            el = ET.SubElement(graph, f"{{{ns}}}edge", {
                "id": str(edge["id"]),
                "source": edge["source"],
                "target": edge["target"],
            })
            e = ET.SubElement(el, f"{{{ns}}}data", {"key": "relation"})
            e.text = edge["type"]

    add_edges(edges)
    add_edges(hierarchy_edges)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default=".cache/musicmap",
                    help="directory for downloaded index.html / master json")
    ap.add_argument("--out-dir", default="data/musicmap",
                    help="directory for generated graph files")
    ap.add_argument("--offline", action="store_true",
                    help="only use already-cached files")
    ap.add_argument("--include-descriptions", action="store_true",
                    help="include the long genre descriptions (copyrighted)")
    ap.add_argument("--include-media", action="store_true",
                    help="include per-genre song lists and playlist links")
    args = ap.parse_args()

    os.makedirs(args.cache_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)

    index_path = os.path.join(args.cache_dir, "index.html")
    master_path = os.path.join(args.cache_dir, "master-genrelist.json")

    print("fetching Musicmap data...", file=sys.stderr)
    index_html = fetch(INDEX_URL, index_path, args.offline)
    master_raw = fetch(MASTER_URL, master_path, args.offline)
    master = json.loads(master_raw)

    nodes, edges, hierarchy_edges = extract(
        index_html, master,
        include_descriptions=args.include_descriptions,
        include_media=args.include_media,
    )

    edge_counts = Counter(e["type"] for e in edges)
    node_counts = Counter(n["type"] for n in nodes.values())
    stats = {
        "nodes": len(nodes),
        "genres": node_counts.get("genre", 0),
        "supergenres": node_counts.get("supergenre", 0),
        "external_origin_nodes": node_counts.get("external", 0),
        "edges": len(edges),
        "edges_by_type": dict(edge_counts),
        "hierarchy_edges": len(hierarchy_edges),
        "various_influence_markers": sum(
            1 for n in nodes.values() if n.get("various_influences")
        ),
        "various_derivative_markers": sum(
            1 for n in nodes.values() if n.get("various_derivatives")
        ),
        "subgenre_markers": sum(
            1 for n in nodes.values() if n.get("divisible_into_subgenres")
        ),
    }

    graph_json = os.path.join(args.out_dir, "musicmap-graph.json")
    write_json(graph_json, nodes, edges, hierarchy_edges, stats)

    write_csv(
        os.path.join(args.out_dir, "nodes.csv"),
        sorted(nodes.values(), key=lambda n: n["id"]),
        ["id", "label", "type", "supergenre", "year", "x", "y"],
    )
    write_csv(
        os.path.join(args.out_dir, "edges.csv"),
        edges + hierarchy_edges,
        ["id", "source", "target", "type", "label"],
    )
    write_graphml(
        os.path.join(args.out_dir, "musicmap-graph.graphml"),
        nodes, edges, hierarchy_edges,
    )

    print(json.dumps(stats, indent=2))
    print(f"\nwritten to {args.out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
