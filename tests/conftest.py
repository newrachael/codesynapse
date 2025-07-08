import pytest
import tempfile
from pathlib import Path
import textwrap

@pytest.fixture
def temp_project_dir():
    """테스트용 임시 프로젝트 디렉토리를 생성합니다."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # 테스트용 파이썬 파일들 생성
        # main.py - 메인 모듈
        main_py = project_path / "main.py"
        main_py.write_text(textwrap.dedent("""
            from utils import helper_function
            from models.user import User
            
            def main():
                user = User("test")
                result = helper_function()
                return result
            
            if __name__ == "__main__":
                main()
        """).strip())
        
        # utils.py - 유틸리티 모듈
        utils_py = project_path / "utils.py"
        utils_py.write_text(textwrap.dedent("""
            import os
            
            def helper_function():
                return "helper result"
            
            class UtilClass:
                def __init__(self):
                    self.value = 42
                
                def get_value(self):
                    return self.value
        """).strip())
        
        # models/ 패키지
        models_dir = project_path / "models"
        models_dir.mkdir()
        (models_dir / "__init__.py").write_text("")
        
        # models/user.py
        user_py = models_dir / "user.py"
        user_py.write_text(textwrap.dedent("""
            from .base import BaseModel
            
            class User(BaseModel):
                def __init__(self, name):
                    super().__init__()
                    self.name = name
                
                def get_name(self):
                    return self.name
        """).strip())
        
        # models/base.py
        base_py = models_dir / "base.py"
        base_py.write_text(textwrap.dedent("""
            class BaseModel:
                def __init__(self):
                    self.id = None
                
                def save(self):
                    pass
        """).strip())
        
        yield project_path

@pytest.fixture
def sample_graph():
    """테스트용 샘플 networkx 그래프를 생성합니다."""
    import networkx as nx
    from codesynapse.rules import NodeType, EdgeType
    
    graph = nx.DiGraph()
    
    # 노드 추가
    graph.add_node("main", type=NodeType.MODULE)
    graph.add_node("main.main", type=NodeType.FUNCTION)
    graph.add_node("utils", type=NodeType.MODULE)
    graph.add_node("utils.helper_function", type=NodeType.FUNCTION)
    graph.add_node("utils.UtilClass", type=NodeType.CLASS)
    
    # 엣지 추가
    graph.add_edge("main", "main.main", type=EdgeType.CONTAINS)
    graph.add_edge("main", "utils.helper_function", type=EdgeType.IMPORTS)
    graph.add_edge("utils", "utils.helper_function", type=EdgeType.CONTAINS)
    graph.add_edge("utils", "utils.UtilClass", type=EdgeType.CONTAINS)
    
    return graph 