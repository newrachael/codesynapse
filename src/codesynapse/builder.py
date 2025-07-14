# src/codesynapse/builder.py
import networkx as nx
from pathlib import Path
from .parser import CodeParser
from .rules import NodeType


class GraphBuilder:
    def __init__(self, project_path: str | Path, collect_signatures: bool = False):
        self.path = Path(project_path)
        self.graph = nx.DiGraph()
        self.collect_signatures = collect_signatures

    def build(self):
        parser = CodeParser(self.path, collect_signatures=self.collect_signatures)
        nodes, edges = parser.parse_project()

        for nid, attrs in nodes:
            self.graph.add_node(nid, **attrs)
        for s, t, attrs in edges:
            if not self.graph.has_node(t):
                self.graph.add_node(t, type=NodeType.EXTERNAL_LIB)
            self.graph.add_edge(s, t, **attrs)

        # Add importance values based on call count
        for nid, attrs in self.graph.nodes(data=True):
            attrs["importance"] = parser.call_counter.get(nid, 0)
            
        return self.graph