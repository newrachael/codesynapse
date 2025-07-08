# src/codesynapse/rules.py

from enum import Enum

class NodeType(Enum):
    """그래프의 노드 타입 정의"""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    EXTERNAL_LIB = "external"

class EdgeType(Enum):
    """관계의 종류"""
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    CONTAINS = "contains"
    DEFINES = "defines"
    INSTANTIATES = "instantiates"

# 시각적 표현 규칙
VISUAL_RULES = {
    "node_styles": {
        NodeType.MODULE: {"shape": "box", "color": "#E3F2FD", "size": 30},
        NodeType.CLASS: {"shape": "ellipse", "color": "#F3E5F5", "size": 20},
        NodeType.FUNCTION: {"shape": "circle", "color": "#E8F5E9", "size": 15},
        NodeType.EXTERNAL_LIB: {"shape": "database", "color": "#FFF9C4", "size": 15},
    },
    "edge_styles": {
        EdgeType.CALLS: {"style": "solid", "color": "#1976D2"},
        EdgeType.INHERITS: {"style": "dashed", "color": "#7B1FA2", "arrowhead": "empty"},
        EdgeType.IMPORTS: {"style": "dotted", "color": "#388E3C"},
    },
    "layout": {
        "hierarchical": True,
        "direction": "LR",  # Left to Right
        "sort_method": "directed",
    }
}