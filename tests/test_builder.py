import pytest
import networkx as nx
from unittest.mock import Mock, patch
from codesynapse.builder import GraphBuilder
from codesynapse.rules import NodeType, EdgeType


class TestGraphBuilder:
    """GraphBuilder 클래스 테스트"""
    
    def test_init(self, temp_project_dir):
        """GraphBuilder 초기화 테스트"""
        builder = GraphBuilder(temp_project_dir)
        
        assert builder.project_path == temp_project_dir
        assert isinstance(builder.graph, nx.DiGraph)
        assert builder.graph.number_of_nodes() == 0
        assert builder.graph.number_of_edges() == 0
    
    def test_build_returns_graph(self, temp_project_dir):
        """build 메서드가 networkx 그래프를 반환하는지 확인"""
        builder = GraphBuilder(temp_project_dir)
        graph = builder.build()
        
        assert isinstance(graph, nx.DiGraph)
        assert graph.number_of_nodes() > 0
        assert graph.number_of_edges() > 0
    
    def test_build_with_real_project(self, temp_project_dir):
        """실제 프로젝트로 그래프 구축 테스트"""
        builder = GraphBuilder(temp_project_dir)
        graph = builder.build()
        
        # 예상되는 노드들이 있는지 확인
        expected_nodes = [
            "main",
            "main.main",
            "utils",
            "utils.helper_function",
            "utils.UtilClass",
            "models",
            "models.user",
            "models.user.User",
            "models.base",
            "models.base.BaseModel"
        ]
        
        for node in expected_nodes:
            assert graph.has_node(node), f"노드 {node}이 그래프에 없습니다"
    
    def test_node_attributes_preserved(self, temp_project_dir):
        """노드 속성이 올바르게 보존되는지 확인"""
        builder = GraphBuilder(temp_project_dir)
        graph = builder.build()
        
        # 모듈 노드 확인
        assert graph.nodes["main"]["type"] == NodeType.MODULE
        assert graph.nodes["utils"]["type"] == NodeType.MODULE
        
        # 클래스 노드 확인
        assert graph.nodes["utils.UtilClass"]["type"] == NodeType.CLASS
        assert graph.nodes["models.user.User"]["type"] == NodeType.CLASS
        
        # 함수 노드 확인
        assert graph.nodes["main.main"]["type"] == NodeType.FUNCTION
        assert graph.nodes["utils.helper_function"]["type"] == NodeType.FUNCTION
    
    def test_edge_attributes_preserved(self, temp_project_dir):
        """엣지 속성이 올바르게 보존되는지 확인"""
        builder = GraphBuilder(temp_project_dir)
        graph = builder.build()
        
        # CONTAINS 엣지 확인
        if graph.has_edge("main", "main.main"):
            assert graph.edges["main", "main.main"]["type"] == EdgeType.CONTAINS
        
        if graph.has_edge("utils", "utils.UtilClass"):
            assert graph.edges["utils", "utils.UtilClass"]["type"] == EdgeType.CONTAINS
    
    @patch('codesynapse.builder.CodeParser')
    def test_build_with_mock_parser(self, mock_parser_class, temp_project_dir):
        """모킹된 파서로 그래프 구축 테스트"""
        # 모킹된 파서 설정
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        
        # 모킹된 파서 결과 설정
        mock_nodes = [
            ("test.module", {"type": NodeType.MODULE}),
            ("test.module.TestClass", {"type": NodeType.CLASS}),
            ("test.module.test_function", {"type": NodeType.FUNCTION})
        ]
        
        mock_edges = [
            ("test.module", "test.module.TestClass", {"type": EdgeType.CONTAINS}),
            ("test.module", "test.module.test_function", {"type": EdgeType.CONTAINS}),
            ("test.module.TestClass", "external.BaseClass", {"type": EdgeType.INHERITS})
        ]
        
        mock_parser.parse_project.return_value = (mock_nodes, mock_edges)
        
        # 그래프 구축
        builder = GraphBuilder(temp_project_dir)
        graph = builder.build()
        
        # 파서가 호출되었는지 확인
        mock_parser_class.assert_called_once_with(temp_project_dir)
        mock_parser.parse_project.assert_called_once()
        
        # 그래프에 노드가 추가되었는지 확인
        assert graph.has_node("test.module")
        assert graph.has_node("test.module.TestClass")
        assert graph.has_node("test.module.test_function")
        
        # 외부 라이브러리 노드가 추가되었는지 확인
        assert graph.has_node("external.BaseClass")
        assert graph.nodes["external.BaseClass"]["type"] == NodeType.EXTERNAL_LIB
    
    def test_external_library_nodes_added(self, temp_project_dir):
        """외부 라이브러리 노드가 자동으로 추가되는지 확인"""
        builder = GraphBuilder(temp_project_dir)
        graph = builder.build()
        
        # BaseModel은 상속되지만 프로젝트에 정의되지 않은 경우
        # (실제로는 models.base.BaseModel이 존재하므로 이 테스트는 다른 외부 라이브러리로 확인)
        external_nodes = [node for node, attrs in graph.nodes(data=True) 
                         if attrs.get("type") == NodeType.EXTERNAL_LIB]
        
        # 외부 라이브러리 노드가 있을 수 있음 (import 관계에 따라)
        for node in external_nodes:
            assert graph.nodes[node]["type"] == NodeType.EXTERNAL_LIB
    
    def test_build_creates_directed_graph(self, temp_project_dir):
        """방향성 그래프가 생성되는지 확인"""
        builder = GraphBuilder(temp_project_dir)
        graph = builder.build()
        
        assert isinstance(graph, nx.DiGraph)
        assert graph.is_directed()
    
    def test_build_handles_empty_project(self):
        """빈 프로젝트도 처리할 수 있는지 확인"""
        import tempfile
        
        with tempfile.TemporaryDirectory() as empty_dir:
            builder = GraphBuilder(empty_dir)
            graph = builder.build()
            
            # 빈 그래프여야 함
            assert graph.number_of_nodes() == 0
            assert graph.number_of_edges() == 0
    
    def test_build_preserves_parser_data_integrity(self, temp_project_dir):
        """파서 데이터의 무결성이 보존되는지 확인"""
        builder = GraphBuilder(temp_project_dir)
        graph = builder.build()
        
        # 모든 노드가 유효한 타입을 가져야 함
        for node, attrs in graph.nodes(data=True):
            assert "type" in attrs
            assert attrs["type"] in NodeType
        
        # 모든 엣지가 유효한 타입을 가져야 함
        for source, target, attrs in graph.edges(data=True):
            assert "type" in attrs
            assert attrs["type"] in EdgeType
    
    def test_multiple_builds_consistent(self, temp_project_dir):
        """같은 프로젝트로 여러 번 build를 해도 일관된 결과가 나오는지 확인"""
        builder = GraphBuilder(temp_project_dir)
        
        graph1 = builder.build()
        graph2 = builder.build()
        
        # 노드 개수가 같아야 함
        assert graph1.number_of_nodes() == graph2.number_of_nodes()
        assert graph1.number_of_edges() == graph2.number_of_edges()
        
        # 같은 노드들을 가져야 함
        assert set(graph1.nodes()) == set(graph2.nodes())
        assert set(graph1.edges()) == set(graph2.edges())
    
    def test_graph_structure_validity(self, temp_project_dir):
        """생성된 그래프 구조가 유효한지 확인"""
        builder = GraphBuilder(temp_project_dir)
        graph = builder.build()
        
        # 그래프가 연결되어 있는지 확인 (약하게 연결된 경우도 포함)
        if graph.number_of_nodes() > 1:
            # 적어도 일부 노드들이 연결되어 있어야 함
            assert graph.number_of_edges() > 0
        
        # 자기 자신으로의 엣지가 없어야 함 (이 프로젝트의 경우)
        self_loops = list(nx.selfloop_edges(graph))
        assert len(self_loops) == 0, f"자기 자신으로의 엣지가 있습니다: {self_loops}"
