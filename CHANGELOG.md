# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-12-19

### Added
- Initial release of CodeSynapse
- AST-based Python code parser with support for modules, classes, and functions
- Interactive graph visualization using pyvis and NetworkX
- Support for inheritance and import relationship analysis
- Command-line interface (`codesynapse` command)
- Comprehensive test suite with 95%+ coverage
- Beautiful HTML output with customizable node and edge styling
- Support for complex package structures with `__init__.py` files
- Automatic external library detection
- Hierarchical layout for better visualization

### Features
- **Parser**: Deep code analysis using Python's AST module
- **Visualizer**: Interactive HTML graphs with pyvis
- **CLI**: Easy-to-use command-line interface
- **Testing**: Extensive test coverage for reliability
- **Styling**: Professional visual themes for different node types

### Documentation
- Complete README with usage examples
- API documentation and advanced usage guide
- Development setup and contribution guidelines
- MIT License for open-source usage

### Technical Details
- Python 3.8+ support
- NetworkX for graph operations
- pyvis for interactive visualizations
- Modern packaging with pyproject.toml
- Type hints and comprehensive error handling 