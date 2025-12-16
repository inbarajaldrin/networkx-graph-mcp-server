## NetworkX Graph MCP Server

State/decision graph MCP server using NetworkX. Supports directed graphs (cycles allowed), explicit edge ordering, conditional branches, import/export, and visualization.

### Setup
```bash
cd ~/Documents/networkx-graph-mcp-server
uv venv
source .venv/bin/activate
uv sync
```

### MCP client config (example)

Add to your `mcp_config.json`:

```json
{
  "mcpServers": {
    "networkx-graph": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "~/Documents/networkx-graph-mcp-server/.venv/bin/python",
      "args": ["-m", "networkx_graph"]
    }
  }
}
```

### Tools (summary)
- Graph: create_state_graph, delete_state_graph, list_state_graphs, get_state_graph_info
- Nodes: add_node, update_node, remove_node, get_node, list_nodes
- Edges: add_edge, remove_edge, get_edges, set_edge_order, set_edge_condition, get_node_edges
- Bulk: bulk_add_nodes, bulk_add_edges
- Export/Visualize: export_graph (yaml/json), import_graph, visualize_graph (PNG)
- Analysis: validate_graph (warnings only, cycles allowed), get_graph_stats, find_path

### Web Visualization

Interactive web browser for visualizing graphs:

```bash
uv run app.py
```

Then open your browser to: http://localhost:5000

**Features:**
- Load YAML/JSON graph files via file upload
- Interactive graph visualization with zoom, pan, and node selection
- View node details, statistics, and graph structure
- Color-coded nodes by type (action, decision, verification, loop, success, failure)