# src/codesynapse/parser.py
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import Counter

from .rules import NodeType, EdgeType
from .complexity import ComplexityCalculator


def _full_attr(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _full_attr(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


class CallAnalyzer(ast.NodeVisitor):
    def __init__(self, scope: str, imports: Dict[str, str], known_classes: Set[str]):
        self.scope = scope
        self.imports = imports
        self.known = known_classes
        self.calls: list[str] = []
        self.insts: list[str] = []

    def visit_Call(self, node: ast.Call):
        name = _full_attr(node.func)
        if not name:
            self.generic_visit(node)
            return
        name = self.imports.get(name, name)
        (self.insts if name in self.known else self.calls).append(name)
        self.generic_visit(node)


class CodeParser(ast.NodeVisitor):
    def __init__(self, project_root: str | Path, collect_signatures: bool = False):
        self.root = Path(project_root).resolve()
        self.collect_signatures = collect_signatures
        
        # Results
        self.nodes: list[Tuple[str, Dict]] = []
        self.edges: list[Tuple[str, str, Dict]] = []
        
        # State
        self.current_module = None
        self.current_class = None
        
        # Additional info
        self.imports: Dict[str, Dict[str, str]] = {}
        self.calls: Dict[str, list[str]] = {}
        self.insts: Dict[str, list[str]] = {}
        self.call_counter: Counter[str] = Counter()
        
        # For complexity calculation
        self.complexity_calc = ComplexityCalculator()

    def parse_project(self):
        for py in self.root.rglob("*.py"):
            if any(part.startswith('.') for part in py.parts):
                continue
            try:
                self._parse_file(py)
            except Exception as e:
                print(f"⚠️  Error parsing {py}: {e}")
        self._flush_calls()
        return self.nodes, self.edges

    def _parse_file(self, py: Path):
        self.current_module = self._module_path(py)
        self.nodes.append((self.current_module, {"type": NodeType.MODULE, "file_path": str(py.relative_to(self.root))}))
        
        content = py.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py))
        
        # Store AST for complexity calculation if needed
        if self.collect_signatures:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    node._source_file = py
                    
        self.visit(tree)

    def _module_path(self, p: Path):
        s = ".".join(p.relative_to(self.root).with_suffix("").parts)
        return s[:-9] if s.endswith(".__init__") else s

    def visit_ClassDef(self, node: ast.ClassDef):
        cls = f"{self.current_module}.{node.name}"
        class_attrs = {
            "type": NodeType.CLASS,
            "docstring": ast.get_docstring(node),
            "lineno": node.lineno,
        }
        
        # Check for abstract base class
        if any(isinstance(d, ast.Name) and d.id == "ABC" for d in node.decorator_list):
            class_attrs["is_abstract"] = True
            
        self.nodes.append((cls, class_attrs))
        self.edges.append((self.current_module, cls, {"type": EdgeType.CONTAINS}))

        for base in node.bases:
            bn = self._resolve(_full_attr(base))
            if bn:
                self.edges.append((cls, bn, {"type": EdgeType.INHERITS}))

        prev = self.current_class
        self.current_class = cls
        for stmt in node.body:
            self.visit(stmt)
        self.current_class = prev

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self.current_class:
            fn = f"{self.current_class}.{node.name}"
            parent, et = self.current_class, EdgeType.DEFINES
        else:
            fn = f"{self.current_module}.{node.name}"
            parent, et = self.current_module, EdgeType.CONTAINS

        func_attrs = {
            "type": NodeType.FUNCTION,
            "docstring": ast.get_docstring(node),
            "lineno": node.lineno,
            "end_lineno": getattr(node, 'end_lineno', node.lineno),
            "is_async": isinstance(node, ast.AsyncFunctionDef),
        }
        
        # Extract signature if requested
        if self.collect_signatures:
            func_attrs["signature"] = self._extract_signature(node)
            func_attrs["cyclomatic_complexity"] = self.complexity_calc.calculate_cyclomatic(node)
            func_attrs["cognitive_complexity"] = self.complexity_calc.calculate_cognitive(node)
            
        # Check for special methods
        if node.name.startswith("__") and node.name.endswith("__"):
            func_attrs["is_dunder"] = True
            
        # Check decorators
        decorators = []
        for deco in node.decorator_list:
            deco_name = _full_attr(deco) or _full_attr(getattr(deco, 'func', None))
            if deco_name:
                decorators.append(deco_name)
                if deco_name in ["property", "classmethod", "staticmethod"]:
                    func_attrs[f"is_{deco_name}"] = True
        func_attrs["decorators"] = decorators

        self.nodes.append((fn, func_attrs))
        self.edges.append((parent, fn, {"type": et}))
        self._add_deco_edges(fn, node.decorator_list)

        analyzer = CallAnalyzer(
            fn,
            self.imports.get(self.current_module, {}),
            {n for n, a in self.nodes if a["type"] == NodeType.CLASS},
        )
        analyzer.visit(node)
        self.calls[fn] = analyzer.calls
        self.insts[fn] = analyzer.insts
        self.call_counter.update(analyzer.calls + analyzer.insts)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import):
        for a in node.names:
            asname = a.asname or a.name
            self.imports.setdefault(self.current_module, {})[asname] = a.name
            self.edges.append((self.current_module, a.name, {"type": EdgeType.IMPORTS}))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        base = self._resolve_relative(node.module or "", node.level)
        if not base:
            return
            
        if len(node.names) == 1 and node.names[0].name == "*":
            self.edges.append((self.current_module, f"{base}.*", {"type": EdgeType.IMPORTS}))
            return
            
        for a in node.names:
            full = f"{base}.{a.name}" if base else a.name
            asname = a.asname or a.name
            self.imports.setdefault(self.current_module, {})[asname] = full
            self.edges.append((self.current_module, full, {"type": EdgeType.IMPORTS}))

    def _resolve_relative(self, mod: str, level: int):
        if not level:
            return mod
        parts = self.current_module.split(".")
        if level > len(parts):
            return None
        prefix = ".".join(parts[:-level])
        return f"{prefix}.{mod}" if prefix and mod else (prefix or mod)

    def _resolve(self, name: str | None):
        if not name:
            return None
        imps = self.imports.get(self.current_module, {})
        if "." not in name and name in imps:
            return imps[name]
        first = name.split(".")[0]
        return name.replace(first, imps[first], 1) if first in imps else name

    def _add_deco_edges(self, target: str, decos: list[ast.AST]):
        for d in decos:
            dn = self._resolve(_full_attr(d) or _full_attr(getattr(d, 'func', None)))
            if dn:
                self.edges.append((target, dn, {"type": EdgeType.DECORATES}))
                self.edges.append((self.current_module, dn, {"type": EdgeType.IMPORTS}))

    def _flush_calls(self):
        for src, lst in self.calls.items():
            for dst in lst:
                if dst:
                    self.edges.append((src, dst, {"type": EdgeType.CALLS}))
        for src, lst in self.insts.items():
            for dst in lst:
                if dst:
                    self.edges.append((src, dst, {"type": EdgeType.INSTANTIATES}))

    def _extract_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature as string"""
        args = []
        
        # Handle arguments
        for i, arg in enumerate(node.args.args):
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except:
                    arg_str += ": Any"
            
            # Handle defaults
            defaults_start = len(node.args.args) - len(node.args.defaults)
            if i >= defaults_start:
                default_idx = i - defaults_start
                try:
                    default_str = ast.unparse(node.args.defaults[default_idx])
                    arg_str += f" = {default_str}"
                except:
                    arg_str += " = ..."
                    
            args.append(arg_str)
        
        # Handle *args and **kwargs
        if node.args.vararg:
            arg_str = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                try:
                    arg_str += f": {ast.unparse(node.args.vararg.annotation)}"
                except:
                    pass
            args.append(arg_str)
            
        if node.args.kwarg:
            arg_str = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                try:
                    arg_str += f": {ast.unparse(node.args.kwarg.annotation)}"
                except:
                    pass
            args.append(arg_str)
        
        # Return type
        returns = ""
        if node.returns:
            try:
                returns = f" -> {ast.unparse(node.returns)}"
            except:
                returns = " -> Any"
        
        func_name = node.name
        if isinstance(node, ast.AsyncFunctionDef):
            func_name = f"async {func_name}"
            
        return f"def {func_name}({', '.join(args)}){returns}"