# src/codesynapse/rules.py
from enum import Enum


class NodeType(Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    EXTERNAL_LIB = "external"


class EdgeType(Enum):
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    CONTAINS = "contains"
    DEFINES = "defines"
    INSTANTIATES = "instantiates"
    DECORATES = "decorates"


class ComplexityLevel(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class DesignPattern(Enum):
    SINGLETON = "singleton"
    FACTORY = "factory"
    OBSERVER = "observer"
    DECORATOR = "decorator"
    ABSTRACT_BASE = "abstract_base"
    DEPENDENCY_INJECTION = "dependency_injection"