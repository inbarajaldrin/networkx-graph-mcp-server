"""
Flask web server for NetworkX graph visualization.
Run with: uv run app.py
Visit: http://localhost:5000
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

# Import from the existing package
from src.networkx_graph.state_graph import StateGraph
from src.networkx_graph.visualization import import_graph_json, import_graph_yaml

app = Flask(
    __name__,
    static_folder="web/static",
    static_url_path="/static",
    template_folder="web/static",
)

# Global graph registry (loaded graphs)
loaded_graphs: Dict[str, StateGraph] = {}


def find_graph_files() -> List[Dict[str, str]]:
    """Find all graph YAML/JSON files in common directories."""
    graph_files = []
    scan_dirs = [
        Path.cwd() / "graphs",
        Path("graphs"),
        Path("/home/aaugus11/Documents/mcp-client-example/graphs"),
    ]

    for dir_path in scan_dirs:
        if dir_path.exists() and dir_path.is_dir():
            for ext in ["*.yaml", "*.yml", "*.json"]:
                for file_path in sorted(dir_path.glob(ext)):
                    graph_files.append(
                        {
                            "path": str(file_path),
                            "name": file_path.name,
                            "format": "yaml" if ext.startswith("*.yam") else "json",
                        }
                    )

    return graph_files


def load_graph_from_file(file_path: str) -> StateGraph:
    """Load a graph from YAML or JSON file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Graph file not found: {file_path}")

    # Determine format
    if path.suffix in [".yaml", ".yml"]:
        data = import_graph_yaml(str(path))
    elif path.suffix == ".json":
        data = import_graph_json(str(path))
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    return _create_graph_from_data(data, path.stem)


def load_graph_from_stream(file_stream, filename: str) -> StateGraph:
    """Load a graph directly from a file stream (no disk save needed)."""
    import yaml
    import json

    # Determine format from filename
    if filename.lower().endswith((".yaml", ".yml")):
        data = yaml.safe_load(file_stream)
    elif filename.lower().endswith(".json"):
        data = json.load(file_stream)
    else:
        raise ValueError(f"Unsupported file format: {filename}")

    return _create_graph_from_data(data, Path(filename).stem)


def _create_graph_from_data(data: Dict[str, Any], default_graph_id: str) -> StateGraph:
    """Create a StateGraph from parsed data."""
    # Create graph and populate
    graph_id = data.get("graph_id", default_graph_id)
    g = StateGraph(graph_id)

    # Add nodes
    for node_id, node_data in data.get("nodes", {}).items():
        g.add_node(
            node_id=node_id,
            node_type=node_data.get("node_type") or node_data.get("type", "action"),
            label=node_data.get("label") or node_data.get("name"),
            phase=node_data.get("phase"),
            tool=node_data.get("tool"),
            properties=node_data.get("properties"),
        )

    # Add edges
    for edge in data.get("edges", []):
        g.add_edge(
            from_node=edge.get("from") or edge.get("parent"),
            to_node=edge.get("to") or edge.get("child"),
            order=edge.get("order", 0),
            condition=edge.get("condition"),
            properties=edge.get("properties"),
        )

    return g


@app.route("/")
def index():
    """Serve main visualization page."""
    return render_template("index.html")


@app.route("/api/graphs")
def list_graphs():
    """List all available graph files."""
    files = find_graph_files()
    return jsonify({"graphs": files})


