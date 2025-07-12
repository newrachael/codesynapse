# src/codesynapse/serializer.py

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import networkx as nx

from .rules import NodeType, EdgeType

class GraphSerializer:
    """그래프를 다양한 형식으로 직렬화하는 클래스"""
    
    def __init__(self, graph: nx.DiGraph, project_path: str = None):
        self.graph = graph
        self.project_path = project_path
    
    def to_json(self, include_metadata: bool = True, pretty: bool = True) -> str:
        """그래프를 JSON 문자열로 변환"""
        data = self.to_dict(include_metadata)
        
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False, default=str)
        return json.dumps(data, ensure_ascii=False, default=str)
    
    def to_dict(self, include_metadata: bool = True) -> Dict[str, Any]:
        """그래프를 딕셔너리로 변환"""
        result = {
            "nodes": self._serialize_nodes(),
            "edges": self._serialize_edges(),
            "summary": self._generate_summary()
        }
        
        if include_metadata:
            result["metadata"] = self._generate_metadata()
            
        return result
    
    def to_llm_format(self) -> Dict[str, Any]:
        """LLM이 이해하기 쉬운 구조화된 형태로 변환"""
        modules = {}
        external_deps = set()
        
        # 노드를 모듈별로 그룹화
        for node_id, attrs in self.graph.nodes(data=True):
            node_type = attrs.get("type", NodeType.FUNCTION)
            
            if node_type == NodeType.MODULE:
                modules[node_id] = {
                    "type": "module",
                    "classes": {},
                    "functions": [],
                    "imports": [],
                    "imported_by": []
                }
            elif node_type == NodeType.EXTERNAL_LIB:
                external_deps.add(node_id)
        
        # 클래스와 함수를 해당 모듈에 추가
        for node_id, attrs in self.graph.nodes(data=True):
            node_type = attrs.get("type", NodeType.FUNCTION)
            parts = node_id.split(".")
            
            if len(parts) >= 2:
                module_path = parts[0] if node_type == NodeType.MODULE else ".".join(parts[:-1])
                
                # 모듈 찾기
                while module_path and module_path not in modules:
                    if "." in module_path:
                        module_path = module_path.rsplit(".", 1)[0]
                    else:
                        break
                
                if module_path in modules:
                    if node_type == NodeType.CLASS:
                        class_name = parts[-1]
                        modules[module_path]["classes"][class_name] = {
                            "full_name": node_id,
                            "methods": [],
                            "inherits_from": [],
                            "inherited_by": [],
                            "instantiated_by": [],
                            "attributes": attrs.get("attributes", {})
                        }
                    elif node_type == NodeType.FUNCTION and len(parts) == 2:
                        # 모듈 레벨 함수
                        modules[module_path]["functions"].append({
                            "name": parts[-1],
                            "full_name": node_id,
                            "calls": [],
                            "called_by": [],
                            "attributes": attrs.get("attributes", {})
                        })
        
        # 엣지 정보 처리
        for source, target, attrs in self.graph.edges(data=True):
            edge_type = attrs.get("type", EdgeType.CALLS)
            
            if edge_type == EdgeType.IMPORTS:
                # Import 관계
                if source in modules:
                    modules[source]["imports"].append(target)
                if target in modules:
                    modules[target]["imported_by"].append(source)
                    
            elif edge_type == EdgeType.INHERITS:
                # 상속 관계
                source_parts = source.split(".")
                target_parts = target.split(".")
                
                if len(source_parts) >= 2:
                    source_module = ".".join(source_parts[:-1])
                    source_class = source_parts[-1]
                    
                    if source_module in modules and source_class in modules[source_module]["classes"]:
                        modules[source_module]["classes"][source_class]["inherits_from"].append(target)
                
                if len(target_parts) >= 2:
                    target_module = ".".join(target_parts[:-1])
                    target_class = target_parts[-1]
                    
                    if target_module in modules and target_class in modules[target_module]["classes"]:
                        modules[target_module]["classes"][target_class]["inherited_by"].append(source)
                        
            elif edge_type == EdgeType.CALLS:
                # 함수 호출 관계
                self._add_call_relationship(modules, source, target)
            
            elif edge_type == EdgeType.DEFINES:
                # 메서드 정의 (클래스가 메서드를 포함)
                if "." in source and "." in target:
                    class_parts = source.split(".")
                    method_parts = target.split(".")
                    
                    if len(class_parts) >= 2 and len(method_parts) >= 3:
                        module_path = ".".join(class_parts[:-1])
                        class_name = class_parts[-1]
                        method_name = method_parts[-1]
                        
                        if module_path in modules and class_name in modules[module_path]["classes"]:
                            modules[module_path]["classes"][class_name]["methods"].append({
                                "name": method_name,
                                "full_name": target,
                                "calls": [],
                                "called_by": []
                            })
        
        return {
            "project_structure": modules,
            "external_dependencies": list(external_deps),
            "statistics": self._generate_summary(),
            "call_graph": self._generate_call_graph(),
            "inheritance_tree": self._generate_inheritance_tree()
        }
    
    def _serialize_nodes(self) -> List[Dict[str, Any]]:
        """노드를 직렬화"""
        nodes = []
        for node_id, attrs in self.graph.nodes(data=True):
            node_data = {
                "id": node_id,
                "type": attrs.get("type", NodeType.FUNCTION).value
            }
            
            # 추가 속성들
            for key, value in attrs.items():
                if key != "type":
                    if hasattr(value, "value"):  # Enum 타입 처리
                        node_data[key] = value.value
                    else:
                        node_data[key] = value
                        
            nodes.append(node_data)
        
        return nodes
    
    def _serialize_edges(self) -> List[Dict[str, Any]]:
        """엣지를 직렬화"""
        edges = []
        for source, target, attrs in self.graph.edges(data=True):
            edge_data = {
                "source": source,
                "target": target,
                "type": attrs.get("type", EdgeType.CALLS).value
            }
            
            # 추가 속성들
            for key, value in attrs.items():
                if key != "type":
                    if hasattr(value, "value"):  # Enum 타입 처리
                        edge_data[key] = value.value
                    else:
                        edge_data[key] = value
                        
            edges.append(edge_data)
        
        return edges
    
    def _generate_summary(self) -> Dict[str, Any]:
        """그래프 요약 정보 생성"""
        node_types_count = {}
        edge_types_count = {}
        
        # 노드 타입별 카운트
        for _, attrs in self.graph.nodes(data=True):
            node_type = attrs.get("type", NodeType.FUNCTION)
            type_name = node_type.value if hasattr(node_type, "value") else str(node_type)
            node_types_count[type_name] = node_types_count.get(type_name, 0) + 1
        
        # 엣지 타입별 카운트
        for _, _, attrs in self.graph.edges(data=True):
            edge_type = attrs.get("type", EdgeType.CALLS)
            type_name = edge_type.value if hasattr(edge_type, "value") else str(edge_type)
            edge_types_count[type_name] = edge_types_count.get(type_name, 0) + 1
        
        # 복잡도 메트릭
        complexity_metrics = {
            "cyclomatic_complexity": self._calculate_cyclomatic_complexity(),
            "max_depth": self._calculate_max_depth(),
            "strongly_connected_components": nx.number_strongly_connected_components(self.graph),
            "is_dag": nx.is_directed_acyclic_graph(self.graph)
        }
        
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": node_types_count,
            "edge_types": edge_types_count,
            "complexity_metrics": complexity_metrics
        }
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """메타데이터 생성"""
        return {
            "generated_at": datetime.now().isoformat(),
            "project_path": str(self.project_path) if self.project_path else None,
            "generator": "CodeSynapse",
            "version": "0.1.0"
        }
    
    def _calculate_cyclomatic_complexity(self) -> int:
        """순환 복잡도 계산 (간단한 버전)"""
        # McCabe's cyclomatic complexity: E - N + 2P
        # E = edges, N = nodes, P = connected components
        if self.graph.number_of_nodes() == 0:
            return 0
        
        num_components = nx.number_weakly_connected_components(self.graph)
        return self.graph.number_of_edges() - self.graph.number_of_nodes() + 2 * num_components
    
    def _calculate_max_depth(self) -> int:
        """그래프의 최대 깊이 계산"""
        if not self.graph.nodes():
            return 0
        
        try:
            # 모든 최단 경로 길이 계산
            lengths = dict(nx.all_pairs_shortest_path_length(self.graph))
            max_depth = 0
            
            for source in lengths:
                for target, length in lengths[source].items():
                    max_depth = max(max_depth, length)
                    
            return max_depth
        except:
            return -1  # 계산 불가능한 경우
    
    def _add_call_relationship(self, modules: Dict, source: str, target: str):
        """함수 호출 관계 추가"""
        # source 찾기
        source_parts = source.split(".")
        if len(source_parts) >= 2:
            source_module = ".".join(source_parts[:-1])
            source_name = source_parts[-1]
            
            if source_module in modules:
                # 함수인지 메서드인지 확인
                for func in modules[source_module]["functions"]:
                    if func["full_name"] == source:
                        func["calls"].append(target)
                        break
                else:
                    # 클래스 메서드일 수 있음
                    if len(source_parts) >= 3:
                        class_name = source_parts[-2]
                        method_name = source_parts[-1]
                        if class_name in modules[source_module]["classes"]:
                            for method in modules[source_module]["classes"][class_name]["methods"]:
                                if method["full_name"] == source:
                                    method["calls"].append(target)
                                    break
    
    def _generate_call_graph(self) -> Dict[str, List[str]]:
        """호출 그래프 생성"""
        call_graph = {}
        
        for source, target, attrs in self.graph.edges(data=True):
            if attrs.get("type") == EdgeType.CALLS:
                if source not in call_graph:
                    call_graph[source] = []
                call_graph[source].append(target)
                
        return call_graph
    
    def _generate_inheritance_tree(self) -> Dict[str, Dict[str, Any]]:
        """상속 트리 생성"""
        inheritance_tree = {}
        
        for source, target, attrs in self.graph.edges(data=True):
            if attrs.get("type") == EdgeType.INHERITS:
                if target not in inheritance_tree:
                    inheritance_tree[target] = {
                        "base_class": target,
                        "derived_classes": []
                    }
                inheritance_tree[target]["derived_classes"].append(source)
                
        return inheritance_tree