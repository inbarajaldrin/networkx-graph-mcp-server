#!/usr/bin/env python3
"""NetworkX Graph MCP Server - State/Decision Graphs."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .state_graph import StateGraph
from .visualization import (
    export_graph_json,
    export_graph_yaml,
    import_graph_json,
    import_graph_yaml,
    visualize_graph,
)

# Global graphs registry
graphs: Dict[str, StateGraph] = {}


class GraphMCPServer:
    """MCP server for state/decision graphs."""

    def __init__(self) -> None:
        self.running = True
        self.initialized = False

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        if method == "initialize":
            self.initialized = True
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "networkx-graph-mcp-server",
                        "version": "0.1.0",
                    },
                },
            }

        # Prompts: return empty to satisfy clients expecting this
        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "prompts": []
                },
            }

        if method == "prompts/get":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32602,
                    "message": "Prompt not found",
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": self._get_tools(),
                },
            }

        if method == "tools/call":
            try:
                result = await self._call_tool(params)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result),
                            }
                        ]
                    },
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}",
                    },
                }

        return None

    def _get_tools(self) -> List[Dict[str, Any]]:
        return [
            # Graph management
            {
                "name": "create_state_graph",
                "description": "Create a new state/decision graph (directed, cycles allowed).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                    },
                    "required": ["graph_id"],
                },
            },
            {
                "name": "delete_state_graph",
                "description": "Delete a state graph.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                    },
                    "required": ["graph_id"],
                },
            },
            {
                "name": "list_state_graphs",
                "description": "List all available state graph files on disk (memory resets each session, so this scans for YAML/JSON files in graphs directories). Returns file paths that can be imported.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Optional directory to scan (defaults to common graph directories)",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_state_graph_info",
                "description": "Get graph metadata and stats.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"graph_id": {"type": "string"}},
                    "required": ["graph_id"],
                },
            },
            # Nodes
            {
                "name": "add_node",
                "description": "Add a node (action/decision/verification/loop/success/failure).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "node_id": {"type": "string"},
                        "node_type": {
                            "type": "string",
                            "enum": ["action", "decision", "verification", "loop", "success", "failure"],
                        },
                        "label": {"type": "string"},
                        "phase": {"type": "integer"},
                        "tool": {"type": "string"},
                        "properties": {"type": "object"},
                    },
                    "required": ["graph_id", "node_id", "node_type"],
                },
            },
            {
                "name": "update_node",
                "description": "Update node properties (label, phase, tool, properties).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "node_id": {"type": "string"},
                        "label": {"type": "string"},
                        "phase": {"type": "integer"},
                        "tool": {"type": "string"},
                        "properties": {"type": "object"},
                    },
                    "required": ["graph_id", "node_id"],
                },
            },
            {
                "name": "remove_node",
                "description": "Remove a node.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "node_id": {"type": "string"},
                    },
                    "required": ["graph_id", "node_id"],
                },
            },
            {
                "name": "get_node",
                "description": "Get node details.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "node_id": {"type": "string"},
                    },
                    "required": ["graph_id", "node_id"],
                },
            },
            {
                "name": "list_nodes",
                "description": "List all nodes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"graph_id": {"type": "string"}},
                    "required": ["graph_id"],
                },
            },
            # Edges
            {
                "name": "add_edge",
                "description": "Add an edge with order and optional condition.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                        "order": {"type": "integer", "default": 0},
                        "condition": {"type": "string"},
                        "properties": {"type": "object"},
                    },
                    "required": ["graph_id", "from", "to"],
                },
            },
            {
                "name": "remove_edge",
                "description": "Remove an edge.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                    },
                    "required": ["graph_id", "from", "to"],
                },
            },
            {
                "name": "get_edges",
                "description": "Get edges (optionally filter by node).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "node_id": {"type": "string"},
                    },
                    "required": ["graph_id"],
                },
            },
            {
                "name": "set_edge_order",
                "description": "Set execution order for an edge.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                        "order": {"type": "integer"},
                    },
                    "required": ["graph_id", "from", "to", "order"],
                },
            },
            {
                "name": "set_edge_condition",
                "description": "Set condition label for an edge.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                        "condition": {"type": "string"},
                    },
                    "required": ["graph_id", "from", "to"],
                },
            },
            {
                "name": "get_node_edges",
                "description": "Get incoming/outgoing edges for a node.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "node_id": {"type": "string"},
                    },
                    "required": ["graph_id", "node_id"],
                },
            },
            # Bulk
            {
                "name": "bulk_add_nodes",
                "description": "Add multiple nodes at once (parents before children).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "node_id": {"type": "string"},
                                    "node_type": {
                                        "type": "string",
                                        "enum": ["action", "decision", "verification", "loop", "success", "failure"],
                                    },
                                    "label": {"type": "string"},
                                    "phase": {"type": "integer"},
                                    "tool": {"type": "string"},
                                    "properties": {"type": "object"},
                                },
                                "required": ["node_id", "node_type"],
                            },
                        },
                    },
                    "required": ["graph_id", "nodes"],
                },
            },
            {
                "name": "bulk_add_edges",
                "description": "Add multiple edges at once (with order/condition).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "edges": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "from": {"type": "string"},
                                    "to": {"type": "string"},
                                    "order": {"type": "integer", "default": 0},
                                    "condition": {"type": "string"},
                                    "properties": {"type": "object"},
                                },
                                "required": ["from", "to"],
                            },
                        },
                    },
                    "required": ["graph_id", "edges"],
                },
            },
            # Export / Import / Visualize
            {
                "name": "export_graph",
                "description": "Export graph to YAML or JSON file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "format": {"type": "string", "enum": ["yaml", "json"], "default": "yaml"},
                        "output_dir": {"type": "string", "default": "graphs"},
                        "filename": {"type": "string"},
                    },
                    "required": ["graph_id"],
                },
            },
            {
                "name": "import_graph",
                "description": "Import graph from YAML or JSON file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "path": {"type": "string"},
                    },
                    "required": ["graph_id", "path"],
                },
            },
            {
                "name": "visualize_graph",
                "description": "Render graph to PNG file (saves to disk, not base64).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "layout": {
                            "type": "string",
                            "enum": ["spring", "circular", "kamada_kawai"],
                            "default": "spring",
                        },
                        "output_dir": {"type": "string", "default": "graphs"},
                        "filename": {"type": "string"},
                        "dpi": {"type": "integer", "default": 90},
                    },
                    "required": ["graph_id"],
                },
            },
            # Analysis / validation
            {
                "name": "validate_graph",
                "description": "Validate graph structure (cycles allowed, warnings only).",
                "inputSchema": {
                    "type": "object",
                    "properties": {"graph_id": {"type": "string"}},
                    "required": ["graph_id"],
                },
            },
            {
                "name": "get_graph_stats",
                "description": "Get statistics: node counts by type, edges, phases, decision points, loops.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"graph_id": {"type": "string"}},
                    "required": ["graph_id"],
                },
            },
            {
                "name": "find_path",
                "description": "Find shortest path between two nodes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                    },
                    "required": ["graph_id", "from", "to"],
                },
            },
            {
                "name": "get_execution_sequence",
                "description": "Get nodes in execution order from a start node, following edges by order attribute. Stops at first decision node by default. Returns sequence of nodes with their details.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "graph_id": {"type": "string"},
                        "from": {"type": "string", "description": "Starting node ID"},
                        "until_decision": {
                            "type": "boolean",
                            "default": True,
                            "description": "Stop at first decision node (default: true)",
                        },
                    },
                    "required": ["graph_id", "from"],
                },
            },
        ]

    async def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "create_state_graph":
            graph_id = args["graph_id"]
            if graph_id in graphs:
                raise ValueError(f"Graph '{graph_id}' already exists")
            g = StateGraph(graph_id)
            graphs[graph_id] = g
            return g.create_graph()

        elif tool_name == "delete_state_graph":
            graph_id = args["graph_id"]
            if graph_id in graphs:
                del graphs[graph_id]
            return {"graph_id": graph_id, "status": "deleted"}

        elif tool_name == "list_state_graphs":
            # Scan for available graph files (memory resets each session)
            available_files = []
            scan_dirs = []
            
            # Use provided directory or scan common locations
            if "directory" in args and args["directory"]:
                scan_dirs = [Path(args["directory"])]
            else:
                # Default: scan common graph directories
                scan_dirs = [
                    Path("/home/aaugus11/Documents/mcp-client-example/graphs"),
                    Path.cwd() / "graphs",
                    Path("graphs"),
                ]
            
            for dir_path in scan_dirs:
                if dir_path.exists() and dir_path.is_dir():
                    for file_path in sorted(dir_path.glob("*.yaml")):
                        available_files.append(str(file_path))
                    for file_path in sorted(dir_path.glob("*.yml")):
                        available_files.append(str(file_path))
                    for file_path in sorted(dir_path.glob("*.json")):
                        available_files.append(str(file_path))
            
            # Also show what's currently in memory (usually empty after restart)
            in_memory = list(graphs.keys())
            
            return {
                "available_files": available_files,
                "graphs_in_memory": in_memory,
                "note": "Memory resets each session. Use 'import_graph' to load a file into memory for use.",
            }

        elif tool_name == "get_state_graph_info":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.get_graph_info()

        # Nodes
        elif tool_name == "add_node":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.add_node(
                node_id=args["node_id"],
                node_type=args["node_type"],
                label=args.get("label"),
                phase=args.get("phase"),
                tool=args.get("tool"),
                properties=args.get("properties"),
            )

        elif tool_name == "update_node":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.update_node(
                node_id=args["node_id"],
                label=args.get("label"),
                phase=args.get("phase"),
                tool=args.get("tool"),
                properties=args.get("properties"),
            )

        elif tool_name == "remove_node":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.remove_node(args["node_id"])

        elif tool_name == "get_node":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.get_node(args["node_id"])

        elif tool_name == "list_nodes":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return {"nodes": g.list_nodes()}

        # Edges
        elif tool_name == "add_edge":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.add_edge(
                from_node=args["from"],
                to_node=args["to"],
                order=args.get("order", 0),
                condition=args.get("condition"),
                properties=args.get("properties"),
            )

        elif tool_name == "remove_edge":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.remove_edge(args["from"], args["to"])

        elif tool_name == "get_edges":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            node_id = args.get("node_id")
            return {"edges": g.get_edges(node_id)}

        elif tool_name == "set_edge_order":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.set_edge_order(args["from"], args["to"], args["order"])

        elif tool_name == "set_edge_condition":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.set_edge_condition(args["from"], args["to"], args.get("condition"))

        elif tool_name == "get_node_edges":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.get_node_edges(args["node_id"])

        # Bulk
        elif tool_name == "bulk_add_nodes":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            created = []
            for node in args["nodes"]:
                created.append(
                    g.add_node(
                        node_id=node["node_id"],
                        node_type=node["node_type"],
                        label=node.get("label"),
                        phase=node.get("phase"),
                        tool=node.get("tool"),
                        properties=node.get("properties"),
                    )
                )
            return {"created": created}

        elif tool_name == "bulk_add_edges":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            created = []
            for edge in args["edges"]:
                created.append(
                    g.add_edge(
                        from_node=edge["from"],
                        to_node=edge["to"],
                        order=edge.get("order", 0),
                        condition=edge.get("condition"),
                        properties=edge.get("properties"),
                    )
                )
            return {"created": created}

        # Export / Import / Visualization
        elif tool_name == "export_graph":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            fmt = args.get("format", "yaml")
            out_dir = args.get("output_dir", "graphs")
            filename = args.get("filename")
            if fmt == "yaml":
                fname = filename or f"{graph_id}.yaml"
                if not fname.endswith((".yaml", ".yml")):
                    fname += ".yaml"
                path = str(Path(out_dir) / fname)
                return export_graph_yaml(g.graph, graph_id, path)
            elif fmt == "json":
                fname = filename or f"{graph_id}.json"
                if not fname.endswith(".json"):
                    fname += ".json"
                path = str(Path(out_dir) / fname)
                return export_graph_json(g.graph, graph_id, path)
            else:
                raise ValueError(f"Unsupported format: {fmt}")

        elif tool_name == "import_graph":
            graph_id = args["graph_id"]
            path = args["path"]
            data: Dict[str, Any]
            if path.endswith(".yaml") or path.endswith(".yml"):
                data = import_graph_yaml(path)
            elif path.endswith(".json"):
                data = import_graph_json(path)
            else:
                raise ValueError("Unsupported import format; use .yaml/.yml or .json")

            # Create graph and populate
            g = StateGraph(graph_id)
            graphs[graph_id] = g
            # Nodes
            for node_id, node_data in data.get("nodes", {}).items():
                g.add_node(
                    node_id=node_id,
                    node_type=node_data.get("node_type") or node_data.get("type", "action"),
                    label=node_data.get("label") or node_data.get("name"),
                    phase=node_data.get("phase"),
                    tool=node_data.get("tool"),
                    properties=node_data.get("properties"),
                )
            # Edges
            for edge in data.get("edges", []):
                g.add_edge(
                    from_node=edge.get("from") or edge.get("parent"),
                    to_node=edge.get("to") or edge.get("child"),
                    order=edge.get("order", 0),
                    condition=edge.get("condition"),
                    properties=edge.get("properties"),
                )
            return {"graph_id": graph_id, "status": "imported", "num_nodes": len(data.get("nodes", {})), "num_edges": len(data.get("edges", []))}

        elif tool_name == "visualize_graph":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return visualize_graph(
                g.graph,
                graph_id,
                layout=args.get("layout", "spring"),
                output_dir=args.get("output_dir", "graphs"),
                filename=args.get("filename"),
                dpi=args.get("dpi", 90),
            )

        # Analysis
        elif tool_name == "validate_graph":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.validate_graph()

        elif tool_name == "get_graph_stats":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return g.get_graph_info()

        elif tool_name == "find_path":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            return {"path": g.find_path(args["from"], args["to"])}

        elif tool_name == "get_execution_sequence":
            graph_id = args["graph_id"]
            g = self._get_graph(graph_id)
            until_decision = args.get("until_decision", True)
            sequence = g.get_execution_sequence(args["from"], until_decision)
            return {"sequence": sequence, "count": len(sequence)}

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _get_graph(self, graph_id: str) -> StateGraph:
        if graph_id not in graphs:
            raise ValueError(f"Graph '{graph_id}' does not exist")
        return graphs[graph_id]


async def run_server() -> None:
    server = GraphMCPServer()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    writer_transport, writer_protocol = await asyncio.get_running_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_running_loop())

    while server.running:
        line = await reader.readline()
        if not line:
            break
        try:
            request = json.loads(line.decode())
        except json.JSONDecodeError:
            continue
        response = await server.handle_request(request)
        if response is not None:
            writer.write((json.dumps(response) + "\n").encode())
            await writer.drain()


def main() -> None:
    asyncio.run(run_server())


if __name__ == "__main__":
    main()

