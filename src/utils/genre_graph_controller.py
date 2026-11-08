from pathlib import Path
import json
import networkx as nx

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "musicmap-graph.json"


class GraphController:

    def __init__(
        self,
        start: str = "CHICAGO HOUSE & GARAGE HOUSE"
    ):  

        with open(DATA_FILE, 'r', encoding="utf-8") as f:
            graph_data = json.load(f)

        self.G = nx.Graph()

        for node in graph_data["nodes"]:
            attributes = {
                "label": node.get("label",""),
                "genre": node.get("supergenre",""),
                "year": node.get("year","")
                }
            self.G.add_node(node["id"],**attributes)


        for edge in graph_data["edges"]:
            self.G.add_edge(edge['source'], edge['target'])
        
        self.start=self._resolve_label(start)

    def _resolve_label(self,label):
        
        if label is None:
            return None

        if label in self.G:
            return label

        needle = str(label).strip().lower()
        for node_id, data in self.G.nodes(data=True):
            if str(data.get("label", "")).strip().lower() == needle:
                return node_id
            
   
        return None

    def _resolve_id(self,id):
        return self.G[id].get("label")
        

    def set_start(self, start: str):
        self.start = self._resolve_label(start)

    def walk_to_node(self, target_):
        if not target_ or self.start is None:
            return

        try:
            target=self._resolve_label(target_)
            path = nx.shortest_path(self.G, source=self.start, target=target)
        except nx.NodeNotFound as exc:
            print(f"Unknown node: {exc}")
            return
        except nx.NetworkXNoPath:
            print(f"No path exists between '{self._resolve_id(self.start)}' and '{self._resolve_id(target)}'.")
            return

        print(f"Path from '{self._resolve_id(self.start)}' to '{self._resolve_id(target)}':")
       
        print(" -> ".join(path))
