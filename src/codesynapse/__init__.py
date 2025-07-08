# src/codesynapse/__init__.py

__version__ = "0.1.0"
__author__ = "Raykim"
__email__ = "phillar85@gmail.com"
__description__ = "A powerful Python tool that visualizes code structure and relationships as interactive graphs"

from .builder import GraphBuilder
from .visualizer import visualize_graph

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

__all__ = ["generate_graph", "GraphBuilder", "visualize_graph", "__version__"]