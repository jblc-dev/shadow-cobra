import json
import networkx as nx

from cobra.paths import DATA_DIR

DATA_FILE = DATA_DIR / "musicmap-graph.json"
CLEANED_DATA_FILE = DATA_DIR / "musicmap-graph-cleaned.json"


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

        with open(CLEANED_DATA_FILE, 'r', encoding="utf-8") as f:
            cleaned_data = json.load(f)

        self.clean_G = nx.Graph()
        for node in cleaned_data["nodes"]:
            self.clean_G.add_node(
                node["id"],
                genres=node.get("genres", []),
                supergenre_genres=node.get("supergenre_genres", []),
                filter_genres=node.get("filter_genres", []),
            )

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

    def get_genres(self):
        if not self.genre or self.genre not in self.clean_G:
            return []
        return list(self.clean_G.nodes[self.genre].get("filter_genres", []))

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
