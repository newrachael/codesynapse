# src/codesynapse/builder.py

import networkx as nx
from pathlib import Path
import logging
from typing import Optional

from .parser import CodeParser
from .cache import ParseCache
from .parallel import ParallelParser

logger = logging.getLogger(__name__)

class GraphBuilder:
    def __init__(self, project_path, use_cache=True, use_parallel=True, max_workers=None):
        self.project_path = Path(project_path)
        self.graph = nx.DiGraph()
        self.use_cache = use_cache
        self.use_parallel = use_parallel
        self.max_workers = max_workers
        self.cache = ParseCache() if use_cache else None

    def build(self):
        """프로젝트를 분석하고 그래프를 생성합니다."""
        if self.use_parallel and self._should_use_parallel():
            logger.info("Using parallel parsing")
            parser = ParallelParser(self.project_path, self.max_workers)
            nodes, edges = parser.parse_project()
        else:
            logger.info("Using sequential parsing")
            parser = CodeParser(self.project_path)
            nodes, edges = parser.parse_project()

        # 그래프 구축
        for node_id, attrs in nodes:
            self.graph.add_node(node_id, **attrs)

        for source, target, attrs in edges:
            # target 노드가 그래프에 없을 경우 외부 라이브러리로 간주하고 추가
            if not self.graph.has_node(target):
                from .rules import NodeType
                self.graph.add_node(target, type=NodeType.EXTERNAL_LIB)
                
            self.graph.add_edge(source, target, **attrs)
        
        # 계층 레벨 계산 (시각화 개선용)
        self._calculate_hierarchy_levels()
            
        return self.graph
    
    def _should_use_parallel(self) -> bool:
        """병렬 처리를 사용할지 결정"""
        # 파일 수가 일정 수준 이상일 때만 병렬 처리
        py_files = list(self.project_path.rglob("*.py"))
        return len(py_files) > 10
    
    def _calculate_hierarchy_levels(self):
        """노드의 계층 레벨 계산"""
        # 모듈을 최상위 레벨로 설정
        from .rules import NodeType
        
        levels = {}
        
        # 레벨 0: 외부 라이브러리
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get("type") == NodeType.EXTERNAL_LIB:
                levels[node] = 0
        
        # 레벨 1: 모듈
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get("type") == NodeType.MODULE:
                levels[node] = 1
        
        # 레벨 2: 클래스
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get("type") == NodeType.CLASS:
                levels[node] = 2
        
        # 레벨 3: 함수/메서드
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get("type") == NodeType.FUNCTION:
                levels[node] = 3
        
        # 레벨 정보를 노드 속성에 추가
        nx.set_node_attributes(self.graph, levels, "level")