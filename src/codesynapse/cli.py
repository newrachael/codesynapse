#!/usr/bin/env python3
"""
CodeSynapse CLI - Command Line Interface for code visualization
"""

import argparse
import sys
from pathlib import Path
from . import generate_graph, __version__


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="CodeSynapse - Visualize Python code structure and relationships as interactive graphs",
        epilog="Example: codesynapse /path/to/project --output my_project_graph.html"
    )
    
    parser.add_argument(
        "project_path",
        help="Path to the Python project root directory"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="codesynapse_graph.html",
        help="Output HTML file name (default: codesynapse_graph.html)"
    )
    
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"CodeSynapse {__version__}"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate project path
    project_path = Path(args.project_path)
    if not project_path.exists():
        print(f"Error: Project path '{project_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"Error: '{project_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    
    # Check if the directory contains Python files
    python_files = list(project_path.rglob("*.py"))
    if not python_files:
        print(f"Warning: No Python files found in '{project_path}'.", file=sys.stderr)
    
    try:
        if args.verbose:
            print(f"Analyzing project: {project_path}")
            print(f"Output file: {args.output}")
            print(f"Found {len(python_files)} Python files")
        
        # Generate the graph
        generate_graph(str(project_path), args.output)
        
        if args.verbose:
            print("✅ Graph generation completed successfully!")
        
    except Exception as e:
        print(f"Error: Failed to generate graph - {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 