# src/codesynapse/parser.py

import ast
import os
import importlib.util
from pathlib import Path
from typing import Set, Dict, List, Tuple, Optional
import logging

from .rules import NodeType, EdgeType

logger = logging.getLogger(__name__)

class TypeHintAnalyzer(ast.NodeVisitor):
    """타입 힌트에서 사용되는 타입을 추출하는 헬퍼 클래스"""
    def __init__(self):
        self.types = set()
        
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.types.add(node.id)
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        # typing.List 같은 형태
        base = self._get_full_name(node)
        if base:
            self.types.add(base)
        self.generic_visit(node)
    
    def _get_full_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_full_name(node.value)
            if base:
                return f"{base}.{node.attr}"
        return None

class CallAnalyzer(ast.NodeVisitor):
    """함수/메서드 호출 및 인스턴스화를 분석하는 헬퍼 클래스"""
    def __init__(self, current_scope: str):
        self.current_scope = current_scope
        self.calls = []
        self.instantiations = []  # 클래스 인스턴스화 추적
        self.imported_names = {}  # 임포트된 이름과 원본 모듈 매핑
        
    def visit_Call(self, node):
        """함수 호출 및 클래스 인스턴스화 분석"""
        call_name = self._get_call_name(node.func)
        if call_name:
            # 임포트된 이름인 경우 원본 이름으로 변환
            original_name = self.imported_names.get(call_name, call_name)
            
            # 대문자로 시작하면 클래스일 가능성이 높음 (휴리스틱)
            if original_name and original_name[0].isupper():
                self.instantiations.append(original_name)
            else:
                self.calls.append(original_name)
                
        self.generic_visit(node)
        
    def _get_call_name(self, node):
        """호출 대상의 이름을 추출"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # obj.method() 형태
            value_name = self._get_call_name(node.value)
            if value_name:
                return f"{value_name}.{node.attr}"
        return None

class CodeParser(ast.NodeVisitor):
    def __init__(self, project_root):
        self.project_root = Path(project_root).resolve()
        self.nodes = []
        self.edges = []
        self.current_module = None
        self.current_class = None
        self.current_function = None
        self.module_imports = {}  # 모듈별 임포트 정보
        self.function_calls = {}  # 함수별 호출 정보
        self.function_instantiations = {}  # 함수별 인스턴스화 정보
        self.decorator_uses = {}  # 데코레이터 사용 정보
        self._star_imports_cache = {}  # star import 캐시
        
    def parse_project(self):
        """프로젝트 내 모든 파이썬 파일을 파싱합니다."""
        # 첫 번째 패스: 모든 정의와 임포트 수집
        for py_file in self.project_root.rglob("*.py"):
            if any(part.startswith('.') for part in py_file.parts):
                continue  # 숨김 디렉토리 건너뛰기
                
            module_path_str = self._get_module_path(py_file)
            self.current_module = module_path_str
            
            # 모듈 노드 추가
            self.nodes.append((self.current_module, {
                "type": NodeType.MODULE,
                "file_path": str(py_file.relative_to(self.project_root))
            }))
            
            with open(py_file, "r", encoding="utf-8") as f:
                try:
                    content = f.read()
                    tree = ast.parse(content, filename=str(py_file))
                    
                    # 동적 임포트 힌트 주석 처리
                    self._process_dynamic_import_hints(content)
                    
                    self.visit(tree)
                except Exception as e:
                    logger.warning(f"Error parsing {py_file}: {e}")
        
        # 두 번째 패스: 호출 관계 분석
        self._analyze_calls()
        self._analyze_instantiations()
        
        return self.nodes, self.edges
    
    def _process_dynamic_import_hints(self, content: str):
        """동적 임포트 힌트 주석 처리"""
        for line in content.split('\n'):
            if '# codesynapse: import' in line:
                parts = line.split('# codesynapse: import')
                if len(parts) > 1:
                    module_name = parts[1].strip()
                    self.edges.append((self.current_module, module_name, {
                        "type": EdgeType.IMPORTS,
                        "dynamic": True
                    }))
    
    def _get_module_path(self, py_file):
        """파일 경로를 모듈 경로로 변환"""
        module_path_str = str(py_file.relative_to(self.project_root).with_suffix("")).replace(os.sep, ".")
        
        # __init__.py 파일은 해당 패키지 이름으로 처리
        if module_path_str.endswith(".__init__"):
            module_path_str = module_path_str[:-9]
            
        return module_path_str

    def visit_ClassDef(self, node):
        """클래스 정의 분석"""
        class_name = f"{self.current_module}.{node.name}"
        
        # 데코레이터 처리
        decorators = []
        for decorator in node.decorator_list:
            dec_name = self._get_decorator_name(decorator)
            if dec_name:
                decorators.append(dec_name)
                self._add_decorator_edge(class_name, dec_name)
        
        self.nodes.append((class_name, {
            "type": NodeType.CLASS,
            "lineno": node.lineno,
            "docstring": ast.get_docstring(node),
            "decorators": decorators
        }))
        self.edges.append((self.current_module, class_name, {"type": EdgeType.CONTAINS}))
        
        # 상속 관계 처리
        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name:
                # 현재 모듈의 임포트 정보를 확인하여 전체 경로 구성
                full_base_name = self._resolve_name(base_name)
                self.edges.append((class_name, full_base_name, {"type": EdgeType.INHERITS}))
        
        # 타입 힌트 분석 (클래스 변수)
        self._analyze_class_type_hints(node, class_name)
        
        prev_class = self.current_class
        self.current_class = class_name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node):
        """함수/메서드 정의 분석"""
        if self.current_class:
            func_name = f"{self.current_class}.{node.name}"
            parent_node = self.current_class
            edge_type = EdgeType.DEFINES
        else:
            func_name = f"{self.current_module}.{node.name}"
            parent_node = self.current_module
            edge_type = EdgeType.CONTAINS

        # 데코레이터 처리
        decorators = []
        is_classmethod = False
        is_staticmethod = False
        
        for decorator in node.decorator_list:
            dec_name = self._get_decorator_name(decorator)
            if dec_name:
                decorators.append(dec_name)
                if dec_name == "classmethod":
                    is_classmethod = True
                elif dec_name == "staticmethod":
                    is_staticmethod = True
                else:
                    self._add_decorator_edge(func_name, dec_name)

        self.nodes.append((func_name, {
            "type": NodeType.FUNCTION,
            "lineno": node.lineno,
            "docstring": ast.get_docstring(node),
            "is_method": self.current_class is not None,
            "is_classmethod": is_classmethod,
            "is_staticmethod": is_staticmethod,
            "decorators": decorators
        }))
        self.edges.append((parent_node, func_name, {"type": edge_type}))
        
        # 타입 힌트 분석 (함수 시그니처)
        self._analyze_function_type_hints(node, func_name)
        
        # 함수 내부의 호출 분석
        prev_function = self.current_function
        self.current_function = func_name
        
        # CallAnalyzer를 사용하여 함수 내부 호출 수집
        analyzer = CallAnalyzer(func_name)
        analyzer.imported_names = self.module_imports.get(self.current_module, {})
        analyzer.visit(node)
        self.function_calls[func_name] = analyzer.calls
        self.function_instantiations[func_name] = analyzer.instantiations
        
        self.generic_visit(node)
        self.current_function = prev_function
    
    # AsyncFunctionDef도 동일하게 처리
    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node):
        """import 문 처리"""
        for alias in node.names:
            imported_name = alias.asname or alias.name
            if self.current_module not in self.module_imports:
                self.module_imports[self.current_module] = {}
            self.module_imports[self.current_module][imported_name] = alias.name
            self.edges.append((self.current_module, alias.name, {"type": EdgeType.IMPORTS}))

    def visit_ImportFrom(self, node):
        """from ... import ... 문 처리 (star import 및 상대 경로 포함)"""
        # 상대 경로 처리
        if node.level > 0:
            # 상대 임포트 해결
            module_parts = self.current_module.split('.')
            if node.level <= len(module_parts):
                base_module_parts = module_parts[:-node.level]
                if node.module:
                    full_module = '.'.join(base_module_parts + [node.module])
                else:
                    full_module = '.'.join(base_module_parts)
            else:
                # 패키지 밖으로 나가는 상대 임포트
                full_module = node.module if node.module else ""
        else:
            full_module = node.module
        
        if full_module:
            # Star import 처리
            if node.names[0].name == '*':
                self._handle_star_import(full_module)
            else:
                # 일반 import 처리
                for alias in node.names:
                    imported_name = alias.asname or alias.name
                    full_name = f"{full_module}.{alias.name}"
                    
                    if self.current_module not in self.module_imports:
                        self.module_imports[self.current_module] = {}
                    self.module_imports[self.current_module][imported_name] = full_name
                    
                    self.edges.append((self.current_module, full_name, {"type": EdgeType.IMPORTS}))

    def _handle_star_import(self, module_name: str):
        """Star import 처리"""
        self.edges.append((self.current_module, module_name, {
            "type": EdgeType.IMPORTS,
            "star": True
        }))
        
        # 가능하면 __all__ 확인 시도
        if module_name not in self._star_imports_cache:
            try:
                # 프로젝트 내부 모듈인 경우
                module_path = module_name.replace('.', os.sep) + '.py'
                full_path = self.project_root / module_path
                
                if not full_path.exists():
                    # __init__.py 확인
                    init_path = self.project_root / module_name.replace('.', os.sep) / '__init__.py'
                    if init_path.exists():
                        full_path = init_path
                
                if full_path.exists():
                    with open(full_path, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                        
                    # __all__ 찾기
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name) and target.id == '__all__':
                                    if isinstance(node.value, ast.List):
                                        all_names = []
                                        for elt in node.value.elts:
                                            if isinstance(elt, ast.Constant):
                                                all_names.append(elt.value)
                                        self._star_imports_cache[module_name] = all_names
                                        break
            except Exception as e:
                logger.debug(f"Could not analyze star import from {module_name}: {e}")
        
        # 캐시된 정보가 있으면 사용
        if module_name in self._star_imports_cache:
            for name in self._star_imports_cache[module_name]:
                full_name = f"{module_name}.{name}"
                if self.current_module not in self.module_imports:
                    self.module_imports[self.current_module] = {}
                self.module_imports[self.current_module][name] = full_name

    def _get_decorator_name(self, node):
        """데코레이터 이름 추출"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_full_attribute_name(node)
        elif isinstance(node, ast.Call):
            # @decorator() 형태
            return self._get_decorator_name(node.func)
        return None
    
    def _get_full_attribute_name(self, node):
        """속성의 전체 이름 추출"""
        if isinstance(node, ast.Attribute):
            base = self._get_full_attribute_name(node.value)
            if base:
                return f"{base}.{node.attr}"
            elif isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
        elif isinstance(node, ast.Name):
            return node.id
        return None

    def _add_decorator_edge(self, target: str, decorator: str):
        """데코레이터 사용 관계 추가"""
        resolved_decorator = self._resolve_name(decorator)
        self.edges.append((target, resolved_decorator, {
            "type": EdgeType.CALLS,  # 데코레이터는 호출로 간주
            "decorator": True
        }))

    def _analyze_function_type_hints(self, node: ast.FunctionDef, func_name: str):
        """함수의 타입 힌트 분석"""
        type_analyzer = TypeHintAnalyzer()
        
        # 매개변수 타입 힌트
        for arg in node.args.args:
            if arg.annotation:
                type_analyzer.visit(arg.annotation)
        
        # 반환 타입 힌트
        if node.returns:
            type_analyzer.visit(node.returns)
        
        # 타입 힌트에서 사용된 타입들을 임포트로 처리
        for type_name in type_analyzer.types:
            resolved_type = self._resolve_name(type_name)
            if resolved_type != type_name:  # 임포트된 타입인 경우
                self.edges.append((func_name, resolved_type, {
                    "type": EdgeType.IMPORTS,
                    "type_hint": True
                }))

    def _analyze_class_type_hints(self, node: ast.ClassDef, class_name: str):
        """클래스 변수의 타입 힌트 분석"""
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                type_analyzer = TypeHintAnalyzer()
                type_analyzer.visit(item.annotation)
                
                for type_name in type_analyzer.types:
                    resolved_type = self._resolve_name(type_name)
                    if resolved_type != type_name:
                        self.edges.append((class_name, resolved_type, {
                            "type": EdgeType.IMPORTS,
                            "type_hint": True
                        }))

    def _get_base_name(self, node):
        """상속 베이스 클래스 이름 추출"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_base_name(node.value)
            if value:
                return f"{value}.{node.attr}"
        return None
    
    def _resolve_name(self, name):
        """이름을 전체 경로로 해결"""
        # 현재 모듈의 임포트 정보 확인
        imports = self.module_imports.get(self.current_module, {})
        
        # 단순 이름인 경우
        if '.' not in name:
            if name in imports:
                return imports[name]
            # 같은 모듈 내의 클래스일 수 있음
            potential_local = f"{self.current_module}.{name}"
            if any(n[0] == potential_local for n in self.nodes):
                return potential_local
        else:
            # 점이 포함된 이름인 경우 첫 부분을 확인
            first_part = name.split('.')[0]
            if first_part in imports:
                return name.replace(first_part, imports[first_part], 1)
        
        return name
    
    def _analyze_calls(self):
        """수집된 호출 정보를 바탕으로 호출 관계 엣지 생성"""
        defined_entities = {node[0] for node in self.nodes}
        
        for caller, calls in self.function_calls.items():
            caller_module = '.'.join(caller.split('.')[:-1])
            
            for call in calls:
                # 호출 대상 해결
                resolved_call = self._resolve_call_target(call, caller_module, defined_entities)
                
                if resolved_call:
                    self.edges.append((caller, resolved_call, {"type": EdgeType.CALLS}))
    
    def _analyze_instantiations(self):
        """수집된 인스턴스화 정보를 바탕으로 INSTANTIATES 엣지 생성"""
        defined_entities = {node[0] for node in self.nodes}
        
        for caller, instantiations in self.function_instantiations.items():
            caller_module = '.'.join(caller.split('.')[:-1])
            
            for class_name in instantiations:
                # 클래스 해결
                resolved_class = self._resolve_call_target(class_name, caller_module, defined_entities)
                
                if resolved_class:
                    self.edges.append((caller, resolved_class, {"type": EdgeType.INSTANTIATES}))
    
    def _resolve_call_target(self, target: str, caller_module: str, defined_entities: set) -> Optional[str]:
        """호출/인스턴스화 대상 해결"""
        # 1. 정확한 매치
        if target in defined_entities:
            return target
        
        # 2. 같은 모듈 내의 함수/클래스
        local_target = f"{caller_module}.{target}"
        if local_target in defined_entities:
            return local_target
        
        # 3. 임포트된 이름 확인
        imports = self.module_imports.get(caller_module, {})
        if target in imports:
            imported_full = imports[target]
            if imported_full in defined_entities:
                return imported_full
            # 외부 라이브러리일 수 있음
            return imported_full
        
        # 4. 부분 경로 매치 (예: module.Class의 경우)
        if '.' in target:
            # 전체 경로로 시도
            if target in defined_entities:
                return target
            
            # 첫 부분이 임포트된 경우
            first_part = target.split('.')[0]
            if first_part in imports:
                resolved = target.replace(first_part, imports[first_part], 1)
                if resolved in defined_entities:
                    return resolved
                return resolved  # 외부 라이브러리일 수 있음
        
        return None