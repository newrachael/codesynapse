# src/codesynapse/parser.py
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import Counter

from .rules import NodeType, EdgeType
from .complexity import ComplexityCalculator


def _full_attr(node: ast.AST) -> str | None:
    """Extract full attribute name from AST node"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _full_attr(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


class CallAnalyzer(ast.NodeVisitor):
    """Analyze function calls and class instantiations"""
    
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
        # Resolve imports
        name = self.imports.get(name, name)
        # Classify as instantiation or call
        if name in self.known:
            self.insts.append(name)
        else:
            self.calls.append(name)
        self.generic_visit(node)


class CodeParser(ast.NodeVisitor):
    """Parse Python code and extract structure, relationships, and signatures"""
    
    def __init__(self, project_root: str | Path, collect_signatures: bool = False):
        self.root = Path(project_root).resolve()
        self.collect_signatures = collect_signatures
        
        # Results
        self.nodes: list[Tuple[str, Dict]] = []
        self.edges: list[Tuple[str, str, Dict]] = []
        
        # State
        self.current_module = None
        self.current_class = None
        self.current_source = ""
        self.current_lines = []
        
        # Additional info
        self.imports: Dict[str, Dict[str, str]] = {}
        self.calls: Dict[str, list[str]] = {}
        self.insts: Dict[str, list[str]] = {}
        self.call_counter: Counter[str] = Counter()
        
        # For complexity calculation
        self.complexity_calc = ComplexityCalculator()
        
        # Debug mode - can be set externally
        self.debug = False

    def parse_project(self) -> Tuple[List, List]:
        """Parse all Python files in the project"""
        if self.debug:
            print(f"🔍 Starting to parse project at: {self.root}")
            print(f"📝 Signature collection: {'ENABLED' if self.collect_signatures else 'DISABLED'}")
            
        py_files = list(self.root.rglob("*.py"))
        if self.debug:
            print(f"📄 Found {len(py_files)} Python files")
            
        for py in py_files:
            # Skip hidden directories
            if any(part.startswith('.') for part in py.parts):
                continue
            try:
                if self.debug:
                    print(f"  📄 Parsing: {py.relative_to(self.root)}")
                self._parse_file(py)
            except Exception as e:
                print(f"⚠️  Error parsing {py}: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
                    
        self._flush_calls()
        
        if self.debug:
            self._debug_summary()
                
        return self.nodes, self.edges

    def _parse_file(self, py: Path):
        """Parse a single Python file"""
        self.current_module = self._module_path(py)
        self.nodes.append((
            self.current_module, 
            {
                "type": NodeType.MODULE, 
                "file_path": str(py.relative_to(self.root))
            }
        ))
        
        content = py.read_text(encoding="utf-8")
        self.current_source = content
        self.current_lines = content.splitlines()
        
        try:
            tree = ast.parse(content, filename=str(py))
            self.visit(tree)
        except SyntaxError as e:
            print(f"⚠️  Syntax error in {py}: {e}")

    def _module_path(self, p: Path) -> str:
        """Convert file path to module path"""
        s = ".".join(p.relative_to(self.root).with_suffix("").parts)
        return s[:-9] if s.endswith(".__init__") else s

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition"""
        cls = f"{self.current_module}.{node.name}"
        class_attrs = {
            "type": NodeType.CLASS,
            "docstring": ast.get_docstring(node),
            "lineno": node.lineno,
        }
        
        # Check for abstract base class
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        if any("ABC" in d or "abstract" in d for d in decorators if d):
            class_attrs["is_abstract"] = True
        
        class_attrs["decorators"] = [d for d in decorators if d]
            
        self.nodes.append((cls, class_attrs))
        self.edges.append((self.current_module, cls, {"type": EdgeType.CONTAINS}))

        # Handle inheritance
        for base in node.bases:
            bn = self._resolve(_full_attr(base))
            if bn:
                self.edges.append((cls, bn, {"type": EdgeType.INHERITS}))

        # Process class body
        prev = self.current_class
        self.current_class = cls
        for stmt in node.body:
            self.visit(stmt)
        self.current_class = prev

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function/method definition"""
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
            signature = self._extract_signature_enhanced(node)
            if signature:
                func_attrs["signature"] = signature
            else:
                # Fallback: try to extract from source
                sig_from_source = self._extract_signature_from_source(node)
                if sig_from_source:
                    func_attrs["signature"] = sig_from_source
                    
            # Calculate complexity
            try:
                func_attrs["cyclomatic_complexity"] = self.complexity_calc.calculate_cyclomatic(node)
                func_attrs["cognitive_complexity"] = self.complexity_calc.calculate_cognitive(node)
            except Exception as e:
                if self.debug:
                    print(f"⚠️  Complexity calculation failed for {fn}: {e}")
            
        # Check for special methods
        if node.name.startswith("__") and node.name.endswith("__"):
            func_attrs["is_dunder"] = True
            
        # Check decorators
        decorators = []
        for deco in node.decorator_list:
            deco_name = self._get_decorator_name(deco)
            if deco_name:
                decorators.append(deco_name)
                if deco_name in ["property", "classmethod", "staticmethod"]:
                    func_attrs[f"is_{deco_name}"] = True
        if decorators:
            func_attrs["decorators"] = decorators

        self.nodes.append((fn, func_attrs))
        self.edges.append((parent, fn, {"type": et}))
        
        # Add decorator edges
        self._add_deco_edges(fn, node.decorator_list)

        # Analyze calls within the function
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
        """Visit import statement"""
        for a in node.names:
            asname = a.asname or a.name
            self.imports.setdefault(self.current_module, {})[asname] = a.name
            self.edges.append((self.current_module, a.name, {"type": EdgeType.IMPORTS}))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from...import statement"""
        base = self._resolve_relative(node.module or "", node.level)
        if not base and node.level == 0:
            return
            
        if node.names[0].name == "*":
            self.edges.append((self.current_module, f"{base}.*", {"type": EdgeType.IMPORTS}))
            return
            
        for a in node.names:
            if base:
                full = f"{base}.{a.name}"
            else:
                full = a.name
            asname = a.asname or a.name
            self.imports.setdefault(self.current_module, {})[asname] = full
            self.edges.append((self.current_module, full, {"type": EdgeType.IMPORTS}))

    def _resolve_relative(self, mod: str, level: int) -> Optional[str]:
        """Resolve relative imports"""
        if not level:
            return mod
        parts = self.current_module.split(".")
        if level > len(parts):
            return None
        prefix = ".".join(parts[:-level])
        return f"{prefix}.{mod}" if prefix and mod else (prefix or mod)

    def _resolve(self, name: str | None) -> Optional[str]:
        """Resolve a name using import information"""
        if not name:
            return None
        imps = self.imports.get(self.current_module, {})
        if "." not in name and name in imps:
            return imps[name]
        first = name.split(".")[0]
        if first in imps:
            return name.replace(first, imps[first], 1)
        return name

    def _get_decorator_name(self, deco: ast.AST) -> Optional[str]:
        """Extract decorator name"""
        if isinstance(deco, ast.Name):
            return deco.id
        elif isinstance(deco, ast.Attribute):
            return _full_attr(deco)
        elif isinstance(deco, ast.Call):
            return self._get_decorator_name(deco.func)
        return None

    def _add_deco_edges(self, target: str, decos: list[ast.AST]):
        """Add decorator edges"""
        for d in decos:
            dn = self._resolve(self._get_decorator_name(d))
            if dn:
                self.edges.append((target, dn, {"type": EdgeType.DECORATES}))
                if not dn.startswith(self.current_module):
                    self.edges.append((self.current_module, dn, {"type": EdgeType.IMPORTS}))

    def _flush_calls(self):
        """Convert collected calls to edges"""
        for src, lst in self.calls.items():
            for dst in lst:
                if dst:
                    resolved = self._resolve(dst)
                    if resolved:
                        self.edges.append((src, resolved, {"type": EdgeType.CALLS}))
                        
        for src, lst in self.insts.items():
            for dst in lst:
                if dst:
                    resolved = self._resolve(dst)
                    if resolved:
                        self.edges.append((src, resolved, {"type": EdgeType.INSTANTIATES}))

    def _extract_signature_enhanced(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract function signature with full type annotations"""
        try:
            args = []
            
            # Handle self/cls for methods
            if self.current_class and node.args.args:
                first_arg = node.args.args[0].arg
                if first_arg in ('self', 'cls'):
                    args.append(first_arg)
                    start_idx = 1
                else:
                    start_idx = 0
            else:
                start_idx = 0
            
            # Process remaining positional arguments
            for i in range(start_idx, len(node.args.args)):
                arg = node.args.args[i]
                arg_str = arg.arg
                
                # Add type annotation
                if arg.annotation:
                    ann_str = self._unparse_annotation(arg.annotation)
                    arg_str += f": {ann_str}"
                
                # Handle defaults
                defaults_start = len(node.args.args) - len(node.args.defaults)
                if i >= defaults_start:
                    default_idx = i - defaults_start
                    if default_idx < len(node.args.defaults):
                        default_str = self._unparse_annotation(node.args.defaults[default_idx])
                        arg_str += f" = {default_str}"
                        
                args.append(arg_str)
            
            # Handle positional-only parameters (Python 3.8+)
            if hasattr(node.args, 'posonlyargs') and node.args.posonlyargs:
                # Add positional-only marker
                args.insert(len(node.args.posonlyargs), '/')
            
            # Handle *args
            if node.args.vararg:
                arg_str = f"*{node.args.vararg.arg}"
                if node.args.vararg.annotation:
                    ann_str = self._unparse_annotation(node.args.vararg.annotation)
                    arg_str += f": {ann_str}"
                args.append(arg_str)
            elif node.args.kwonlyargs:
                # Bare * for keyword-only args
                args.append("*")
            
            # Handle keyword-only args
            for i, arg in enumerate(node.args.kwonlyargs):
                arg_str = arg.arg
                if arg.annotation:
                    ann_str = self._unparse_annotation(arg.annotation)
                    arg_str += f": {ann_str}"
                
                # Handle kw_defaults
                if i < len(node.args.kw_defaults) and node.args.kw_defaults[i]:
                    default_str = self._unparse_annotation(node.args.kw_defaults[i])
                    arg_str += f" = {default_str}"
                
                args.append(arg_str)
                
            # Handle **kwargs
            if node.args.kwarg:
                arg_str = f"**{node.args.kwarg.arg}"
                if node.args.kwarg.annotation:
                    ann_str = self._unparse_annotation(node.args.kwarg.annotation)
                    arg_str += f": {ann_str}"
                args.append(arg_str)
            
            # Return type
            returns = ""
            if node.returns:
                returns = f" -> {self._unparse_annotation(node.returns)}"
            
            # Build final signature
            func_name = node.name
            if isinstance(node, ast.AsyncFunctionDef):
                func_name = f"async def {func_name}"
            else:
                func_name = f"def {func_name}"
                
            return f"{func_name}({', '.join(args)}){returns}"
            
        except Exception as e:
            if self.debug:
                print(f"⚠️  Failed to extract signature for {node.name}: {e}")
            return None

    def _unparse_annotation(self, node: ast.AST) -> str:
        """Unparse an annotation node to string"""
        try:
            # Python 3.9+ has ast.unparse
            if sys.version_info >= (3, 9):
                return ast.unparse(node)
            else:
                # Fallback for older versions
                return self._simple_unparse(node)
        except Exception:
            return "Any"

    def _simple_unparse(self, node: ast.AST) -> str:
        """Simple unparsing for common AST nodes (Python < 3.9)"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, (ast.Str, ast.Num)):  # Python 3.7
            return repr(node.n if isinstance(node, ast.Num) else node.s)
        elif isinstance(node, ast.NameConstant):  # Python 3.7
            return str(node.value)
        elif isinstance(node, ast.Attribute):
            value = self._simple_unparse(node.value)
            return f"{value}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            value = self._simple_unparse(node.value)
            if hasattr(node.slice, 'value'):  # Python 3.8 and earlier
                slice_val = self._simple_unparse(node.slice.value)
            else:
                slice_val = self._simple_unparse(node.slice)
            return f"{value}[{slice_val}]"
        elif isinstance(node, ast.Index):  # Python 3.8 and earlier
            return self._simple_unparse(node.value)
        elif isinstance(node, ast.List):
            elements = [self._simple_unparse(e) for e in node.elts]
            return f"[{', '.join(elements)}]"
        elif isinstance(node, ast.Tuple):
            elements = [self._simple_unparse(e) for e in node.elts]
            if len(elements) == 1:
                return f"({elements[0]},)"
            return f"({', '.join(elements)})"
        elif isinstance(node, ast.Dict):
            pairs = []
            for k, v in zip(node.keys, node.values):
                if k:
                    key = self._simple_unparse(k)
                    val = self._simple_unparse(v)
                    pairs.append(f"{key}: {val}")
                else:
                    val = self._simple_unparse(v)
                    pairs.append(f"**{val}")
            return f"{{{', '.join(pairs)}}}"
        elif isinstance(node, ast.Set):
            elements = [self._simple_unparse(e) for e in node.elts]
            return f"{{{', '.join(elements)}}}"
        elif isinstance(node, ast.Call):
            func = self._simple_unparse(node.func)
            args = [self._simple_unparse(arg) for arg in node.args]
            return f"{func}({', '.join(args)})"
        elif isinstance(node, ast.BinOp):
            # Handle Union types (e.g., int | str)
            left = self._simple_unparse(node.left)
            right = self._simple_unparse(node.right)
            if isinstance(node.op, ast.BitOr):
                return f"{left} | {right}"
            return f"{left} ? {right}"  # Fallback
        elif isinstance(node, ast.UnaryOp):
            operand = self._simple_unparse(node.operand)
            if isinstance(node.op, ast.Not):
                return f"not {operand}"
            return f"?{operand}"
        elif node is None:
            return "None"
        else:
            # Fallback for complex types
            return type(node).__name__

    def _extract_signature_from_source(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract signature directly from source code as fallback"""
        try:
            if not self.current_lines:
                return None
                
            # Find the function definition line
            start_line = node.lineno - 1
            end_line = start_line
            
            # Find where the signature ends (look for ':')
            lines = []
            paren_count = 0
            found_def = False
            
            for i in range(start_line, min(start_line + 50, len(self.current_lines))):
                line = self.current_lines[i]
                
                # Check if this line contains the def
                if not found_def and ('def ' in line or 'async def' in line):
                    found_def = True
                    
                if found_def:
                    lines.append(line)
                    # Count parentheses
                    for char in line:
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                    
                    # Check if we've found the complete signature
                    if ':' in line and paren_count == 0:
                        break
                        
            if lines:
                # Join lines and extract signature
                full_text = ' '.join(line.strip() for line in lines)
                # Remove everything after the colon
                if ':' in full_text:
                    sig_part = full_text.split(':', 1)[0].strip()
                    # Clean up extra whitespace
                    sig_part = ' '.join(sig_part.split())
                    return sig_part
                    
        except Exception as e:
            if self.debug:
                print(f"⚠️  Failed to extract signature from source: {e}")
                
        return None

    def _debug_summary(self):
        """Print debug summary of parsing results"""
        # Count by type
        type_counts = Counter(attrs["type"] for _, attrs in self.nodes)
        print(f"\n📊 Parsing Summary:")
        print(f"   Total nodes: {len(self.nodes)}")
        for node_type, count in type_counts.items():
            print(f"   - {node_type.value}: {count}")
            
        # Functions with signatures
        funcs_with_sigs = [
            (n, attrs) for n, attrs in self.nodes 
            if attrs.get("type") == NodeType.FUNCTION and "signature" in attrs
        ]
        print(f"\n📝 Functions with signatures: {len(funcs_with_sigs)}/{type_counts.get(NodeType.FUNCTION, 0)}")
        
        # Show first few signatures
        if funcs_with_sigs:
            print("   Examples:")
            for name, attrs in funcs_with_sigs[:5]:
                print(f"   - {name}")
                print(f"     {attrs['signature']}")
                if 'cyclomatic_complexity' in attrs:
                    print(f"     Complexity: {attrs['cyclomatic_complexity']}")
                    
        # Edge summary
        edge_counts = Counter(attrs["type"] for _, _, attrs in self.edges)
        print(f"\n🔗 Edge Summary:")
        for edge_type, count in edge_counts.items():
            print(f"   - {edge_type.value}: {count}")