@app.route("/api/load-file", methods=["POST"])
def load_file():
    """Load a graph from an uploaded file."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Check file extension
        if not file.filename.lower().endswith((".yaml", ".yml", ".json")):
            return jsonify({"error": "File must be .yaml, .yml, or .json"}), 400

        filename = secure_filename(file.filename)
        
        # Load directly from stream
        print(f"Loading graph from uploaded file: {filename}")
        g = load_graph_from_stream(file.stream, filename)
        print(f"Successfully loaded graph: {g.graph_id} with {g.graph.number_of_nodes()} nodes")

        # Store in loaded graphs with a unique key
        graph_key = f"uploaded_{filename}"
        loaded_graphs[graph_key] = g

        # Convert to visualization format
        nodes = []
        for node_id in g.graph.nodes():
            node_data = g.graph.nodes[node_id]
            nodes.append(
                {
                    "id": node_id,
                    "label": node_data.get("label", node_id),
                    "type": node_data.get("node_type", "action"),
                    "phase": node_data.get("phase"),
                    "tool": node_data.get("tool"),
                    "properties": node_data.get("properties", {}),
                }
            )

        edges = []
        for from_node, to_node, attrs in g.graph.edges(data=True):
            edges.append(
                {
                    "from": from_node,
                    "to": to_node,
                    "order": attrs.get("order", 0),
                    "condition": attrs.get("condition"),
                }
            )

        stats = g.get_graph_info()

        return jsonify(
            {
                "graph_id": g.graph_id,
                "filename": filename,
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "total_nodes": stats["num_nodes"],
                    "total_edges": stats["num_edges"],
                    "node_types": stats["node_types"],
                    "phases": stats["phases"],
                    "decision_points": stats["decision_points"],
                    "loops": stats["loops"],
                },
            }
        )

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error loading file: {error_msg}")
        print(traceback.format_exc())
        return jsonify({"error": error_msg}), 500


@app.route("/api/graph/<graph_name>")
def get_graph(graph_name: str):
    """Load and return graph data for visualization."""
    try:
        # Find the graph file
        files = find_graph_files()
        graph_file = None
        for f in files:
            if f["name"] == graph_name or f["name"].startswith(graph_name):
                graph_file = f
                break

        if not graph_file:
            return jsonify({"error": f"Graph '{graph_name}' not found"}), 404

        # Load graph if not already loaded
        if graph_file["path"] not in loaded_graphs:
            loaded_graphs[graph_file["path"]] = load_graph_from_file(graph_file["path"])

        g = loaded_graphs[graph_file["path"]]

        # Convert to visualization format
        nodes = []
        for node_id in g.graph.nodes():
            node_data = g.graph.nodes[node_id]
            nodes.append(
                {
                    "id": node_id,
                    "label": node_data.get("label", node_id),
                    "type": node_data.get("node_type", "action"),
                    "phase": node_data.get("phase"),
                    "tool": node_data.get("tool"),
                    "properties": node_data.get("properties", {}),
                }
            )

        edges = []
        for from_node, to_node, attrs in g.graph.edges(data=True):
            edges.append(
                {
                    "from": from_node,
                    "to": to_node,
                    "order": attrs.get("order", 0),
                    "condition": attrs.get("condition"),
                }
            )

        stats = g.get_graph_info()

        return jsonify(
            {
                "graph_id": g.graph_id,
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "total_nodes": stats["num_nodes"],
                    "total_edges": stats["num_edges"],
                    "node_types": stats["node_types"],
                    "phases": stats["phases"],
                    "decision_points": stats["decision_points"],
                    "loops": stats["loops"],
                },
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/graph/<graph_name>/node/<node_id>")
def get_node(graph_name: str, node_id: str):
    """Get specific node details."""
    try:
        files = find_graph_files()
        graph_file = None
        for f in files:
            if f["name"] == graph_name or f["name"].startswith(graph_name):
                graph_file = f
                break

        if not graph_file:
            return jsonify({"error": "Graph not found"}), 404

        if graph_file["path"] not in loaded_graphs:
            loaded_graphs[graph_file["path"]] = load_graph_from_file(graph_file["path"])

        g = loaded_graphs[graph_file["path"]]

        if node_id not in g.graph.nodes():
            return jsonify({"error": "Node not found"}), 404

        node_data = dict(g.graph.nodes[node_id])
        node_data["node_id"] = node_id

        # Get edges
        incoming = []
        for from_n, to_n, attrs in g.graph.in_edges(node_id, data=True):
            incoming.append(
                {
                    "from": from_n,
                    "to": to_n,
                    "order": attrs.get("order", 0),
                    "condition": attrs.get("condition"),
                }
            )

        outgoing = []
        for from_n, to_n, attrs in g.graph.out_edges(node_id, data=True):
            outgoing.append(
                {
                    "from": from_n,
                    "to": to_n,
                    "order": attrs.get("order", 0),
                    "condition": attrs.get("condition"),
                }
            )

        return jsonify(
            {
                "node": node_data,
                "incoming": incoming,
                "outgoing": outgoing,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🌐 NETWORKX GRAPH VISUALIZATION SERVER")
    print("=" * 60)
    print("\n✓ Starting Flask server...")
    print("✓ Open your browser to: http://localhost:5000")
    print("✓ Press Ctrl+C to stop\n")

    try:
        app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nServer stopped.")

