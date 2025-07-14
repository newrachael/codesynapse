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
from typing import Any, Dict, List, Optional
from pathlib import Path
import networkx as nx

from .rules import NodeType, EdgeType, ComplexityLevel, DesignPattern


def _tok(obj) -> int:
    """Calculate approximate token count"""
    return math.ceil(len(json.dumps(obj, separators=(",", ":"))) / 4)


def _short(name: str) -> str:
    """Get the last part of a dotted name"""
    return name.split(".")[-1]


class GraphSerializer:
    """Serialize networkx graph to various formats optimized for LLMs"""
    
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
        self.debug = False  # Can be set externally

        # Pre-calculate common data
        self.ext_deps = sorted(
            n for n, a in graph.nodes(data=True) if a["type"] == NodeType.EXTERNAL_LIB
        )
        self.entry_points = [
            n for n in self.g.nodes if n.endswith(".main") or n.endswith("__main__")
        ][:3]

    def serialize(self, mode="compressed"):
        """Serialize graph to specified mode"""
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
        """Split serialized data into chunks for LLM context limits"""
        data = self.serialize(mode)
        if mode == "summary":
            return [data]

        # Determine the main list/dict key
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
        """Generate a specific view of the project"""
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
                "hot_paths": self._find_hot_paths(),
            }
            
        if view == "api":
            return {
                "public_api": self._extract_public_api(),
                "entry_points": self.entry_points,
                "class_hierarchy": self._extract_class_hierarchy(),
            }
            
        raise ValueError("view must be architecture|dependencies|flow|api")

    def generate_natural_summary(self) -> str:
        """Generate a natural language summary of the project"""
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
            summary += f"\nAverage complexity: {avg_complexity['rating']} (score: {avg_complexity['average']})"
            
        if self.test_coverage:
            coverage = self._analyze_test_coverage()
            summary += f"\nTest coverage: {coverage['test_modules']} test modules covering {coverage['coverage_ratio']*100:.0f}% of modules"
            
        return summary

    def _summary(self):
        """Generate basic summary statistics"""
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
        """Compressed format using string indexing"""
        strings, sindex = [], {}
        def idx(s):
            if s not in sindex:
                sindex[s] = len(strings)
                strings.append(s)
            return sindex[s]

        # Calculate importance threshold
        importances = [a.get("importance", 0) for _, a in self.g.nodes(data=True)]
        imp_thresh = max(importances, default=0) * 0.05 if self.important_only and importances else -1
        
        keep = {
            n for n, a in self.g.nodes(data=True)
            if not self.important_only or a.get("importance", 0) >= imp_thresh
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
        """LLM-friendly compressed format"""
        # Calculate importance threshold
        importances = [a.get("importance", 0) for _, a in self.g.nodes(data=True)]
        if importances and self.important_only:
            imp_thresh = max(importances) * 0.05
        else:
            imp_thresh = -1  # Include all

        if self.debug:
            print(f"\n📊 Importance threshold: {imp_thresh}")
            print(f"   Max importance: {max(importances) if importances else 0}")
            print(f"   Important only: {self.important_only}")

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
                    and "." not in n[len(m)+1:]  # Direct children only
                ][:3],
                "entry_points": [
                    _short(n) for n in self.g.nodes
                    if n.startswith(f"{m}.") and self.g.nodes[n]["type"] == NodeType.FUNCTION
                    and _short(n) in ("main", "__init__", "__call__")
                    and "." not in n[len(m)+1:]  # Direct children only
                ],
            }
            
            # Add code snippets if requested
            if self.include_code:
                mod_info["functions"] = self._extract_all_module_functions(m, imp_thresh)
                if self.debug and not mod_info["functions"]:
                    print(f"   ⚠️  No functions found for module: {mod_name}")
                
            # Add complexity metrics if requested
            if self.complexity:
                mod_info["complexity"] = self._calculate_module_complexity(m)
                
            modules[mod_name] = mod_info

        # Key relations
        relations = [
            f"{_short(s)} → {_short(t)}"
            for s, t, a in self.g.edges(data=True)
            if a["type"] in (EdgeType.INHERITS, EdgeType.INSTANTIATES)
            and (not self.important_only or self.g.nodes[s].get("importance", 0) >= imp_thresh)
        ][:20]

        result = {"modules": modules, "relations": relations, "focus": "architecture overview"}
        
        if self.detect_patterns:
            result["patterns"] = self._detect_patterns()
            
        return result

    def _full(self):
        """Full format with all details"""
        nodes = []
        for n, a in self.g.nodes(data=True):
            if self.important_only and a.get("importance", 0) == 0:
                continue
                
            node_data = {"id": n, "type": a["type"].value}
            
            # Add all attributes
            for key, value in a.items():
                if key not in ["type", "importance"]:
                    if hasattr(value, "value"):  # Enum
                        node_data[key] = value.value
                    else:
                        node_data[key] = value
            
            # Add code info if requested
            if self.include_code and a["type"] == NodeType.FUNCTION:
                if "signature" in a:
                    node_data["signature"] = a["signature"]
                if "docstring" in a and a["docstring"]:
                    node_data["docstring"] = a["docstring"][:200]
                    
            # Add complexity if requested
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

    def _extract_all_module_functions(self, module: str, imp_thresh: float) -> Dict[str, Any]:
        """Extract ALL functions (including class methods) with signatures"""
        functions = {}
        
        if self.debug:
            print(f"\n🔍 Extracting functions for module: {module}")
            print(f"   Include code: {self.include_code}")
            print(f"   Importance threshold: {imp_thresh}")
        
        # Find all functions in this module
        module_functions = []
        for node_id, attrs in self.g.nodes(data=True):
            if (attrs["type"] == NodeType.FUNCTION and 
                node_id.startswith(f"{module}.")):
                
                # Check importance
                node_importance = attrs.get("importance", 0)
                if not self.important_only or node_importance >= imp_thresh:
                    module_functions.append((node_id, attrs))
                    if self.debug:
                        print(f"   ✅ Found function: {node_id} (importance: {node_importance})")
                elif self.debug:
                    print(f"   ❌ Skipped due to importance: {node_id} ({node_importance} < {imp_thresh})")
        
        if self.debug:
            print(f"   Total functions found: {len(module_functions)}")
        
        # Process each function
        for node_id, attrs in module_functions:
            # Determine display name
            parts = node_id.split('.')
            if len(parts) >= 3:  # Class method: module.Class.method
                func_name = f"{parts[-2]}.{parts[-1]}"
            else:  # Module function: module.function
                func_name = parts[-1]
            
            # Skip private functions unless they're special
            if func_name.startswith('_') and not func_name.startswith('__'):
                continue
                
            func_info = {}
            
            # Add signature
            if "signature" in attrs:
                func_info["signature"] = attrs["signature"]
            else:
                # Construct basic signature
                if attrs.get("is_async"):
                    func_info["signature"] = f"async def {func_name}(...)"
                else:
                    func_info["signature"] = f"def {func_name}(...)"
                if self.debug:
                    print(f"   ⚠️  No signature for {func_name}, using placeholder")
                    
            # Add docstring
            if attrs.get("docstring"):
                doc = attrs["docstring"]
                if len(doc) > 100:
                    func_info["docstring"] = doc[:100] + "..."
                else:
                    func_info["docstring"] = doc
                    
            # Add decorators
            if attrs.get("decorators"):
                func_info["decorators"] = attrs["decorators"]
                
            # Add async flag
            if attrs.get("is_async"):
                func_info["is_async"] = True
                
            # Add complexity
            if self.complexity and "cyclomatic_complexity" in attrs:
                func_info["complexity"] = attrs["cyclomatic_complexity"]
                
            # Add special method flags
            for flag in ["is_property", "is_classmethod", "is_staticmethod", "is_dunder"]:
                if attrs.get(flag):
                    func_info[flag] = True
                    
            functions[func_name] = func_info
        
        # Sort by complexity, then name
        sorted_functions = sorted(
            functions.items(),
            key=lambda x: (
                -x[1].get("complexity", 0),  # Higher complexity first
                not x[0].startswith('__'),    # Dunder methods last
                x[0]                          # Alphabetical
            )
        )
        
        # Return top 20 functions
        return dict(sorted_functions[:20])

    def _calculate_module_complexity(self, module: str) -> Dict[str, Any]:
        """Calculate module-level complexity metrics"""
        functions = [
            n for n in self.g.nodes
            if n.startswith(f"{module}.") and 
            self.g.nodes[n]["type"] == NodeType.FUNCTION
        ]
        
        if not functions:
            return {"rating": ComplexityLevel.SIMPLE.value, "avg_cyclomatic": 0}
            
        complexities = []
        for f in functions:
            if "cyclomatic_complexity" in self.g.nodes[f]:
                complexities.append(self.g.nodes[f]["cyclomatic_complexity"])
                
        if not complexities:
            return {"rating": ComplexityLevel.SIMPLE.value, "avg_cyclomatic": 0}
            
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
            return {"rating": ComplexityLevel.SIMPLE.value, "average": 0}
            
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
                    if n in self.g and m in self.g and
                    self.g.edges.get((n, m), {}).get("type") == EdgeType.DEFINES
                ]
                
                method_names = [_short(m) for m in methods]
                
                # Check for singleton indicators
                if any(name in ["get_instance", "instance", "__new__"] for name in method_names):
                    patterns.append({
                        "type": DesignPattern.SINGLETON.value,
                        "class": _short(n),
                        "confidence": "high" if "instance" in str(method_names) else "medium"
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
                    
        # Observer pattern (has subscribe/notify methods)
        for n, a in self.g.nodes(data=True):
            if a["type"] == NodeType.CLASS:
                methods = self._get_class_methods(n)
                method_names = [_short(m) for m in methods]
                
                if any(name in ["subscribe", "attach", "register"] for name in method_names) and \
                   any(name in ["notify", "update", "publish"] for name in method_names):
                    patterns.append({
                        "type": DesignPattern.OBSERVER.value,
                        "class": _short(n),
                        "confidence": "high"
                    })
                    
        return patterns[:10]  # Return top 10 patterns

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
                        if not ("test" in target or "tests" in target):
                            module = ".".join(target.split(".")[:-1]) or target
                            tested_modules[module] += 1
                            
        total_modules = sum(1 for _, a in self.g.nodes(data=True) 
                          if a["type"] == NodeType.MODULE and not ("test" in _ or "tests" in _))
        test_module_count = len(test_modules)
        tested_module_count = len(tested_modules)
        
        return {
            "test_modules": test_module_count,
            "tested_modules": tested_module_count,
            "total_modules": total_modules,
            "coverage_ratio": round(tested_module_count / max(total_modules, 1), 2),
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
                    if t in self.g.nodes and self.g.nodes[t]["type"] == NodeType.EXTERNAL_LIB:
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
                    if t in self.g.nodes:
                        t_type = self.g.nodes[t]["type"]
                        if t_type == NodeType.MODULE:
                            deps.append(_short(t))
                        elif t_type != NodeType.EXTERNAL_LIB:
                            # Extract module from function/class
                            mod = ".".join(t.split(".")[:-1])
                            if mod and mod in self.g.nodes:
                                if self.g.nodes[mod]["type"] == NodeType.MODULE:
                                    deps.append(_short(mod))
                            
            if deps:
                graph[mod_name] = sorted(list(set(deps)))
                
        return graph

    def _analyze_call_chains(self) -> List[List[str]]:
        """Analyze significant call chains"""
        chains = []
        
        # Start from entry points
        for entry in self.entry_points[:3]:
            if entry in self.g.nodes:
                chain = self._trace_call_chain(entry, max_depth=5)
                if len(chain) > 2:
                    chains.append([_short(c) for c in chain])
                    
        return chains

    def _find_hot_paths(self) -> List[Dict[str, Any]]:
        """Find most frequently called paths"""
        call_counts = Counter()
        
        # Count incoming calls for each function
        for _, target, attrs in self.g.edges(data=True):
            if attrs["type"] == EdgeType.CALLS:
                call_counts[target] += 1
                
        # Find paths through hot functions
        hot_paths = []
        for func, count in call_counts.most_common(5):
            if func in self.g.nodes:
                # Trace backwards to find callers
                callers = []
                for source, _, attrs in self.g.in_edges(func, data=True):
                    if attrs["type"] == EdgeType.CALLS:
                        callers.append(source)
                        
                if callers:
                    hot_paths.append({
                        "function": _short(func),
                        "call_count": count,
                        "callers": [_short(c) for c in callers[:5]]
                    })
                    
        return hot_paths

    def _trace_call_chain(self, start: str, max_depth: int = 5) -> List[str]:
        """Trace a call chain from a starting point"""
        chain = [start]
        visited = {start}
        current = start
        
        for _ in range(max_depth):
            # Find most important call
            calls = []
            for _, target, attrs in self.g.out_edges(current, data=True):
                if attrs["type"] == EdgeType.CALLS and target not in visited:
                    importance = self.g.nodes[target].get("importance", 0)
                    calls.append((target, importance))
            
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
                        # Check if it's directly in the module
                        parts_after_module = n[len(m)+1:].split(".")
                        if len(parts_after_module) == 1:  # Direct child
                            item_info = {"name": _short(n)}
                            
                            if self.include_code and "signature" in node_attrs:
                                item_info["signature"] = node_attrs["signature"]
                            
                            if node_attrs.get("docstring"):
                                item_info["doc"] = node_attrs["docstring"][:80]
                                
                            public_items.append(item_info)
                            
            if public_items:
                api[_short(m)] = public_items[:20]
                
        return api

    def _extract_class_hierarchy(self) -> Dict[str, Any]:
        """Extract class inheritance hierarchy"""
        hierarchy = {}
        
        # Find all inheritance relationships
        for source, target, attrs in self.g.edges(data=True):
            if attrs["type"] == EdgeType.INHERITS:
                if target not in hierarchy:
                    hierarchy[target] = {"base": _short(target), "derived": []}
                hierarchy[target]["derived"].append(_short(source))
                
        # Add classes without inheritance
        for n, attrs in self.g.nodes(data=True):
            if attrs["type"] == NodeType.CLASS:
                class_name = _short(n)
                if n not in hierarchy and not any(n in h["derived"] for h in hierarchy.values()):
                    hierarchy[n] = {"base": class_name, "derived": []}
                    
        return hierarchy

    def _get_class_methods(self, class_node: str) -> List[str]:
        """Get all methods of a class"""
        methods = []
        for target, attrs in self.g.nodes(data=True):
            if (attrs["type"] == NodeType.FUNCTION and 
                target.startswith(f"{class_node}.")):
                methods.append(target)
        return methods

    def _core_modules(self) -> List[str]:
        """Identify core modules by importance"""
        score = Counter()
        for n, a in self.g.nodes(data=True):
            if a["type"] != NodeType.MODULE:
                mod = ".".join(n.split(".")[:-1])
                if mod:
                    score[mod] += a.get("importance", 0)
                    
        return [m for m, _ in score.most_common(10)]

    def _trace_main_flow(self) -> List[str]:
        """Trace main execution flow"""
        if not self.entry_points:
            # Try to find a main function
            for n in self.g.nodes:
                if n.endswith(".main") or n == "main":
                    return self._trace_call_chain(n, max_depth=10)
            return []
            
        return self._trace_call_chain(self.entry_points[0], max_depth=10)