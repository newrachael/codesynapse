# src/codesynapse/parallel.py

import asyncio
import concurrent.futures
from pathlib import Path
from typing import List, Tuple, Dict, Any
import logging
import os
import ast
from .parser import CodeParser

logger = logging.getLogger(__name__)

class ParallelParser:
    """병렬로 파이썬 파일을 파싱하는 클래스"""
    
    def __init__(self, project_root: Path, max_workers: int = None):
        self.project_root = project_root
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
    
    async def parse_file_async(self, py_file: Path) -> Tuple[List, List]:
        """비동기로 단일 파일 파싱"""
        loop = asyncio.get_event_loop()
        
        # CPU 집약적 작업은 스레드 풀에서 실행
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            parser = CodeParser(self.project_root)
            result = await loop.run_in_executor(
                executor, 
                self._parse_single_file, 
                parser, 
                py_file
            )
        
        return result
    
    def _parse_single_file(self, parser: CodeParser, py_file: Path) -> Tuple[List, List]:
        """단일 파일 파싱 (동기)"""
        module_path_str = parser._get_module_path(py_file)
        parser.current_module = module_path_str
        
        nodes = [(module_path_str, {
            "type": "module",
            "file_path": str(py_file.relative_to(parser.project_root))
        })]
        edges = []
        
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(py_file))
            
            # 파서 상태 초기화
            parser.nodes = nodes
            parser.edges = edges
            
            # AST 방문
            parser.visit(tree)
            
            # 동적 임포트 힌트 처리
            parser._process_dynamic_import_hints(content)
            
            return parser.nodes, parser.edges
            
        except Exception as e:
            logger.warning(f"Error parsing {py_file}: {e}")
            return nodes, edges
    
    async def parse_project_async(self) -> Tuple[List, List]:
        """프로젝트 전체를 비동기로 파싱"""
        # 파이썬 파일 목록 수집
        py_files = []
        for py_file in self.project_root.rglob("*.py"):
            if not any(part.startswith('.') for part in py_file.parts):
                py_files.append(py_file)
        
        # 병렬로 파일 파싱
        tasks = [self.parse_file_async(py_file) for py_file in py_files]
        results = await asyncio.gather(*tasks)
        
        # 결과 병합
        all_nodes = []
        all_edges = []
        
        for nodes, edges in results:
            all_nodes.extend(nodes)
            all_edges.extend(edges)
        
        return all_nodes, all_edges
    
    def parse_project(self) -> Tuple[List, List]:
        """동기 인터페이스"""
        return asyncio.run(self.parse_project_async())