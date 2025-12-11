"""Graph visualization and export utilities using matplotlib."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
import yaml

matplotlib.use("Agg")  # Non-interactive backend


def visualize_graph(
    graph: nx.DiGraph,
    graph_id: str,
    layout: str = "spring",
    output_dir: str = "graphs",
    filename: Optional[str] = None,
    show_labels: bool = True,
    dpi: int = 90,
    figsize: Tuple[int, int] = (10, 8),
) -> Dict[str, Any]:
    """Render graph to PNG file."""
    if graph.number_of_nodes() == 0:
        raise ValueError("Graph is empty, cannot visualize")

    # Layout
    if layout == "spring":
        pos = nx.spring_layout(graph, k=2, iterations=100)
    elif layout == "circular":
        pos = nx.circular_layout(graph)
    elif layout == "kamada_kawai":
        pos = nx.kamada_kawai_layout(graph)
    else:
        pos = nx.spring_layout(graph)

    # Colors by node type
    type_colors = {
        "action": "#93c5fd",
        "decision": "#fcd34d",
        "verification": "#c4b5fd",
        "loop": "#fb7185",
        "success": "#86efac",
        "failure": "#fca5a5",
    }
    node_colors = []
    for n in graph.nodes():
        t = graph.nodes[n].get("node_type", "action")
        node_colors.append(type_colors.get(t, "#cbd5e1"))

    fig, ax = plt.subplots(figsize=figsize)

    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        edge_color="black",
        arrows=True,
        arrowsize=20,
        width=1.5,
        alpha=0.8,
    )

    nx.draw_networkx_nodes(
        graph,
        pos,
        ax=ax,
        node_color=node_colors,
        node_size=1200,
        edgecolors="black",
        linewidths=1.2,
    )

    if show_labels:
        labels = {}
        for n in graph.nodes():
            label = graph.nodes[n].get("label", n)
            ntype = graph.nodes[n].get("node_type", "")
            labels[n] = f"{label}\n({ntype})" if ntype else label
        nx.draw_networkx_labels(graph, pos, labels=labels, ax=ax, font_size=8, font_weight="bold")

    # Edge labels (order / condition)
    edge_labels = {}
    for u, v, data in graph.edges(data=True):
        parts = []
        if "order" in data:
            parts.append(f"order={data['order']}")
        if "condition" in data:
            parts.append(f"cond={data['condition']}")
        if parts:
            edge_labels[(u, v)] = ", ".join(parts)
    if edge_labels:
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_size=7, ax=ax)

    ax.set_title(f"Graph: {graph_id}", fontsize=14, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if filename is None:
        filename = f"{graph_id}.png"
    if not filename.endswith(".png"):
        filename += ".png"
    file_path = output_path / filename

    plt.savefig(file_path, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return {
        "graph_id": graph_id,
        "format": "png",
        "file_path": str(file_path),
        "absolute_path": str(file_path.absolute()),
        "file_size_bytes": file_path.stat().st_size,
        "layout": layout,
        "num_nodes": graph.number_of_nodes(),
        "num_edges": graph.number_of_edges(),
    }


def export_graph_yaml(graph: nx.DiGraph, graph_id: str, output_path: str) -> Dict[str, Any]:
    """Export graph to YAML file."""
    data = {
        "graph_id": graph_id,
        "nodes": {},
        "edges": [],
    }
    for n in graph.nodes():
        node_data = dict(graph.nodes[n])
        node_data["node_id"] = n
        data["nodes"][n] = node_data
    for u, v, attrs in graph.edges(data=True):
        edge_data = dict(attrs)
        edge_data["from"] = u
        edge_data["to"] = v
        data["edges"].append(edge_data)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    return {
        "graph_id": graph_id,
        "format": "yaml",
        "file_path": str(path),
        "absolute_path": str(path.absolute()),
        "file_size_bytes": path.stat().st_size,
    }


def export_graph_json(graph: nx.DiGraph, graph_id: str, output_path: str) -> Dict[str, Any]:
    """Export graph to JSON file."""
    import json

    data = {
        "graph_id": graph_id,
        "nodes": {},
        "edges": [],
    }
    for n in graph.nodes():
        node_data = dict(graph.nodes[n])
        node_data["node_id"] = n
        data["nodes"][n] = node_data
    for u, v, attrs in graph.edges(data=True):
        edge_data = dict(attrs)
        edge_data["from"] = u
        edge_data["to"] = v
        data["edges"].append(edge_data)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return {
        "graph_id": graph_id,
        "format": "json",
        "file_path": str(path),
        "absolute_path": str(path.absolute()),
        "file_size_bytes": path.stat().st_size,
    }


def import_graph_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def import_graph_json(path: str) -> Dict[str, Any]:
    import json

    with open(path, "r") as f:
        return json.load(f)

