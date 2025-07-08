import pytest
from codesynapse.rules import NodeType, EdgeType, VISUAL_RULES


class TestNodeType:
    """NodeType 열거형 테스트"""
    
    def test_node_type_values(self):
        """NodeType의 모든 값이 올바른지 확인"""
        assert NodeType.MODULE.value == "module"
        assert NodeType.CLASS.value == "class"
        assert NodeType.FUNCTION.value == "function"
        assert NodeType.EXTERNAL_LIB.value == "external"
    
    def test_node_type_count(self):
        """NodeType에 예상한 개수의 항목이 있는지 확인"""
        assert len(NodeType) == 4
    
    def test_node_type_unique_values(self):
        """모든 NodeType 값이 고유한지 확인"""
        values = [node_type.value for node_type in NodeType]
        assert len(values) == len(set(values))


class TestEdgeType:
    """EdgeType 열거형 테스트"""
    
    def test_edge_type_values(self):
        """EdgeType의 모든 값이 올바른지 확인"""
        assert EdgeType.IMPORTS.value == "imports"
        assert EdgeType.CALLS.value == "calls"
        assert EdgeType.INHERITS.value == "inherits"
        assert EdgeType.CONTAINS.value == "contains"
        assert EdgeType.DEFINES.value == "defines"
        assert EdgeType.INSTANTIATES.value == "instantiates"
    
    def test_edge_type_count(self):
        """EdgeType에 예상한 개수의 항목이 있는지 확인"""
        assert len(EdgeType) == 6
    
    def test_edge_type_unique_values(self):
        """모든 EdgeType 값이 고유한지 확인"""
        values = [edge_type.value for edge_type in EdgeType]
        assert len(values) == len(set(values))


class TestVisualRules:
    """VISUAL_RULES 상수 테스트"""
    
    def test_visual_rules_structure(self):
        """VISUAL_RULES의 기본 구조가 올바른지 확인"""
        assert "node_styles" in VISUAL_RULES
        assert "edge_styles" in VISUAL_RULES
        assert "layout" in VISUAL_RULES
    
    def test_node_styles_completeness(self):
        """모든 NodeType에 대한 스타일이 정의되었는지 확인"""
        node_styles = VISUAL_RULES["node_styles"]
        
        for node_type in NodeType:
            assert node_type in node_styles, f"NodeType.{node_type.name}에 대한 스타일이 없습니다"
    
    def test_node_style_properties(self):
        """각 노드 스타일이 필요한 속성을 가지고 있는지 확인"""
        node_styles = VISUAL_RULES["node_styles"]
        required_properties = {"shape", "color", "size"}
        
        for node_type, style in node_styles.items():
            for prop in required_properties:
                assert prop in style, f"NodeType.{node_type.name}의 스타일에 {prop} 속성이 없습니다"
    
    def test_edge_styles_exist(self):
        """일부 EdgeType에 대한 스타일이 정의되었는지 확인"""
        edge_styles = VISUAL_RULES["edge_styles"]
        
        # 모든 EdgeType에 스타일이 있을 필요는 없지만, 일부는 있어야 함
        assert len(edge_styles) > 0
        
        # 정의된 스타일들이 유효한 EdgeType인지 확인
        for edge_type in edge_styles:
            assert edge_type in EdgeType
    
    def test_layout_configuration(self):
        """레이아웃 설정이 올바른지 확인"""
        layout = VISUAL_RULES["layout"]
        
        assert "hierarchical" in layout
        assert isinstance(layout["hierarchical"], bool)
        
        if "direction" in layout:
            assert layout["direction"] in ["UD", "DU", "LR", "RL"]
    
    def test_color_format(self):
        """색상 값이 올바른 형식인지 확인"""
        node_styles = VISUAL_RULES["node_styles"]
        
        for node_type, style in node_styles.items():
            color = style["color"]
            # 헥스 색상 코드 형식 확인
            assert color.startswith("#"), f"NodeType.{node_type.name}의 색상이 헥스 형식이 아닙니다"
            assert len(color) == 7, f"NodeType.{node_type.name}의 색상 길이가 올바르지 않습니다"
    
    def test_size_values(self):
        """크기 값이 양수인지 확인"""
        node_styles = VISUAL_RULES["node_styles"]
        
        for node_type, style in node_styles.items():
            size = style["size"]
            assert isinstance(size, (int, float)), f"NodeType.{node_type.name}의 크기가 숫자가 아닙니다"
            assert size > 0, f"NodeType.{node_type.name}의 크기가 양수가 아닙니다" 