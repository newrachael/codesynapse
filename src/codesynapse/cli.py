#!/usr/bin/env python3
# src/codesynapse/cli.py
from pathlib import Path
import argparse
import sys
from . import __version__, generate_json


def main():
    p = argparse.ArgumentParser(
        prog="codesynapse",
        description="LLM-optimized Python code analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  codesynapse /path/to/project
  
  # Include code signatures and complexity
  codesynapse /path/to/project --include-code --complexity
  
  # Generate architecture view with patterns
  codesynapse /path/to/project --view architecture --detect-patterns
  
  # Split large projects into chunks
  codesynapse /path/to/project --chunk 4000 --mode friendly
"""
    )
    
    p.add_argument("project", help="Python project root directory")
    p.add_argument("-o", "--output", default="codesynapse.json",
                   help="Output file path (default: codesynapse.json)")
    
    # Serialization options
    p.add_argument("--mode", choices=["summary", "compressed", "friendly", "full"],
                   default="friendly",
                   help="Output mode (default: friendly)")
    p.add_argument("--view", choices=["architecture", "dependencies", "flow", "api"],
                   help="Generate a specific view instead of raw data")
    
    # Filtering options
    p.add_argument("--important-only", action="store_true",
                   help="Include only important nodes (top 5%% by usage)")
    p.add_argument("--depth", type=int, default=2,
                   help="Maximum call graph depth (default: 2)")
    
    # Enhancement options
    p.add_argument("--include-code", action="store_true",
                   help="Include function signatures and docstrings")
    p.add_argument("--complexity", action="store_true",
                   help="Calculate and include complexity metrics")
    p.add_argument("--test-coverage", action="store_true",
                   help="Analyze test coverage relationships")
    p.add_argument("--detect-patterns", action="store_true",
                   help="Detect common design patterns")
    
    # Output options
    p.add_argument("--chunk", type=int, metavar="TOKENS",
                   help="Split output into chunks of max TOKENS size")
    p.add_argument("--pretty", action="store_true", default=True,
                   help="Pretty-print JSON output (default: True)")
    p.add_argument("--minify", dest="pretty", action="store_false",
                   help="Minify JSON output")
    
    # Meta options
    p.add_argument("-v", "--version", action="version",
                   version=f"CodeSynapse {__version__}")
    p.add_argument("--verbose", action="store_true",
                   help="Enable verbose output")
    
    args = p.parse_args()

    proj = Path(args.project).resolve()
    if not proj.is_dir():
        sys.exit(f"❌ Error: '{proj}' is not a valid directory")

    if args.verbose:
        py_files = list(proj.rglob("*.py"))
        print(f"📊 Found {len(py_files)} Python files")
        print(f"🔧 Mode: {args.mode}")
        if args.view:
            print(f"👁️  View: {args.view}")
        if args.include_code:
            print("📝 Including code signatures")
        if args.complexity:
            print("📈 Calculating complexity metrics")

    try:
        generate_json(
            str(proj),
            output=args.output,
            mode=args.mode,
            view=args.view,
            important_only=args.important_only,
            max_depth=args.depth,
            chunk_tokens=args.chunk,
            pretty=args.pretty,
            include_code=args.include_code,
            complexity=args.complexity,
            test_coverage=args.test_coverage,
            detect_patterns=args.detect_patterns,
        )
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(f"❌ Error: {e}")


if __name__ == "__main__":
    main()