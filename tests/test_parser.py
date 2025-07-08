import pytest
import ast
from pathlib import Path
from codesynapse.parser import CodeParser
from codesynapse.rules import NodeType, EdgeType


class TestCodeParser:
    """CodeParser 클래스 테스트"""
    
    def test_init(self, temp_project_dir):
        """CodeParser 초기화 테스트"""
        parser = CodeParser(temp_project_dir)
        
        assert parser.project_root == temp_project_dir.resolve()
        assert len(parser.nodes) == 0
        assert len(parser.edges) == 0
        assert parser.current_module is None
        assert parser.current_class is None
    
    def test_parse_project(self, temp_project_dir):
        """프로젝트 파싱 테스트"""
        parser = CodeParser(temp_project_dir)
        nodes, edges = parser.parse_project()
        
        # 노드가 생성되었는지 확인
        assert len(nodes) > 0
        assert len(edges) > 0
        
        # 노드 형식 확인
        for node_id, attrs in nodes:
            assert isinstance(node_id, str)
            assert "type" in attrs
            assert attrs["type"] in NodeType
        
        # 엣지 형식 확인
        for source, target, attrs in edges:
            assert isinstance(source, str)
            assert isinstance(target, str)
            assert "type" in attrs
            assert attrs["type"] in EdgeType
    
    def test_module_nodes_created(self, temp_project_dir):
        """모듈 노드가 올바르게 생성되는지 확인"""
        parser = CodeParser(temp_project_dir)
        nodes, edges = parser.parse_project()
        
        # 모듈 노드들 찾기
        module_nodes = [node for node, attrs in nodes if attrs["type"] == NodeType.MODULE]
        
        expected_modules = ["main", "utils", "models", "models.user", "models.base"]
        
        for expected_module in expected_modules:
            assert expected_module in module_nodes, f"모듈 {expected_module}이 발견되지 않았습니다"
    
    def test_class_nodes_created(self, temp_project_dir):
        """클래스 노드가 올바르게 생성되는지 확인"""
        parser = CodeParser(temp_project_dir)
        nodes, edges = parser.parse_project()
        
        # 클래스 노드들 찾기
        class_nodes = [node for node, attrs in nodes if attrs["type"] == NodeType.CLASS]
        
        expected_classes = ["utils.UtilClass", "models.user.User", "models.base.BaseModel"]
        
        for expected_class in expected_classes:
            assert expected_class in class_nodes, f"클래스 {expected_class}이 발견되지 않았습니다"
    
    def test_function_nodes_created(self, temp_project_dir):
        """함수 노드가 올바르게 생성되는지 확인"""
        parser = CodeParser(temp_project_dir)
        nodes, edges = parser.parse_project()
        
        # 함수 노드들 찾기
        function_nodes = [node for node, attrs in nodes if attrs["type"] == NodeType.FUNCTION]
        
        expected_functions = [
            "main.main",
            "utils.helper_function",
            "utils.UtilClass.__init__",
            "utils.UtilClass.get_value",
            "models.user.User.__init__",
            "models.user.User.get_name",
            "models.base.BaseModel.__init__",
            "models.base.BaseModel.save"
        ]
        
        for expected_function in expected_functions:
            assert expected_function in function_nodes, f"함수 {expected_function}이 발견되지 않았습니다"
    
    def test_contains_edges(self, temp_project_dir):
        """CONTAINS 엣지가 올바르게 생성되는지 확인"""
        parser = CodeParser(temp_project_dir)
        nodes, edges = parser.parse_project()
        
        # CONTAINS 엣지들 찾기
        contains_edges = [(source, target) for source, target, attrs in edges 
                         if attrs["type"] == EdgeType.CONTAINS]
        
        # 모듈이 함수를 포함하는 관계
        assert ("main", "main.main") in contains_edges
        assert ("utils", "utils.helper_function") in contains_edges
        assert ("utils", "utils.UtilClass") in contains_edges
        
        # 모듈이 클래스를 포함하는 관계
        assert ("models.user", "models.user.User") in contains_edges
        assert ("models.base", "models.base.BaseModel") in contains_edges
    
    def test_inheritance_edges(self, temp_project_dir):
        """상속 관계 엣지가 올바르게 생성되는지 확인"""
        parser = CodeParser(temp_project_dir)
        nodes, edges = parser.parse_project()
        
        # INHERITS 엣지들 찾기
        inherits_edges = [(source, target) for source, target, attrs in edges 
                         if attrs["type"] == EdgeType.INHERITS]
        
        # User 클래스가 BaseModel을 상속하는 관계
        assert ("models.user.User", "BaseModel") in inherits_edges
    
    def test_visit_classdef(self, temp_project_dir):
        """visit_ClassDef 메서드 테스트"""
        parser = CodeParser(temp_project_dir)
        parser.current_module = "test_module"
        
        # 테스트용 AST 노드 생성
        class_node = ast.ClassDef(
            name="TestClass",
            bases=[ast.Name(id="BaseClass", ctx=ast.Load())],
            keywords=[],
            decorator_list=[],
            body=[]
        )
        
        parser.visit_ClassDef(class_node)
        
        # 클래스 노드가 추가되었는지 확인
        class_nodes = [node for node, attrs in parser.nodes if attrs["type"] == NodeType.CLASS]
        assert "test_module.TestClass" in class_nodes
        
        # 상속 관계가 추가되었는지 확인
        inherits_edges = [(source, target) for source, target, attrs in parser.edges 
                         if attrs["type"] == EdgeType.INHERITS]
        assert ("test_module.TestClass", "BaseClass") in inherits_edges
    
    def test_visit_functiondef(self, temp_project_dir):
        """visit_FunctionDef 메서드 테스트"""
        parser = CodeParser(temp_project_dir)
        parser.current_module = "test_module"
        
        # 모듈 레벨 함수 테스트
        func_node = ast.FunctionDef(
            name="test_function",
            args=ast.arguments(
                posonlyargs=[], args=[], vararg=None, kwonlyargs=[],
                kw_defaults=[], kwarg=None, defaults=[]
            ),
            body=[],
            decorator_list=[],
            returns=None
        )
        
        parser.visit_FunctionDef(func_node)
        
        # 함수 노드가 추가되었는지 확인
        function_nodes = [node for node, attrs in parser.nodes if attrs["type"] == NodeType.FUNCTION]
        assert "test_module.test_function" in function_nodes
        
        # CONTAINS 엣지가 추가되었는지 확인
        contains_edges = [(source, target) for source, target, attrs in parser.edges 
                         if attrs["type"] == EdgeType.CONTAINS]
        assert ("test_module", "test_module.test_function") in contains_edges
    
    def test_visit_functiondef_in_class(self, temp_project_dir):
        """클래스 내부 함수 처리 테스트"""
        parser = CodeParser(temp_project_dir)
        parser.current_module = "test_module"
        parser.current_class = "test_module.TestClass"
        
        func_node = ast.FunctionDef(
            name="test_method",
            args=ast.arguments(
                posonlyargs=[], args=[], vararg=None, kwonlyargs=[],
                kw_defaults=[], kwarg=None, defaults=[]
            ),
            body=[],
            decorator_list=[],
            returns=None
        )
        
        parser.visit_FunctionDef(func_node)
        
        # 메서드 노드가 추가되었는지 확인
        function_nodes = [node for node, attrs in parser.nodes if attrs["type"] == NodeType.FUNCTION]
        assert "test_module.TestClass.test_method" in function_nodes
        
        # DEFINES 엣지가 추가되었는지 확인
        defines_edges = [(source, target) for source, target, attrs in parser.edges 
                        if attrs["type"] == EdgeType.DEFINES]
        assert ("test_module.TestClass", "test_module.TestClass.test_method") in defines_edges
    
    def test_visit_importfrom(self, temp_project_dir):
        """visit_ImportFrom 메서드 테스트"""
        parser = CodeParser(temp_project_dir)
        parser.current_module = "test_module"
        
        # from package import function
        import_node = ast.ImportFrom(
            module="package",
            names=[ast.alias(name="function", asname=None)],
            level=0
        )
        
        parser.visit_ImportFrom(import_node)
        
        # IMPORTS 엣지가 추가되었는지 확인
        imports_edges = [(source, target) for source, target, attrs in parser.edges 
                        if attrs["type"] == EdgeType.IMPORTS]
        assert ("test_module", "package.function") in imports_edges
    
    def test_visit_importfrom_with_alias(self, temp_project_dir):
        """별칭을 가진 import 테스트"""
        parser = CodeParser(temp_project_dir)
        parser.current_module = "test_module"
        
        # from package import function as func
        import_node = ast.ImportFrom(
            module="package",
            names=[ast.alias(name="function", asname="func")],
            level=0
        )
        
        parser.visit_ImportFrom(import_node)
        
        # IMPORTS 엣지가 추가되었는지 확인 (별칭 사용)
        imports_edges = [(source, target) for source, target, attrs in parser.edges 
                        if attrs["type"] == EdgeType.IMPORTS]
        assert ("test_module", "package.func") in imports_edges
    
    def test_error_handling(self, temp_project_dir):
        """구문 오류가 있는 파일 처리 테스트"""
        # 잘못된 구문의 파이썬 파일 생성
        invalid_py = temp_project_dir / "invalid.py"
        invalid_py.write_text("def incomplete_function(")
        
        parser = CodeParser(temp_project_dir)
        
        # 예외가 발생하지 않고 파싱이 계속되어야 함
        nodes, edges = parser.parse_project()
        
        # 다른 유효한 파일들은 여전히 파싱되어야 함
        assert len(nodes) > 0 