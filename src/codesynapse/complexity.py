# src/codesynapse/complexity.py
import ast
import math
from typing import Dict, Any


class ComplexityCalculator:
    """Calculate various code complexity metrics"""
    
    @staticmethod
    def calculate_cyclomatic(node: ast.AST) -> int:
        """McCabe's Cyclomatic Complexity"""
        complexity = 1
        
        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):  # and, or
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += sum(1 for _ in child.ifs) + 1
                
        return complexity
    
    @staticmethod
    def calculate_cognitive(node: ast.AST) -> int:
        """Cognitive Complexity (Sonar)"""
        class CognitiveVisitor(ast.NodeVisitor):
            def __init__(self):
                self.score = 0
                self.nesting = 0
                
            def visit_If(self, node):
                self.score += (1 + self.nesting)
                if hasattr(node, 'orelse') and node.orelse:
                    # else/elif adds complexity
                    self.score += 1
                self.nesting += 1
                self.generic_visit(node)
                self.nesting -= 1
                
            def visit_For(self, node):
                self.score += (1 + self.nesting)
                self.nesting += 1
                self.generic_visit(node)
                self.nesting -= 1
                
            def visit_While(self, node):
                self.score += (1 + self.nesting)
                self.nesting += 1
                self.generic_visit(node)
                self.nesting -= 1
                
            def visit_ExceptHandler(self, node):
                self.score += (1 + self.nesting)
                self.nesting += 1
                self.generic_visit(node)
                self.nesting -= 1
                
            def visit_BoolOp(self, node):
                # Each logical operator adds complexity
                self.score += len(node.values) - 1
                self.generic_visit(node)
                
            def visit_Lambda(self, node):
                self.score += 1
                self.generic_visit(node)
        
        visitor = CognitiveVisitor()
        visitor.visit(node)
        return visitor.score
    
    @staticmethod
    def calculate_halstead(node: ast.AST) -> Dict[str, float]:
        """Halstead Complexity Metrics"""
        operators = []
        operands = []
        
        for child in ast.walk(node):
            # Operators
            if isinstance(child, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
                                ast.Pow, ast.LShift, ast.RShift, ast.BitOr,
                                ast.BitXor, ast.BitAnd, ast.FloorDiv)):
                operators.append(type(child).__name__)
            elif isinstance(child, (ast.And, ast.Or, ast.Not)):
                operators.append(type(child).__name__)
            elif isinstance(child, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
                                  ast.Is, ast.IsNot, ast.In, ast.NotIn)):
                operators.append(type(child).__name__)
            elif isinstance(child, ast.Call):
                operators.append('Call')
            elif isinstance(child, ast.Attribute):
                operators.append('Attribute')
            elif isinstance(child, ast.Subscript):
                operators.append('Subscript')
                
            # Operands
            elif isinstance(child, ast.Name):
                operands.append(child.id)
            elif isinstance(child, ast.Constant):
                operands.append(str(child.value))
            elif isinstance(child, ast.Str):  # For older Python versions
                operands.append(child.s)
            elif isinstance(child, ast.Num):  # For older Python versions
                operands.append(str(child.n))
                
        n1 = len(set(operators))  # unique operators
        n2 = len(set(operands))   # unique operands
        N1 = len(operators)       # total operators
        N2 = len(operands)        # total operands
        
        if n1 == 0 or n2 == 0:
            return {"volume": 0, "difficulty": 0, "effort": 0}
            
        vocabulary = n1 + n2
        length = N1 + N2
        volume = length * math.log2(vocabulary) if vocabulary > 0 else 0
        difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0
        effort = volume * difficulty
        
        return {
            "volume": round(volume, 2),
            "difficulty": round(difficulty, 2),
            "effort": round(effort, 2),
            "vocabulary": vocabulary,
            "length": length
        }