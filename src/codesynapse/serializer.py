# src/codesynapse/serializer.py
"""
Enhanced Serializer with code snippets and complexity metrics
"""

from __future__ import annotations
import json
import math
import itertools
from datetime import datetime
from collections import Counter
from typing import Any, Dict, List
from pathlib import Path
import networkx as nx

from .rules import NodeType, EdgeType, ComplexityLevel, DesignPattern


def _tok(obj) -> int:
    return math.ceil(len(json.dumps(obj, separators=(",", ":"))) / 4)


def _short(name: str) -> str:
    return name.split(".")[-1]


class GraphSerializer:
    def __init__(
        self,
        graph: nx.DiGraph,
        project_path: str | None = None,
        *,
        important_only: bool = False,
        max_depth: int | None = None,
        include_code: bool = False,
        complexity: bool = False,
        test_coverage: bool = False,
        detect_patterns: bool = False,
    ):
        self.g = graph
        self.path = project_path
        self.important_only = important_only
        self.max_depth = max_depth
        self.include_code = include_code
        self.complexity = complexity
        self.test_coverage = test_coverage
        self.detect_patterns = detect_patterns

        # Pre-calculate common data
        self.ext_deps = sorted(
            n for n, a in graph.nodes(data=True) if a["type"] == NodeType.EXTERNAL_LIB
        )
        self.entry_points = [
            n for n in self.g.nodes if n.endswith(".main") or n.endswith("__main__")
        ][:3]

    def serialize(self, mode="compressed"):
        if mode == "summary":
            return self._summary()
        if mode == "compressed":
            return self._compressed_index()
        if mode == "friendly":
            return self._compressed_friendly()
        if mode == "full":
            return self._full()
        raise ValueError(f"unknown mode {mode}")

    def to_llm_chunks(self, *, mode="compressed", max_tokens=4000):
        data = self.serialize(mode)
        if mode == "summary":
            return [data]

        list_key = "edges" if "edges" in data else "nodes"
        if "modules" in data:
            list_key = "modules"
            
        header = {k: v for k, v in data.items() if k != list_key}
        items = data[list_key] if isinstance(data[list_key], list) else list(data[list_key].items())

        chunks, cur, cur_tok = [], {**header, list_key: {} if isinstance(data[list_key], dict) else []}, _tok(header)
        
        for itm in items:
            t = _tok(itm)
            if cur_tok + t > max_tokens and cur[list_key]:
                chunks.append(cur)
                cur, cur_tok = {**header, list_key: {} if isinstance(data[list_key], dict) else []}, _tok(header)
            
            if isinstance(data[list_key], dict):
                cur[list_key][itm[0]] = itm[1]
            else:
                cur[list_key].append(itm)
            cur_tok += t
            
        if cur[list_key]:
            chunks.append(cur)
        return chunks

    def generate_view(self, view: str):
        view = view.lower()
        if view == "architecture":
            result = {
                "summary": self.generate_natural_summary(),
                **self._compressed_friendly(),
            }
            if self.complexity:
                result["complexity_overview"] = self._analyze_complexity()
            if self.detect_patterns:
                result["design_patterns"] = self._detect_patterns()
            return result
            
        if view == "dependencies":
            return {
                "external_dependencies": self.ext_deps,
                "module_imports": self._module_dependencies(),
                "dependency_graph": self._simplified_dependency_graph(),
            }
            
        if view == "flow":
            return {
                "main_flow": self._trace_main_flow(),
                "call_chains": self._analyze_call_chains(),
            }
            
        if view == "api":
            return {
                "public_api": self._extract_public_api(),
                "entry_points": self.entry_points,
            }
            
        raise ValueError("view must be architecture|dependencies|flow|api")

    def generate_natural_summary(self) -> str:
        stats = self._summary()["stats"]
        summary = (
            f"This project contains {stats['nodes']} components "
            f"across {len(stats['node_types'])} node types "
            f"and {len(self.ext_deps)} external dependencies.\n"
            f"Main entry point: {self.entry_points[0] if self.entry_points else 'N/A'}\n"
            f"Key dependencies: {', '.join(self.ext_deps[:5])}\n"
            f"Core modules: {', '.join(self._core_modules()[:5])}\n"
            f"Primary flow: {' → '.join(self._trace_main_flow()[:6])}"
        )
        
        if self.complexity:
            avg_complexity = self._calculate_avg_complexity()
            summary += f"\nAverage complexity: {avg_complexity['rating']}"
            
        return summary

    def _summary(self):
        nt, et = Counter(), Counter()
        for _, a in self.g.nodes(data=True):
            nt[a["type"].value] += 1
        for _, _, a in self.g.edges(data=True):
            et[a["type"].value] += 1
            
        result = {
            "stats": {
                "nodes": sum(nt.values()),
                "edges": sum(et.values()),
                "node_types": dict(nt),
                "edge_types": dict(et),
                "components": nx.number_weakly_connected_components(self.g),
            },
            "entry_points": self.entry_points,
            "external_deps": self.ext_deps[:20],
            "generated_at": datetime.now().isoformat(),
        }
        
        if self.test_coverage:
            result["test_coverage"] = self._analyze_test_coverage()
            
        return result

    def _compressed_index(self):
        strings, sindex = [], {}
        def idx(s):
            if s not in sindex:
                sindex[s] = len(strings)
                strings.append(s)
            return sindex[s]

        imp_thresh = max(
            (a["importance"] for _, a in self.g.nodes(data=True)), default=0
        ) * 0.05
        keep = {
            n for n, a in self.g.nodes(data=True)
            if not self.important_only or a["importance"] >= imp_thresh
        }

        nodes = [{"id": idx(n), "t": self.g.nodes[n]["type"].value} for n in keep]
        edges = [
            {"s": idx(s), "t": idx(t), "tp": a["type"].value}
            for s, t, a in self.g.edges(data=True)
            if s in keep and t in keep and a["type"] in
               (EdgeType.CALLS, EdgeType.INHERITS, EdgeType.IMPORTS)
        ]
        return {"strings": strings, "nodes": nodes, "edges": edges, "summary": self._summary()}

    def _compressed_friendly(self):
        imp_thresh = max((a["importance"] for _, a in self.g.nodes(data=True)), default=0) * 0.05

        modules = {}
        for m, attrs in self.g.nodes(data=True):
            if attrs["type"] != NodeType.MODULE:
                continue
                
            mod_name = _short(m)
            mod_info = {
                "path": m,
                "imports": [
                    _short(t) for _, t, a in self.g.out_edges(m, data=True)
                    if a["type"] == EdgeType.IMPORTS
                ][:5],
                "key_classes": [
                    _short(n) for n in self.g.nodes
                    if n.startswith(f"{m}.") and self.g.nodes[n]["type"] == NodeType.CLASS
                ][:3],
                "entry_points": [
                    _short(n) for n in self.g.nodes
                    if n.startswith(f"{m}.") and self.g.nodes[n]["type"] == NodeType.FUNCTION
                       and _short(n) in ("main", "__init__", "__call__")
                ],
            }
            
            # Add code snippets if requested
            if self.include_code:
                mod_info["functions"] = self._extract_module_functions(m, imp_thresh)
                
            # Add complexity metrics if requested
            if self.complexity:
                mod_info["complexity"] = self._calculate_module_complexity(m)
                
            modules[mod_name] = mod_info

        relations = [
            f"{_short(s)} → {_short(t)}"
            for s, t, a in self.g.edges(data=True)
            if a["type"] in (EdgeType.INHERITS, EdgeType.INSTANTIATES)
               and self.g.nodes[s]["importance"] >= imp_thresh
        ][:20]

        result = {"modules": modules, "relations": relations, "focus": "architecture overview"}
        
        if self.detect_patterns:
            result["patterns"] = self._detect_patterns()
            
        return result

    def _full(self):
        nodes = []
        for n, a in self.g.nodes(data=True):
            if self.important_only and a["importance"] == 0:
                continue
                
            node_data = {"id": n, "type": a["type"].value}
            
            if self.include_code and a["type"] == NodeType.FUNCTION:
                if "signature" in a:
                    node_data["signature"] = a["signature"]
                if "docstring" in a and a["docstring"]:
                    node_data["docstring"] = a["docstring"][:200]
                    
            if self.complexity and a["type"] == NodeType.FUNCTION:
                if "cyclomatic_complexity" in a:
                    node_data["complexity"] = {
                        "cyclomatic": a["cyclomatic_complexity"],
                        "cognitive": a.get("cognitive_complexity", 0)
                    }
                    
            nodes.append(node_data)
            
        edges = [
            {"source": s, "target": t, "type": a["type"].value}
            for s, t, a in self.g.edges(data=True)
        ]
        
        return {"nodes": nodes, "edges": edges, "summary": self._summary()}

    # Enhanced helper methods

    def _extract_module_functions(self, module: str, imp_thresh: float) -> Dict[str, Any]:
        """Extract important functions with signatures"""
        functions = {}
        
        for node_id, attrs in self.g.nodes(data=True):
            if (node_id.startswith(f"{module}.") and 
                attrs["type"] == NodeType.FUNCTION and
                not _short(node_id).startswith("_") and
                attrs["importance"] > imp_thresh and
                "." not in node_id[len(module)+1:]):  # Module-level functions only
                
                func_name = _short(node_id)
                func_info = {}
                
                if "signature" in attrs:
                    func_info["signature"] = attrs["signature"]
                if "docstring" in attrs and attrs["docstring"]:
                    func_info["docstring"] = attrs["docstring"][:100]
                if "decorators" in attrs and attrs["decorators"]:
                    func_info["decorators"] = attrs["decorators"]
                if "is_async" in attrs:
                    func_info["is_async"] = attrs["is_async"]
                    
                if self.complexity:
                    if "cyclomatic_complexity" in attrs:
                        func_info["complexity"] = attrs["cyclomatic_complexity"]
                        
                functions[func_name] = func_info
                
        # Return top 5 by complexity
        return dict(itertools.islice(
            sorted(functions.items(), 
                   key=lambda x: x[1].get("complexity", 0), 
                   reverse=True),
            5
        ))

    def _calculate_module_complexity(self, module: str) -> Dict[str, Any]:
        """Calculate module-level complexity metrics"""
        functions = [
            n for n in self.g.nodes
            if n.startswith(f"{module}.") and 
            self.g.nodes[n]["type"] == NodeType.FUNCTION
        ]
        
        if not functions:
            return {"rating": "simple", "avg_cyclomatic": 0}
            
        complexities = []
        for f in functions:
            if "cyclomatic_complexity" in self.g.nodes[f]:
                complexities.append(self.g.nodes[f]["cyclomatic_complexity"])
                
        if not complexities:
            return {"rating": "simple", "avg_cyclomatic": 0}
            
        avg_complexity = sum(complexities) / len(complexities)
        max_complexity = max(complexities)
        
        return {
            "rating": self._rate_complexity(avg_complexity),
            "avg_cyclomatic": round(avg_complexity, 2),
            "max_cyclomatic": max_complexity,
            "total_functions": len(functions),
            "complex_functions": [
                _short(f) for f in functions
                if self.g.nodes[f].get("cyclomatic_complexity", 0) > 10
            ][:5]
        }

    def _rate_complexity(self, score: float) -> str:
        """Rate complexity level"""
        if score < 5:
            return ComplexityLevel.SIMPLE.value
        elif score < 10:
            return ComplexityLevel.MODERATE.value
        elif score < 20:
            return ComplexityLevel.COMPLEX.value
        else:
            return ComplexityLevel.VERY_COMPLEX.value

    def _analyze_complexity(self) -> Dict[str, Any]:
        """Project-wide complexity analysis"""
        return {
            "by_module": {
                _short(m): self._calculate_module_complexity(m)
                for m, a in self.g.nodes(data=True)
                if a["type"] == NodeType.MODULE
            },
            "hotspots": self._find_complexity_hotspots(),
            "overall": self._calculate_avg_complexity()
        }

    def _find_complexity_hotspots(self) -> List[Dict[str, Any]]:
        """Find the most complex functions"""
        hotspots = []
        
        for n, a in self.g.nodes(data=True):
            if a["type"] == NodeType.FUNCTION and "cyclomatic_complexity" in a:
                if a["cyclomatic_complexity"] > 10:
                    hotspots.append({
                        "function": _short(n),
                        "module": ".".join(n.split(".")[:-1]),
                        "cyclomatic": a["cyclomatic_complexity"],
                        "cognitive": a.get("cognitive_complexity", 0)
                    })
                    
        return sorted(hotspots, key=lambda x: x["cyclomatic"], reverse=True)[:10]

    def _calculate_avg_complexity(self) -> Dict[str, Any]:
        """Calculate average project complexity"""
        all_complexities = []
        
        for _, a in self.g.nodes(data=True):
            if a["type"] == NodeType.FUNCTION and "cyclomatic_complexity" in a:
                all_complexities.append(a["cyclomatic_complexity"])
                
        if not all_complexities:
            return {"rating": "simple", "average": 0}
            
        avg = sum(all_complexities) / len(all_complexities)
        return {
            "rating": self._rate_complexity(avg),
            "average": round(avg, 2),
            "total_functions": len(all_complexities)
        }

    def _detect_patterns(self) -> List[Dict[str, Any]]:
        """Detect common design patterns"""
        patterns = []
        
        # Singleton pattern
        for n, a in self.g.nodes(data=True):
            if a["type"] == NodeType.CLASS:
                methods = [
                    m for m in self.g.successors(n)
                    if self.g.edges[n, m]["type"] == EdgeType.DEFINES
                ]
                
                method_names = [_short(m) for m in methods]
                
                # Check for singleton indicators
                if any(name in ["get_instance", "instance", "__new__"] for name in method_names):
                    if any("instance" in self.g.nodes[m].get("docstring", "").lower() for m in methods):
                        patterns.append({
                            "type": DesignPattern.SINGLETON.value,
                            "class": _short(n),
                            "confidence": "high"
                        })
                        
                # Check for factory pattern
                if any(name in ["create", "build", "make"] for name in method_names):
                    patterns.append({
                        "type": DesignPattern.FACTORY.value,
                        "class": _short(n),
                        "confidence": "medium"
                    })
                    
                # Check for abstract base class
                if a.get("is_abstract"):
                    patterns.append({
                        "type": DesignPattern.ABSTRACT_BASE.value,
                        "class": _short(n),
                        "confidence": "high"
                    })
                    
        # Dependency injection pattern
        for n, a in self.g.nodes(data=True):
            if a["type"] == NodeType.FUNCTION and "signature" in a:
                sig = a["signature"]
                # Simple check for DI pattern
                if sig.count(":") > 2 and "__init__" in n:
                    patterns.append({
                        "type": DesignPattern.DEPENDENCY_INJECTION.value,
                        "function": _short(n),
                        "confidence": "low"
                    })
                    
        return patterns

    def _analyze_test_coverage(self) -> Dict[str, Any]:
        """Analyze test coverage relationships"""
        test_modules = []
        tested_modules = Counter()
        
        for n, a in self.g.nodes(data=True):
            if a["type"] == NodeType.MODULE and ("test" in n or "tests" in n):
                test_modules.append(n)
                
                # Find what this test module tests
                for _, target, edge_attrs in self.g.out_edges(n, data=True):
                    if edge_attrs["type"] in [EdgeType.IMPORTS, EdgeType.CALLS]:
                        if not ("test" in target):
                            module = ".".join(target.split(".")[:-1]) or target
                            tested_modules[module] += 1
                            
        total_modules = sum(1 for _, a in self.g.nodes(data=True) if a["type"] == NodeType.MODULE)
        test_module_count = len(test_modules)
        tested_module_count = len(tested_modules)
        
        return {
            "test_modules": test_module_count,
            "tested_modules": tested_module_count,
            "total_modules": total_modules,
            "coverage_ratio": round(tested_module_count / max(total_modules - test_module_count, 1), 2),
            "most_tested": [m for m, _ in tested_modules.most_common(5)]
        }

    def _module_dependencies(self) -> Dict[str, List[str]]:
        """Module-level dependency mapping"""
        deps = {}
        
        for m, a in self.g.nodes(data=True):
            if a["type"] != NodeType.MODULE:
                continue
                
            imports = set()
            for _, t, edge_a in self.g.out_edges(m, data=True):
                if edge_a["type"] == EdgeType.IMPORTS:
                    # Extract module part
                    if self.g.nodes[t]["type"] == NodeType.EXTERNAL_LIB:
                        imports.add(_short(t).split(".")[0])
                    else:
                        mod_parts = t.split(".")
                        if len(mod_parts) > 1:
                            imports.add(mod_parts[0])
                            
            deps[_short(m)] = sorted(imports)[:10]
            
        return deps

    def _simplified_dependency_graph(self) -> Dict[str, List[str]]:
        """Simplified module dependency graph"""
        graph = {}
        
        for m, a in self.g.nodes(data=True):
            if a["type"] != NodeType.MODULE:
                continue
                
            mod_name = _short(m)
            deps = []
            
            # Find internal module dependencies
            for _, t, edge_a in self.g.out_edges(m, data=True):
                if edge_a["type"] == EdgeType.IMPORTS:
                    if t in self.g.nodes and self.g.nodes[t]["type"] == NodeType.MODULE:
                        deps.append(_short(t))
                    elif "." in t:
                        # Extract module part
                        mod = ".".join(t.split(".")[:-1])
                        if mod in self.g.nodes and self.g.nodes[mod]["type"] == NodeType.MODULE:
                            deps.append(_short(mod))
                            
            if deps:
                graph[mod_name] = list(set(deps))
                
        return graph

    def _analyze_call_chains(self) -> List[List[str]]:
        """Analyze significant call chains"""
        chains = []
        
        # Start from entry points
        for entry in self.entry_points[:3]:
            chain = self._trace_call_chain(entry, max_depth=5)
            if len(chain) > 2:
                chains.append([_short(c) for c in chain])
                
        return chains

    def _trace_call_chain(self, start: str, max_depth: int = 5) -> List[str]:
        """Trace a call chain from a starting point"""
        chain = [start]
        visited = {start}
        current = start
        
        for _ in range(max_depth):
            # Find most important call
            calls = [
                (t, self.g.nodes[t]["importance"])
                for _, t, a in self.g.out_edges(current, data=True)
                if a["type"] == EdgeType.CALLS and t not in visited
            ]
            
            if not calls:
                break
                
            next_node = max(calls, key=lambda x: x[1])[0]
            chain.append(next_node)
            visited.add(next_node)
            current = next_node
            
        return chain

    def _extract_public_api(self) -> Dict[str, List[str]]:
        """Extract public API per module"""
        api = {}
        
        for m, a in self.g.nodes(data=True):
            if a["type"] != NodeType.MODULE:
                continue
                
            public_items = []
            
            # Find public classes and functions
            for n in self.g.nodes:
                if n.startswith(f"{m}.") and not _short(n).startswith("_"):
                    node_attrs = self.g.nodes[n]
                    if node_attrs["type"] in [NodeType.CLASS, NodeType.FUNCTION]:
                        # Check if it's directly in the module (not nested)
                        parts_after_module = n[len(m)+1:].split(".")
                        if len(parts_after_module) == 1:  # Direct child
                            item = _short(n)
                            if self.include_code and "signature" in node_attrs:
                                item = node_attrs["signature"]
                            public_items.append(item)
                            
            if public_items:
                api[_short(m)] = sorted(public_items)[:20]
                
        return api

    def _core_modules(self):
        """Identify core modules by importance"""
        score = Counter()
        for n, a in self.g.nodes(data=True):
            if a["type"] == NodeType.MODULE:
                continue
            mod = ".".join(n.split(".")[:-1])
            score[mod] += a["importance"]
        return [m for m, _ in score.most_common(10)]

    def _trace_main_flow(self):
        """Trace main execution flow"""
        if not self.entry_points:
            return []
        start = self.entry_points[0]
        path = [start]
        visited = {start}
        cur = start
        for _ in range(10):
            nxt_edges = [
                (t, self.g.nodes[t]["importance"])
                for _, t, a in self.g.out_edges(cur, data=True)
                if a["type"] == EdgeType.CALLS and t not in visited
            ]
            if not nxt_edges:
                break
            nxt = max(nxt_edges, key=lambda x: x[1])[0]
            path.append(nxt)
            visited.add(nxt)
            cur = nxt
        return [_short(p) for p in path]