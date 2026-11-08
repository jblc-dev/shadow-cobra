from pathlib import Path
import json
import re
import networkx as nx

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "musicmap-graph.json"


class GraphController:

    def __init__(
        self,
        genre: str = "CHICAGO HOUSE & GARAGE HOUSE"
    ):

        with open(DATA_FILE, 'r', encoding="utf-8") as f:
            graph_data = json.load(f)

        self.G = nx.Graph()

        for node in graph_data["nodes"]:
            attributes = {
                "genre": node.get("label", ""),
                "supergenre": node.get("supergenre", ""),
                "year": node.get("year", "")
            }
            self.G.add_node(node["id"], **attributes)

        for edge in graph_data["edges"]:
            self.G.add_edge(edge['source'], edge['target'])

        self.genre = self._resolve_genre(genre)
        self.path = []
        self.genres = []

    def _resolve_genre(self, genre):
        if genre is None:
            return None

        if genre in self.G:
            return genre

        needle = str(genre).strip().lower()
        for node_id, data in self.G.nodes(data=True):
            if str(data.get("genre", "")).strip().lower() == needle:
                return node_id

        return None

    def _resolve_id(self, id, super_=False):

        if super_:
            return self.G.nodes[id].get("supergenre")
        return self.G.nodes[id].get("genre")

    def get_genre(self):
        return self._resolve_id(self.genre) if self.genre else None

    def get_supergenre(self):
        if not self.genre:
            return None

        supergenre_id = self._resolve_id(self.genre, super_=True)
        if not supergenre_id:
            return None
        if supergenre_id in self.G:
            return self._resolve_id(supergenre_id)
        return supergenre_id

   
    def _clean_genre(value):
        value = str(value).strip().lower()
        value = re.sub(r"\([^)]*\)", " ", value)
        value = re.sub(r"[^a-z0-9]+", " ", value)
        value = re.sub(r"\bn\b", "and", value)
        value = re.sub(r"\s+", " ", value).strip()
        return re.sub(r"\s+(music|genre)$", "", value)

    def _genre_terms(self, label):
        terms = []
        if not label:
            return terms

        without_parens = re.sub(r"\([^)]*\)", " ", label)
        for candidate in [without_parens] + re.split(r"[&/]", without_parens):
            term = self._clean_genre(candidate)
            if term and term not in terms:
                terms.append(term)
        return terms

    def get_genres(self):
        genres = []
        for label in (self.get_genre(), self.get_supergenre()):
            for term in self._genre_terms(label):
                if term not in genres:
                    genres.append(term)
        return genres

    def set_genre(self, genre: str):
        self.genre = self._resolve_genre(genre)

    def walk_to_node(self, target_):
        if not target_ or self.genre is None:
            return

        target = self._resolve_genre(target_)
        if target is None:
            print(f"Unknown genre: '{target_}'")
            return

        try:
            path = nx.shortest_path(self.G, source=self.genre, target=target)
        except nx.NetworkXNoPath:
            print(f"No path exists between '{self._resolve_id(self.genre)}' and '{self._resolve_id(target)}'.")
            return

        print(f"Path from '{self._resolve_id(self.genre)}' to '{self._resolve_id(target)}':")
        print(" -> ".join(self._resolve_id(node_id) for node_id in path))

        self.genre = target
        self.path = path
