#!/usr/bin/env python3
"""
CodeSynapse CLI - Command Line Interface for code visualization
"""

import argparse
import sys
import json
from pathlib import Path
from . import __version__
from .builder import GraphBuilder
from .visualizer import visualize_graph
from .serializer import GraphSerializer
from .cache import ParseCache


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="CodeSynapse - Visualize Python code structure and relationships",
        epilog="Examples:\n"
               "  codesynapse /path/to/project --output my_graph.html\n"
               "  codesynapse /path/to/project --json --output analysis.json\n"
               "  codesynapse /path/to/project --json --llm-format\n"
               "  codesynapse /path/to/project --no-cache --no-parallel",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "project_path",
        help="Path to the Python project root directory"
    )
    
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file name (default: codesynapse_graph.html or codesynapse_analysis.json)"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of HTML visualization"
    )
    
    parser.add_argument(
        "--llm-format",
        action="store_true",
        help="Use LLM-friendly JSON format (implies --json)"
    )
    
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Exclude metadata from JSON output"
    )
    
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact JSON output (no pretty printing)"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching of parse results"
    )
    
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the parse cache"
    )
    
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel parsing"
    )
    
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of parallel workers"
    )
    
    parser.add_argument(
        "--filter-menu",
        action="store_true",
        help="Add interactive filter menu to HTML output"
    )
    
    parser.add_argument(
        "--search",
        action="store_true",
        help="Add search functionality to HTML output"
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
    
    # Clear cache if requested
    if args.clear_cache:
        cache = ParseCache()
        cache.clear()
        print("Parse cache cleared.")
        if not args.project_path or args.project_path == "clear-cache":
            sys.exit(0)
    
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
    
    # Determine output format and filename
    if args.json or args.llm_format:
        output_format = "json"
        default_output = "codesynapse_analysis.json"
    else:
        output_format = "html"
        default_output = "codesynapse_graph.html"
    
    output_file = args.output or default_output
    
    try:
        if args.verbose:
            print(f"Analyzing project: {project_path}")
            print(f"Output format: {output_format}")
            print(f"Output file: {output_file}")
            print(f"Found {len(python_files)} Python files")
            print(f"Cache: {'disabled' if args.no_cache else 'enabled'}")
            print(f"Parallel: {'disabled' if args.no_parallel else 'enabled'}")
        
        # Build the graph
        builder = GraphBuilder(
            str(project_path),
            use_cache=not args.no_cache,
            use_parallel=not args.no_parallel,
            max_workers=args.max_workers
        )
        graph = builder.build()
        
        if args.verbose:
            print(f"Built graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
            
            # 노드 타입별 통계
            from collections import Counter
            node_types = Counter(attrs.get("type", "unknown").value 
                               for _, attrs in graph.nodes(data=True))
            print("\nNode types:")
            for node_type, count in node_types.most_common():
                print(f"  {node_type}: {count}")
            
            # 엣지 타입별 통계
            edge_types = Counter(attrs.get("type", "unknown").value 
                               for _, _, attrs in graph.edges(data=True))
            print("\nEdge types:")
            for edge_type, count in edge_types.most_common():
                print(f"  {edge_type}: {count}")
        
        # Generate output based on format
        if output_format == "json":
            serializer = GraphSerializer(graph, str(project_path))
            
            if args.llm_format:
                if args.verbose:
                    print("Using LLM-friendly format")
                data = serializer.to_llm_format()
                
                # Save to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    if args.compact:
                        json.dump(data, f, ensure_ascii=False, default=str)
                    else:
                        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            else:
                # Standard JSON format
                json_str = serializer.to_json(
                    include_metadata=not args.no_metadata,
                    pretty=not args.compact
                )
                
                # Save to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_str)
            
            if args.verbose:
                # Print summary to console
                summary = serializer.to_dict(include_metadata=False)["summary"]
                print("\n📊 Analysis Summary:")
                print(f"  Total Nodes: {summary['total_nodes']}")
                print(f"  Total Edges: {summary['total_edges']}")
                print(f"  Node Types: {summary['node_types']}")
                print(f"  Edge Types: {summary['edge_types']}")
                if 'complexity_metrics' in summary:
                    print(f"  Cyclomatic Complexity: {summary['complexity_metrics']['cyclomatic_complexity']}")
                    print(f"  Is DAG: {summary['complexity_metrics']['is_dag']}")
        else:
            # HTML visualization
            options = {
                "filter_menu": args.filter_menu,
                "search": args.search
            }
            visualize_graph(graph, output_file, options=options)
        
        if args.verbose:
            print(f"\n✅ Output generated successfully: {output_file}")
        else:
            print(f"Output saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: Failed to generate output - {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()