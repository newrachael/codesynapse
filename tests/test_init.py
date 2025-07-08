import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from codesynapse import generate_graph, GraphBuilder


class TestGenerateGraph:
    """generate_graph 함수 테스트"""
    
    @patch('codesynapse.visualize_graph')
    @patch('codesynapse.GraphBuilder')
    def test_generate_graph_basic(self, mock_builder_class, mock_visualize, temp_project_dir):
        """기본적인 generate_graph 함수 테스트"""
        # Mock 설정
        mock_builder = Mock()
        mock_graph = Mock()
        mock_graph.number_of_nodes.return_value = 10
        mock_graph.number_of_edges.return_value = 15
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder
        
        # 함수 호출
        generate_graph(str(temp_project_dir), "test_output.html")
        
        # GraphBuilder가 올바른 경로로 호출되었는지 확인
        mock_builder_class.assert_called_once_with(str(temp_project_dir))
        
        # build 메서드가 호출되었는지 확인
        mock_builder.build.assert_called_once()
        
        # visualize_graph가 올바른 매개변수로 호출되었는지 확인
        mock_visualize.assert_called_once_with(mock_graph, "test_output.html")
    
    @patch('codesynapse.visualize_graph')
    @patch('codesynapse.GraphBuilder')
    def test_generate_graph_default_filename(self, mock_builder_class, mock_visualize, temp_project_dir):
        """기본 파일명 사용 테스트"""
        # Mock 설정
        mock_builder = Mock()
        mock_graph = Mock()
        mock_graph.number_of_nodes.return_value = 5
        mock_graph.number_of_edges.return_value = 8
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder
        
        # 파일명을 지정하지 않고 호출
        generate_graph(str(temp_project_dir))
        
        # visualize_graph가 기본 파일명으로 호출되었는지 확인
        mock_visualize.assert_called_once_with(mock_graph, "codesynapse_graph.html")
    
    @patch('builtins.print')
    @patch('codesynapse.visualize_graph')
    @patch('codesynapse.GraphBuilder')
    def test_generate_graph_prints_messages(self, mock_builder_class, mock_visualize, mock_print, temp_project_dir):
        """메시지 출력 테스트"""
        # Mock 설정
        mock_builder = Mock()
        mock_graph = Mock()
        mock_graph.number_of_nodes.return_value = 20
        mock_graph.number_of_edges.return_value = 35
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder
        
        project_path = str(temp_project_dir)
        generate_graph(project_path, "test_messages.html")
        
        # 시작 메시지가 출력되었는지 확인
        expected_start_message = f"Starting analysis of project at: {project_path}"
        mock_print.assert_any_call(expected_start_message)
        
        # 결과 메시지가 출력되었는지 확인
        expected_result_message = "Found 20 nodes and 35 edges."
        mock_print.assert_any_call(expected_result_message)
    
    def test_generate_graph_integration(self, temp_project_dir):
        """실제 통합 테스트"""
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "integration_test.html"
            
            # 실제 함수 호출
            generate_graph(str(temp_project_dir), str(output_path))
            
            # 출력 파일이 생성되었는지 확인
            assert output_path.exists()
            assert output_path.is_file()
            assert output_path.stat().st_size > 0
    
    @patch('codesynapse.visualize_graph')
    @patch('codesynapse.GraphBuilder')
    def test_generate_graph_with_empty_graph(self, mock_builder_class, mock_visualize, temp_project_dir):
        """빈 그래프 처리 테스트"""
        # Mock 설정 - 빈 그래프
        mock_builder = Mock()
        mock_graph = Mock()
        mock_graph.number_of_nodes.return_value = 0
        mock_graph.number_of_edges.return_value = 0
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder
        
        # 함수 호출 (예외가 발생하지 않아야 함)
        generate_graph(str(temp_project_dir), "empty_test.html")
        
        # 모든 단계가 정상적으로 호출되어야 함
        mock_builder_class.assert_called_once()
        mock_builder.build.assert_called_once()
        mock_visualize.assert_called_once()
    
    @patch('codesynapse.visualize_graph')
    @patch('codesynapse.GraphBuilder')
    def test_generate_graph_builder_exception(self, mock_builder_class, mock_visualize, temp_project_dir):
        """GraphBuilder에서 예외 발생 시 처리 테스트"""
        # Mock 설정 - 빌더에서 예외 발생
        mock_builder = Mock()
        mock_builder.build.side_effect = Exception("Build failed")
        mock_builder_class.return_value = mock_builder
        
        # 예외가 발생해야 함
        with pytest.raises(Exception, match="Build failed"):
            generate_graph(str(temp_project_dir), "error_test.html")
        
        # GraphBuilder는 호출되었지만 visualize_graph는 호출되지 않아야 함
        mock_builder_class.assert_called_once()
        mock_builder.build.assert_called_once()
        mock_visualize.assert_not_called()
    
    @patch('codesynapse.visualize_graph')
    @patch('codesynapse.GraphBuilder')
    def test_generate_graph_visualizer_exception(self, mock_builder_class, mock_visualize, temp_project_dir):
        """시각화에서 예외 발생 시 처리 테스트"""
        # Mock 설정
        mock_builder = Mock()
        mock_graph = Mock()
        mock_graph.number_of_nodes.return_value = 5
        mock_graph.number_of_edges.return_value = 3
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder
        
        # 시각화에서 예외 발생
        mock_visualize.side_effect = Exception("Visualization failed")
        
        # 예외가 발생해야 함
        with pytest.raises(Exception, match="Visualization failed"):
            generate_graph(str(temp_project_dir), "viz_error_test.html")
        
        # 모든 단계가 호출되었지만 마지막에 실패
        mock_builder_class.assert_called_once()
        mock_builder.build.assert_called_once()
        mock_visualize.assert_called_once()
    
    def test_generate_graph_with_pathlib_path(self, temp_project_dir):
        """Path 객체로 경로 전달 테스트"""
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "pathlib_test.html"
            
            # Path 객체로 호출
            generate_graph(temp_project_dir, str(output_path))
            
            # 정상적으로 파일이 생성되어야 함
            assert output_path.exists()
    
    @patch('codesynapse.visualize_graph')
    @patch('codesynapse.GraphBuilder')
    def test_generate_graph_parameter_types(self, mock_builder_class, mock_visualize, temp_project_dir):
        """매개변수 타입 처리 테스트"""
        # Mock 설정
        mock_builder = Mock()
        mock_graph = Mock()
        mock_graph.number_of_nodes.return_value = 1
        mock_graph.number_of_edges.return_value = 1
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder
        
        # 다양한 타입의 매개변수로 테스트
        test_cases = [
            (str(temp_project_dir), "string_path.html"),
            (temp_project_dir, "path_object.html"),  # Path 객체
        ]
        
        for project_path, output_file in test_cases:
            mock_builder_class.reset_mock()
            mock_visualize.reset_mock()
            
            generate_graph(project_path, output_file)
            
            # 모든 경우에 정상적으로 호출되어야 함
            mock_builder_class.assert_called_once()
            mock_visualize.assert_called_once()
    
    def test_generate_graph_real_project_structure(self, temp_project_dir):
        """실제 프로젝트 구조로 전체 프로세스 테스트"""
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "real_structure_test.html"
            
            # 실제 함수 호출
            generate_graph(str(temp_project_dir), str(output_path))
            
            # 파일이 존재하고 내용이 있는지 확인
            assert output_path.exists()
            content = output_path.read_text()
            
            # HTML 파일의 기본 구조 확인
            assert "<html" in content.lower()
            assert "</html>" in content.lower()
            
            # pyvis 관련 내용이 있는지 확인
            assert "vis-network" in content or "vis.js" in content.lower()
    
    @patch('builtins.print')
    def test_generate_graph_output_messages_content(self, mock_print, temp_project_dir):
        """출력 메시지 내용의 정확성 테스트"""
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "message_test.html"
            
            generate_graph(str(temp_project_dir), str(output_path))
            
            # print 호출 내용 확인
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            
            # 시작 메시지 확인
            start_messages = [msg for msg in print_calls if "Starting analysis" in msg]
            assert len(start_messages) == 1
            assert str(temp_project_dir) in start_messages[0]
            
            # 결과 메시지 확인
            result_messages = [msg for msg in print_calls if "Found" in msg and "nodes" in msg and "edges" in msg]
            assert len(result_messages) == 1
            
            # 완료 메시지 확인 (visualizer에서 출력)
            completion_messages = [msg for msg in print_calls if "Graph has been generated" in msg]
            assert len(completion_messages) == 1
            assert str(output_path) in completion_messages[0] 