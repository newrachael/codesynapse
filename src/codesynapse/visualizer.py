# src/codesynapse/visualizer.py

from pyvis.network import Network
from .rules import VISUAL_RULES, NodeType, EdgeType

def visualize_graph(graph, output_filename="codesynapse_graph.html"):
    """networkx 그래프를 pyvis를 사용해 HTML 파일로 시각화합니다."""
    net = Network(height="100vh", width="100%", directed=True, notebook=False)
    
    # 레이아웃 설정
    if VISUAL_RULES["layout"]["hierarchical"]:
        net.hrepulsion(node_distance=300, central_gravity=0.5)

    for node, attrs in graph.nodes(data=True):
        node_type = attrs.get("type", NodeType.FUNCTION) # 기본값 설정
        style = VISUAL_RULES["node_styles"].get(node_type, {})
        
        # 노드 이름에서 마지막 부분만 라벨로 사용
        label = node.split('.')[-1]
        
        net.add_node(
            node,
            label=label,
            title=node, # 마우스 오버 시 전체 경로 표시
            shape=style.get("shape", "circle"),
            color=style.get("color", "#CCCCCC"),
            size=style.get("size", 10),
        )

    for source, target, attrs in graph.edges(data=True):
        edge_type = attrs.get("type", EdgeType.CALLS)
        style = VISUAL_RULES["edge_styles"].get(edge_type, {})

        net.add_edge(
            source,
            target,
            color=style.get("color", "#888888"),
            dashes=(style.get("style") == "dashed"),
            arrows=style.get("arrowhead", "to"),
        )
        
    net.show(output_filename, notebook=False)
    print(f"Graph has been generated: {output_filename}")