# src/codesynapse/__init__.py

__version__ = "0.1.0"
__author__ = "Raykim"
__email__ = "phillar85@gmail.com"
__description__ = "A powerful Python tool that visualizes code structure and relationships as interactive graphs"

from .builder import GraphBuilder
from .visualizer import visualize_graph
from .serializer import GraphSerializer

def generate_graph(project_path, output_filename="codesynapse_graph.html"):
    """
    Generate an interactive graph visualization of a Python project.
    
    Args:
        project_path (str): Path to the Python project root directory.
        output_filename (str): Name of the output HTML file.
    """
    print(f"Starting analysis of project at: {project_path}")
    builder = GraphBuilder(project_path)
    graph = builder.build()
    print(f"Found {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
    visualize_graph(graph, output_filename)

def generate_json(project_path, output_filename="codesynapse_analysis.json", 
                  llm_format=False, include_metadata=True, pretty=True):
    """
    Generate a JSON analysis of a Python project structure.
    
    Args:
        project_path (str): Path to the Python project root directory.
        output_filename (str): Name of the output JSON file.
        llm_format (bool): Use LLM-friendly format if True.
        include_metadata (bool): Include metadata in output.
        pretty (bool): Pretty print JSON output.
    
    Returns:
        dict: The generated analysis data.
    """
    print(f"Starting analysis of project at: {project_path}")
    builder = GraphBuilder(project_path)
    graph = builder.build()
    print(f"Found {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
    
    serializer = GraphSerializer(graph, project_path)
    
    if llm_format:
        data = serializer.to_llm_format()
    else:
        data = serializer.to_dict(include_metadata=include_metadata)
    
    # Save to file
    import json
    with open(output_filename, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        else:
            json.dump(data, f, ensure_ascii=False, default=str)
    
    print(f"JSON analysis saved to: {output_filename}")
    return data

def analyze_project(project_path, return_format="dict", llm_format=False):
    """
    Analyze a Python project and return the analysis data.
    
    Args:
        project_path (str): Path to the Python project root directory.
        return_format (str): Format of return value - "dict", "json", or "graph".
        llm_format (bool): Use LLM-friendly format if True (only for dict/json).
    
    Returns:
        Union[dict, str, nx.DiGraph]: Analysis data in requested format.
    """
    builder = GraphBuilder(project_path)
    graph = builder.build()
    
    if return_format == "graph":
        return graph
    
    serializer = GraphSerializer(graph, project_path)
    
    if llm_format:
        data = serializer.to_llm_format()
    else:
        data = serializer.to_dict(include_metadata=True)
    
    if return_format == "json":
        import json
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    
    return data

__all__ = [
    "generate_graph", 
    "generate_json",
    "analyze_project",
    "GraphBuilder", 
    "visualize_graph",
    "GraphSerializer",
    "__version__"
]