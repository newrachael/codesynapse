# CodeSynapse

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](https://github.com/newrachael/codesynapse)

**CodeSynapse** is a powerful Python tool that visualizes the structure and relationships within your Python codebase as an interactive graph. It analyzes your code using Abstract Syntax Trees (AST) and generates beautiful, interactive HTML visualizations showing modules, classes, functions, and their interconnections.

## ✨ Features

- 📊 **Interactive Visualization**: Generate beautiful HTML graphs using pyvis
- 🔍 **AST-based Analysis**: Deep code analysis using Python's AST module
- 🏗️ **Relationship Mapping**: Discover imports, inheritance, and containment relationships
- 🎨 **Customizable Styling**: Different visual styles for modules, classes, and functions
- 📦 **Package Support**: Handles complex package structures with `__init__.py` files
- 🚀 **Easy to Use**: Simple CLI interface and programmatic API
- 🧪 **Well Tested**: Comprehensive test suite with high coverage

## 🚀 Quick Start

### Installation

#### From PyPI (Recommended)

```bash
# Install from PyPI
pip install codesynapse

# Verify installation
codesynapse --version
```

#### From Source

```bash
# Clone the repository
git clone https://github.com/newrachael/codesynapse.git
cd codesynapse

# Install the package
pip install -e .

# For development (with test dependencies)
pip install -e ".[test]"
```

### Basic Usage

```python
from codesynapse import generate_graph

# Analyze your project and generate visualization
generate_graph("/path/to/your/project", "output_graph.html")
```

### Command Line Usage

```bash
# Analyze current directory
codesynapse . --output my_project_graph.html

# Analyze specific project with verbose output
codesynapse /path/to/your/project --output analysis.html --verbose

# Quick analysis with default settings
codesynapse /path/to/project
```

## 📋 Example Output

CodeSynapse analyzes your Python project and creates an interactive graph showing:

- **Blue boxes** 📘: Modules and packages
- **Purple circles** 🟣: Classes
- **Green circles** 🟢: Functions and methods
- **Yellow database icons** 🗄️: External libraries

The graph shows various relationships:
- **Solid lines** → Containment (module contains class/function)
- **Dashed lines** ⇢ Inheritance (class inherits from another)
- **Dotted lines** ⋯ Import relationships

## 🏗️ Project Structure

```
codesynapse/
├── src/codesynapse/
│   ├── __init__.py          # Main API
│   ├── builder.py           # Graph construction
│   ├── parser.py            # AST parsing
│   ├── rules.py             # Node/edge types and styling
│   └── visualizer.py        # HTML visualization
├── tests/                   # Comprehensive test suite
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## 🔧 How It Works

1. **Parsing**: CodeSynapse uses Python's `ast` module to parse your source code
2. **Analysis**: Extracts modules, classes, functions, and their relationships
3. **Graph Building**: Constructs a NetworkX directed graph representing your code structure
4. **Visualization**: Uses pyvis to generate an interactive HTML visualization

## 📚 API Reference

### Main Function

```python
def generate_graph(project_path, output_filename="codesynapse_graph.html"):
    """
    Generate an interactive graph visualization of a Python project.
    
    Args:
        project_path (str): Path to the Python project root
        output_filename (str): Name of the output HTML file
    """
```

### Advanced Usage

```python
from codesynapse.builder import GraphBuilder
from codesynapse.visualizer import visualize_graph

# For more control over the process
builder = GraphBuilder("/path/to/project")
graph = builder.build()

# Customize visualization
visualize_graph(graph, "custom_output.html")
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/codesynapse --cov-report=html

# Run specific test modules
pytest tests/test_parser.py
pytest tests/test_builder.py
pytest tests/test_visualizer.py
```

The test suite includes:
- Unit tests for all components
- Integration tests for the full pipeline
- Mock tests for external dependencies
- Error handling and edge case testing

## 🎯 Use Cases

- **Code Documentation**: Generate visual documentation of your project structure
- **Code Review**: Understand complex codebases quickly
- **Refactoring**: Identify tightly coupled components
- **Architecture Analysis**: Visualize dependencies and relationships
- **Onboarding**: Help new team members understand project structure
- **Technical Debt**: Identify circular dependencies and architectural issues

## 🛠️ Development

### Setting up Development Environment

```bash
# Clone and setup
git clone https://github.com/newrachael/codesynapse.git
cd codesynapse

# Install in development mode
pip install -e ".[test]"

# Run tests
pytest

# Run linting (if you have it configured)
flake8 src/ tests/
```

### Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## 📋 Requirements

- Python 3.8+
- networkx
- pyvis
- pathlib (built-in)
- ast (built-in)

## 🐛 Known Limitations

- Currently focuses on static analysis (no runtime behavior)
- Function call relationships are not fully implemented
- Some complex inheritance patterns may not be captured perfectly
- Large projects may generate complex visualizations

## 📦 Publishing to PyPI

For maintainers who want to publish new versions to PyPI:

### Prerequisites

```bash
# Install build tools
pip install build twine

# Or install dev dependencies
pip install -e ".[dev]"
```

### Build and Upload

```bash
# 1. Update version in src/codesynapse/__init__.py and pyproject.toml
# 2. Update CHANGELOG.md

# 3. Clean previous builds
rm -rf dist/ build/ *.egg-info/

# 4. Build the package
python -m build

# 5. Check the package
twine check dist/*

# 6. Upload to TestPyPI (optional)
twine upload --repository testpypi dist/*

# 7. Upload to PyPI
twine upload dist/*

# 8. Create GitHub release
git tag v0.1.0
git push origin v0.1.0
```

### Testing the PyPI Package

```bash
# Test installation from PyPI
pip install codesynapse

# Test the CLI
codesynapse --version
codesynapse . --output test_graph.html
```

## 🗺️ Roadmap

- [ ] Add support for function call analysis
- [ ] Implement filtering options for large projects
- [ ] Add support for other output formats (PNG, SVG)
- [ ] Include docstring analysis
- [ ] Add complexity metrics
- [ ] Support for type hints analysis

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Raykim** - [phillar85@gmail.com](mailto:phillar85@gmail.com)

## 🙏 Acknowledgments

- Built with [NetworkX](https://networkx.org/) for graph operations
- Visualization powered by [pyvis](https://pyvis.readthedocs.io/)
- Inspired by the need for better code visualization tools

## 📊 Stats

![GitHub stars](https://img.shields.io/github/stars/newrachael/codesynapse)
![GitHub forks](https://img.shields.io/github/forks/newrachael/codesynapse)
![GitHub issues](https://img.shields.io/github/issues/newrachael/codesynapse)

---

**Happy coding!** 🚀 If you find this tool useful, please consider giving it a star ⭐
