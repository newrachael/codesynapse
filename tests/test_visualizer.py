import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from codesynapse.visualizer import visualize_graph
from codesynapse.rules import NodeType, EdgeType, VISUAL_RULES


class TestVisualizeGraph:
    """visualize_graph 함수 테스트"""
    
    @patch('codesynapse.visualizer.Network')
    def test_visualize_graph_basic(self, mock_network_class, sample_graph):
        """기본적인 그래프 시각화 테스트"""
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        visualize_graph(sample_graph, "test_output.html")
        
        # Network 클래스가 올바른 매개변수로 호출되었는지 확인
        mock_network_class.assert_called_once_with(
            height="100vh", 
            width="100%", 
            directed=True, 
            notebook=False
        )
        
        # show 메서드가 호출되었는지 확인
        mock_net.show.assert_called_once_with("test_output.html", notebook=False)
    
    @patch('codesynapse.visualizer.Network')
    def test_visualize_graph_nodes_added(self, mock_network_class, sample_graph):
        """노드가 올바르게 추가되는지 테스트"""
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        visualize_graph(sample_graph, "test_output.html")
        
        # add_node가 호출되었는지 확인
        assert mock_net.add_node.call_count == sample_graph.number_of_nodes()
        
        # 각 노드가 적절한 매개변수로 추가되었는지 확인
        added_nodes = [call[0][0] for call in mock_net.add_node.call_args_list]
        expected_nodes = list(sample_graph.nodes())
        
        for node in expected_nodes:
            assert node in added_nodes
    
    @patch('codesynapse.visualizer.Network')
    def test_visualize_graph_edges_added(self, mock_network_class, sample_graph):
        """엣지가 올바르게 추가되는지 테스트"""
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        visualize_graph(sample_graph, "test_output.html")
        
        # add_edge가 호출되었는지 확인
        assert mock_net.add_edge.call_count == sample_graph.number_of_edges()
        
        # 각 엣지가 적절한 매개변수로 추가되었는지 확인
        added_edges = [(call[0][0], call[0][1]) for call in mock_net.add_edge.call_args_list]
        expected_edges = list(sample_graph.edges())
        
        for edge in expected_edges:
            assert edge in added_edges
    
    @patch('codesynapse.visualizer.Network')
    def test_node_styling_applied(self, mock_network_class, sample_graph):
        """노드 스타일링이 올바르게 적용되는지 테스트"""
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        visualize_graph(sample_graph, "test_output.html")
        
        # 각 add_node 호출에서 스타일 매개변수 확인
        for call in mock_net.add_node.call_args_list:
            args, kwargs = call
            node_id = args[0]
            node_type = sample_graph.nodes[node_id].get("type", NodeType.FUNCTION)
            expected_style = VISUAL_RULES["node_styles"].get(node_type, {})
            
            # 필수 스타일 속성들이 있는지 확인
            assert "label" in kwargs
            assert "title" in kwargs
            assert "shape" in kwargs
            assert "color" in kwargs
            assert "size" in kwargs
            
            # 스타일이 VISUAL_RULES에 따라 설정되었는지 확인
            if expected_style:
                assert kwargs["shape"] == expected_style.get("shape", "circle")
                assert kwargs["color"] == expected_style.get("color", "#CCCCCC")
                assert kwargs["size"] == expected_style.get("size", 10)
    
    @patch('codesynapse.visualizer.Network')
    def test_edge_styling_applied(self, mock_network_class, sample_graph):
        """엣지 스타일링이 올바르게 적용되는지 테스트"""
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        visualize_graph(sample_graph, "test_output.html")
        
        # 각 add_edge 호출에서 스타일 매개변수 확인
        for call in mock_net.add_edge.call_args_list:
            args, kwargs = call
            source, target = args[0], args[1]
            edge_type = sample_graph.edges[source, target].get("type", EdgeType.CALLS)
            expected_style = VISUAL_RULES["edge_styles"].get(edge_type, {})
            
            # 기본 스타일 속성들이 있는지 확인
            assert "color" in kwargs
            assert "dashes" in kwargs
            assert "arrows" in kwargs
    
    @patch('codesynapse.visualizer.Network')
    def test_hierarchical_layout_configuration(self, mock_network_class, sample_graph):
        """계층적 레이아웃 설정이 적용되는지 테스트"""
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        visualize_graph(sample_graph, "test_output.html")
        
        # hrepulsion이 호출되었는지 확인 (hierarchical이 True인 경우)
        if VISUAL_RULES["layout"]["hierarchical"]:
            mock_net.hrepulsion.assert_called_once_with(
                node_distance=300, 
                central_gravity=0.5
            )
    
    @patch('codesynapse.visualizer.Network')
    def test_node_label_formatting(self, mock_network_class, sample_graph):
        """노드 라벨이 올바르게 포맷되는지 테스트"""
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        visualize_graph(sample_graph, "test_output.html")
        
        # 각 노드의 라벨과 타이틀 확인
        for call in mock_net.add_node.call_args_list:
            args, kwargs = call
            node_id = args[0]
            
            # 라벨은 마지막 부분만 사용해야 함
            expected_label = node_id.split('.')[-1]
            assert kwargs["label"] == expected_label
            
            # 타이틀은 전체 경로여야 함
            assert kwargs["title"] == node_id
    
    @patch('codesynapse.visualizer.Network')
    def test_default_filename(self, mock_network_class, sample_graph):
        """기본 파일명이 올바르게 사용되는지 테스트"""
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        # 파일명을 지정하지 않고 호출
        visualize_graph(sample_graph)
        
        # 기본 파일명으로 show가 호출되었는지 확인
        mock_net.show.assert_called_once_with("codesynapse_graph.html", notebook=False)
    
    @patch('codesynapse.visualizer.Network')
    def test_empty_graph_handling(self, mock_network_class):
        """빈 그래프도 처리할 수 있는지 테스트"""
        import networkx as nx
        
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        empty_graph = nx.DiGraph()
        
        # 예외가 발생하지 않아야 함
        visualize_graph(empty_graph, "empty_test.html")
        
        # Network 객체는 생성되어야 함
        mock_network_class.assert_called_once()
        mock_net.show.assert_called_once_with("empty_test.html", notebook=False)
        
        # 노드나 엣지는 추가되지 않아야 함
        mock_net.add_node.assert_not_called()
        mock_net.add_edge.assert_not_called()
    
    @patch('codesynapse.visualizer.Network')
    def test_missing_node_type_handling(self, mock_network_class):
        """노드 타입이 없는 경우의 처리 테스트"""
        import networkx as nx
        
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        # 타입이 없는 노드를 가진 그래프 생성
        graph = nx.DiGraph()
        graph.add_node("test_node", name="test")  # type 속성 없음
        
        # 예외가 발생하지 않아야 함
        visualize_graph(graph, "test_missing_type.html")
        
        # 기본 타입(FUNCTION)으로 처리되어야 함
        mock_net.add_node.assert_called_once()
        call_args = mock_net.add_node.call_args_list[0]
        args, kwargs = call_args
        
        # 기본 스타일이 적용되어야 함
        default_style = VISUAL_RULES["node_styles"][NodeType.FUNCTION]
        assert kwargs["shape"] == default_style["shape"]
        assert kwargs["color"] == default_style["color"]
        assert kwargs["size"] == default_style["size"]
    
    @patch('codesynapse.visualizer.Network')
    def test_missing_edge_type_handling(self, mock_network_class):
        """엣지 타입이 없는 경우의 처리 테스트"""
        import networkx as nx
        
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        # 타입이 없는 엣지를 가진 그래프 생성
        graph = nx.DiGraph()
        graph.add_node("node1", type=NodeType.MODULE)
        graph.add_node("node2", type=NodeType.FUNCTION)
        graph.add_edge("node1", "node2", weight=1)  # type 속성 없음
        
        # 예외가 발생하지 않아야 함
        visualize_graph(graph, "test_missing_edge_type.html")
        
        # 기본 타입(CALLS)으로 처리되어야 함
        mock_net.add_edge.assert_called_once()
        call_args = mock_net.add_edge.call_args_list[0]
        args, kwargs = call_args
        
        # 기본 스타일이 적용되어야 함
        default_style = VISUAL_RULES["edge_styles"].get(EdgeType.CALLS, {})
        if default_style:
            assert kwargs["color"] == default_style.get("color", "#888888")
    
    @patch('builtins.print')
    @patch('codesynapse.visualizer.Network')
    def test_completion_message_printed(self, mock_network_class, mock_print, sample_graph):
        """완료 메시지가 출력되는지 테스트"""
        mock_net = Mock()
        mock_network_class.return_value = mock_net
        
        output_file = "test_completion.html"
        visualize_graph(sample_graph, output_file)
        
        # 완료 메시지가 출력되었는지 확인
        mock_print.assert_called_with(f"Graph has been generated: {output_file}")
    
    def test_integration_with_real_output(self, sample_graph):
        """실제 파일 출력 통합 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "integration_test.html"
            
            # 실제로 파일을 생성해보기
            visualize_graph(sample_graph, str(output_path))
            
            # 파일이 생성되었는지 확인
            assert output_path.exists()
            assert output_path.is_file()
            
            # 파일 크기가 0보다 큰지 확인 (실제 내용이 있는지)
            assert output_path.stat().st_size > 0
            
            # HTML 파일의 기본 구조가 있는지 확인
            content = output_path.read_text()
            assert "<html" in content.lower()
            assert "</html>" in content.lower() 