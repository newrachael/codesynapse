# src/codesynapse/parser.py

import ast
from pathlib import Path

from .rules import NodeType, EdgeType

class CodeParser(ast.NodeVisitor):
    def __init__(self, project_root):
        self.project_root = Path(project_root).resolve()
        self.nodes = []
        self.edges = []
        self.current_module = None
        self.current_class = None

    def parse_project(self):
        """프로젝트 내 모든 파이썬 파일을 파싱합니다."""
        for py_file in self.project_root.rglob("*.py"):
            module_path_str = str(py_file.relative_to(self.project_root).with_suffix("")).replace("/", ".")
            
            # __init__.py 파일은 해당 패키지 이름으로 처리
            if module_path_str.endswith(".__init__"):
                module_path_str = module_path_str[:-9]  # ".__init__" 제거
            
            self.current_module = module_path_str
            
            # 모듈 노드 추가
            self.nodes.append((self.current_module, {"type": NodeType.MODULE}))
            
            with open(py_file, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=str(py_file))
                    self.visit(tree)
                except Exception as e:
                    print(f"Error parsing {py_file}: {e}")
        return self.nodes, self.edges

    def visit_ClassDef(self, node):
        class_name = f"{self.current_module}.{node.name}"
        self.nodes.append((class_name, {"type": NodeType.CLASS}))
        self.edges.append((self.current_module, class_name, {"type": EdgeType.CONTAINS}))
        
        # 상속 관계 처리
        for base in node.bases:
            if isinstance(base, ast.Name):
                # NOTE: 외부 라이브러리나 다른 모듈의 클래스 상속은 추가적인 분석이 필요
                self.edges.append((class_name, base.id, {"type": EdgeType.INHERITS}))
        
        self.current_class = class_name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        if self.current_class:
            func_name = f"{self.current_class}.{node.name}"
            parent_node = self.current_class
            edge_type = EdgeType.DEFINES
        else:
            func_name = f"{self.current_module}.{node.name}"
            parent_node = self.current_module
            edge_type = EdgeType.CONTAINS

        self.nodes.append((func_name, {"type": NodeType.FUNCTION}))
        self.edges.append((parent_node, func_name, {"type": edge_type}))
        
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module
        for name in node.names:
            self.edges.append((self.current_module, f"{module}.{name.asname or name.name}", {"type": EdgeType.IMPORTS}))

    def visit_Call(self, node):
        # NOTE: 호출 관계 분석은 정적 분석의 가장 복잡한 부분이며,
        # 이 예제는 단순한 이름 기반 호출만 처리합니다.
        # 실제로는 변수의 타입을 추적해야 정확한 분석이 가능합니다.
        pass