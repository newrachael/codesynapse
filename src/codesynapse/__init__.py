# src/codesynapse/__init__.py
"""
CodeSynapse 0.4.0-LLM
LLM-optimized Python code analyzer with enhanced metrics.
"""

from pathlib import Path
import json

from .builder import GraphBuilder
from .serializer import GraphSerializer

__version__ = "0.4.0-llm"
__author__ = "Raykim"
__email__ = "phillar85@gmail.com"


def generate_json(
    project_path: str,
    output: str = "codesynapse.json",
    *,
    mode: str = "compressed",
    view: str | None = None,
    important_only: bool = True,
    max_depth: int | None = 2,
    chunk_tokens: int | None = None,
    pretty: bool = True,
    include_code: bool = False,
    complexity: bool = False,
    test_coverage: bool = False,
    detect_patterns: bool = False,
):
    """
    Analyze a Python project and export JSON.

    Parameters
    ----------
    project_path : str
        Root directory of the Python project.
    output : str
        Output file path.
    mode : str
        Serialization mode: summary | compressed | friendly | full
    view : str | None
        Purpose-specific view: architecture | dependencies | flow | api
    important_only : bool
        Keep only the most-important nodes.
    max_depth : int | None
        Limit call-graph expansion depth.
    chunk_tokens : int | None
        Split output into multiple chunks.
    pretty : bool
        Pretty-print JSON.
    include_code : bool
        Include function signatures and docstrings.
    complexity : bool
        Calculate and include complexity metrics.
    test_coverage : bool
        Analyze test coverage relationships.
    detect_patterns : bool
        Detect common design patterns.
    """
    builder = GraphBuilder(project_path, collect_signatures=include_code)
    graph = builder.build()

    serializer = GraphSerializer(
        graph,
        project_path,
        important_only=important_only,
        max_depth=max_depth,
        include_code=include_code,
        complexity=complexity,
        test_coverage=test_coverage,
        detect_patterns=detect_patterns,
    )

    # View mode
    if view:
        data = serializer.generate_view(view)
        if isinstance(data, str):
            Path(output).write_text(data, encoding="utf-8")
        else:
            Path(output).write_text(
                json.dumps(data, indent=(2 if pretty else None), ensure_ascii=False),
                encoding="utf-8",
            )
        print(f"✅  view:{view} saved → {output}")
        return data

    # Chunking mode
    if chunk_tokens:
        chunks = serializer.to_llm_chunks(
            mode=mode,
            max_tokens=chunk_tokens,
        )
        base = Path(output)
        base.parent.mkdir(parents=True, exist_ok=True)
        for idx, chunk in enumerate(chunks, 1):
            part_file = base.with_stem(f"{base.stem}_part{idx}")
            part_file.write_text(
                json.dumps(chunk, indent=(2 if pretty else None), ensure_ascii=False),
                encoding="utf-8",
            )
        print(f"✅  {len(chunks)} JSON chunks saved under {base.parent}")
        return chunks

    # Single file output
    data = serializer.serialize(mode=mode)
    Path(output).write_text(
        json.dumps(data, indent=(2 if pretty else None), ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"✅  JSON saved → {output}")
    return data


__all__ = ["generate_json", "GraphBuilder", "GraphSerializer", "__version__"]