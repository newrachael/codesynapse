# src/codesynapse/builder.py

import networkx as nx
from .parser import CodeParser

class GraphBuilder:
    def __init__(self, project_path):
        self.project_path = project_path
        self.graph = nx.DiGraph()

    def build(self):
        """프로젝트를 분석하고 그래프를 생성합니다."""
        parser = CodeParser(self.project_path)
        nodes, edges = parser.parse_project()

        for node_id, attrs in nodes:
            self.graph.add_node(node_id, **attrs)

        for source, target, attrs in edges:
            # target 노드가 그래프에 없을 경우 외부 라이브러리로 간주하고 추가
            if not self.graph.has_node(target):
                from .rules import NodeType
                self.graph.add_node(target, type=NodeType.EXTERNAL_LIB)
                
            self.graph.add_edge(source, target, **attrs)
            
        return self.graph