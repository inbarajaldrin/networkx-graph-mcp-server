"""State-transition graph management using NetworkX."""

import threading
from typing import Any, Dict, List, Optional

import networkx as nx


class StateGraph:
    """State-transition graph manager using NetworkX DiGraph (cycles allowed)."""

    def __init__(self, graph_id: str) -> None:
        self.graph_id = graph_id
        self.graph = nx.DiGraph()
        self._lock = threading.RLock()  # Thread-safe operations

    def create_graph(self) -> Dict[str, Any]:
        """Create a new empty graph."""
        with self._lock:
            return {
                "graph_id": self.graph_id,
                "status": "created",
                "num_nodes": 0,
                "num_edges": 0,
            }

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: Optional[str] = None,
        phase: Optional[int] = None,
        tool: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a node to the graph."""
        with self._lock:
            if node_id in self.graph:
                raise ValueError(f"Node '{node_id}' already exists")

            if node_type not in ["action", "decision", "verification", "loop", "success", "failure"]:
                raise ValueError(f"Invalid node type: {node_type}")

            node_attrs = {
                "node_type": node_type,
                "label": label or node_id,
                "properties": properties or {},
            }

            if phase is not None:
                node_attrs["phase"] = phase
            if tool is not None:
                node_attrs["tool"] = tool

            self.graph.add_node(node_id, **node_attrs)

            return {
                "node_id": node_id,
                "node_type": node_type,
                "status": "added",
            }

    def update_node(
        self,
        node_id: str,
        label: Optional[str] = None,
        phase: Optional[int] = None,
        tool: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update node properties."""
        with self._lock:
            if node_id not in self.graph:
                raise ValueError(f"Node '{node_id}' does not exist")

            if label is not None:
                self.graph.nodes[node_id]["label"] = label
            if phase is not None:
                self.graph.nodes[node_id]["phase"] = phase
            if tool is not None:
                self.graph.nodes[node_id]["tool"] = tool
            if properties is not None:
                existing_props = self.graph.nodes[node_id].get("properties", {})
                existing_props.update(properties)
                self.graph.nodes[node_id]["properties"] = existing_props

            return {
                "node_id": node_id,
                "status": "updated",
            }

    def remove_node(self, node_id: str) -> Dict[str, Any]:
        """Remove a node from the graph."""
        with self._lock:
            if node_id not in self.graph:
                raise ValueError(f"Node '{node_id}' does not exist")

            self.graph.remove_node(node_id)

            return {
                "node_id": node_id,
                "status": "removed",
            }

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        order: int = 0,
        condition: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add an edge to the graph."""
        with self._lock:
            if from_node not in self.graph:
                raise ValueError(f"Source node '{from_node}' does not exist")
            if to_node not in self.graph:
                raise ValueError(f"Target node '{to_node}' does not exist")

            edge_attrs = {
                "order": order,
                "properties": properties or {},
            }

            if condition is not None:
                edge_attrs["condition"] = condition

            self.graph.add_edge(from_node, to_node, **edge_attrs)

            return {
                "from": from_node,
                "to": to_node,
                "status": "added",
            }

    def remove_edge(self, from_node: str, to_node: str) -> Dict[str, Any]:
        """Remove an edge from the graph."""
        with self._lock:
            if not self.graph.has_edge(from_node, to_node):
                raise ValueError(f"Edge from '{from_node}' to '{to_node}' does not exist")

            self.graph.remove_edge(from_node, to_node)

            return {
                "from": from_node,
                "to": to_node,
                "status": "removed",
            }

    def set_edge_order(self, from_node: str, to_node: str, order: int) -> Dict[str, Any]:
        """Set execution order for an edge."""
        with self._lock:
            if not self.graph.has_edge(from_node, to_node):
                raise ValueError(f"Edge from '{from_node}' to '{to_node}' does not exist")

            self.graph.edges[from_node, to_node]["order"] = order

            return {
                "from": from_node,
                "to": to_node,
                "order": order,
                "status": "updated",
            }

    def set_edge_condition(
        self, from_node: str, to_node: str, condition: Optional[str]
    ) -> Dict[str, Any]:
        """Set condition label for an edge."""
        with self._lock:
            if not self.graph.has_edge(from_node, to_node):
                raise ValueError(f"Edge from '{from_node}' to '{to_node}' does not exist")

            if condition is None:
                if "condition" in self.graph.edges[from_node, to_node]:
                    del self.graph.edges[from_node, to_node]["condition"]
            else:
                self.graph.edges[from_node, to_node]["condition"] = condition

            return {
                "from": from_node,
                "to": to_node,
                "condition": condition,
                "status": "updated",
            }

    def get_graph_info(self) -> Dict[str, Any]:
        """Get information about the graph."""
        with self._lock:
            node_types = {}
            phases = set()
            decision_count = 0
            loop_count = 0

            for node in self.graph.nodes():
                node_data = self.graph.nodes[node]
                node_type = node_data.get("node_type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1

                if "phase" in node_data:
                    phases.add(node_data["phase"])

                if node_type == "decision":
                    decision_count += 1
                elif node_type == "loop":
                    loop_count += 1

            return {
                "graph_id": self.graph_id,
                "num_nodes": self.graph.number_of_nodes(),
                "num_edges": self.graph.number_of_edges(),
                "node_types": node_types,
                "phases": sorted(list(phases)) if phases else [],
                "decision_points": decision_count,
                "loops": loop_count,
            }

    def validate_graph(self) -> Dict[str, Any]:
        """Validate graph structure (cycles allowed)."""
        with self._lock:
            warnings: List[str] = []

            isolated = list(nx.isolates(self.graph))
            if isolated:
                warnings.append(f"Graph has isolated nodes: {isolated}")

            entry_points = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
            if len(entry_points) > 1:
                warnings.append(f"Graph has multiple entry points: {entry_points}")

            try:
                cycles = list(nx.simple_cycles(self.graph))
                if cycles:
                    warnings.append(
                        f"Graph contains {len(cycles)} cycle(s) (allowed in state-transition graphs)"
                    )
            except Exception:
                pass

            return {
                "valid": True,
                "warnings": warnings,
            }

    def get_node(self, node_id: str) -> Dict[str, Any]:
        """Get node details."""
        with self._lock:
            if node_id not in self.graph:
                raise ValueError(f"Node '{node_id}' does not exist")
            data = dict(self.graph.nodes[node_id])
            data["node_id"] = node_id
            return data

    def list_nodes(self) -> List[Dict[str, Any]]:
        """List all nodes."""
        with self._lock:
            nodes = []
            for node_id in self.graph.nodes():
                node_data = dict(self.graph.nodes[node_id])
                node_data["node_id"] = node_id
                nodes.append(node_data)
            return nodes

    def get_edges(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all edges, optionally filtered by node (incoming/outgoing)."""
        with self._lock:
            edges = []
            if node_id is not None:
                if node_id not in self.graph:
                    raise ValueError(f"Node '{node_id}' does not exist")
                for from_node, to_node, attrs in self.graph.in_edges(node_id, data=True):
                    edge_data = dict(attrs)
                    edge_data["from"] = from_node
                    edge_data["to"] = to_node
                    edges.append(edge_data)
                for from_node, to_node, attrs in self.graph.out_edges(node_id, data=True):
                    edge_data = dict(attrs)
                    edge_data["from"] = from_node
                    edge_data["to"] = to_node
                    edges.append(edge_data)
            else:
                for from_node, to_node, attrs in self.graph.edges(data=True):
                    edge_data = dict(attrs)
                    edge_data["from"] = from_node
                    edge_data["to"] = to_node
                    edges.append(edge_data)
            return edges

    def get_node_edges(self, node_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get incoming and outgoing edges for a node."""
        with self._lock:
            if node_id not in self.graph:
                raise ValueError(f"Node '{node_id}' does not exist")

            incoming = []
            for from_node, to_node, attrs in self.graph.in_edges(node_id, data=True):
                edge_data = dict(attrs)
                edge_data["from"] = from_node
                edge_data["to"] = to_node
                incoming.append(edge_data)

            outgoing = []
            for from_node, to_node, attrs in self.graph.out_edges(node_id, data=True):
                edge_data = dict(attrs)
                edge_data["from"] = from_node
                edge_data["to"] = to_node
                outgoing.append(edge_data)

            return {
                "node_id": node_id,
                "incoming": incoming,
                "outgoing": outgoing,
            }

    def find_path(self, from_node: str, to_node: str) -> List[str]:
        """Find a path between two nodes (shortest path)."""
        with self._lock:
            if from_node not in self.graph:
                raise ValueError(f"Source node '{from_node}' does not exist")
            if to_node not in self.graph:
                raise ValueError(f"Target node '{to_node}' does not exist")

            try:
                path = nx.shortest_path(self.graph, from_node, to_node)
                return path
            except nx.NetworkXNoPath:
                return []

    def get_execution_sequence(self, from_node: str, until_decision: bool = True) -> List[Dict[str, Any]]:
        """Get nodes in execution order from a start node, following edges by order attribute.
        
        Args:
            from_node: Starting node ID
            until_decision: If True, stop at first decision node; if False, continue until no more edges
            
        Returns:
            List of node dictionaries with execution order information
        """
        with self._lock:
            if from_node not in self.graph:
                raise ValueError(f"Source node '{from_node}' does not exist")
            
            sequence = []
            visited = set()
            current = from_node
            
            while current and current not in visited:
                visited.add(current)
                node_data = dict(self.graph.nodes[current])
                node_data["node_id"] = current
                sequence.append(node_data)
                
                # Stop if we hit a decision node and until_decision is True
                if until_decision and node_data.get("node_type") == "decision":
                    break
                
                # Get outgoing edges sorted by order
                outgoing = []
                for from_n, to_n, attrs in self.graph.out_edges(current, data=True):
                    edge_data = dict(attrs)
                    edge_data["from"] = from_n
                    edge_data["to"] = to_n
                    outgoing.append(edge_data)
                
                if not outgoing:
                    break
                
                # Sort by order, then take the first one (lowest order)
                outgoing.sort(key=lambda e: e.get("order", 0))
                next_edge = outgoing[0]
                current = next_edge["to"]
            
            return sequence

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: Optional[str] = None,
        phase: Optional[int] = None,
        tool: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a node to the graph.

        Args:
            node_id: Unique identifier for the node
            node_type: Type of node (action, decision, verification, loop, success, failure)
            label: Human-readable label
            phase: Optional phase number
            tool: Optional tool name for actions
            properties: Additional custom properties

        Returns:
            Dictionary with node creation info
        """
        with self._lock:
            if node_id in self.graph:
                raise ValueError(f"Node '{node_id}' already exists")

            if node_type not in ["action", "decision", "verification", "loop", "success", "failure"]:
                raise ValueError(f"Invalid node type: {node_type}")

            # Set node attributes
            node_attrs = {
                "node_type": node_type,
                "label": label or node_id,
                "properties": properties or {},
            }

            if phase is not None:
                node_attrs["phase"] = phase
            if tool is not None:
                node_attrs["tool"] = tool

            self.graph.add_node(node_id, **node_attrs)

            return {
                "node_id": node_id,
                "node_type": node_type,
                "status": "added",
            }

    def update_node(
        self,
        node_id: str,
        label: Optional[str] = None,
        phase: Optional[int] = None,
        tool: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update node properties.

        Args:
            node_id: Node ID to update
            label: New label
            phase: New phase
            tool: New tool name
            properties: Properties to update (merged with existing)

        Returns:
            Dictionary with update info
        """
        with self._lock:
            if node_id not in self.graph:
                raise ValueError(f"Node '{node_id}' does not exist")

            if label is not None:
                self.graph.nodes[node_id]["label"] = label
            if phase is not None:
                self.graph.nodes[node_id]["phase"] = phase
            if tool is not None:
                self.graph.nodes[node_id]["tool"] = tool
            if properties is not None:
                existing_props = self.graph.nodes[node_id].get("properties", {})
                existing_props.update(properties)
                self.graph.nodes[node_id]["properties"] = existing_props

            return {
                "node_id": node_id,
                "status": "updated",
            }

    def remove_node(self, node_id: str) -> Dict[str, Any]:
        """Remove a node from the graph.

        Args:
            node_id: Node ID to remove

        Returns:
            Dictionary with removal info
        """
        with self._lock:
            if node_id not in self.graph:
                raise ValueError(f"Node '{node_id}' does not exist")

            self.graph.remove_node(node_id)

            return {
                "node_id": node_id,
                "status": "removed",
            }

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        order: int = 0,
        condition: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add an edge to the graph.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            order: Execution order (for sequence execution from same parent)
            condition: Optional condition label (for decision branches)
            properties: Additional edge properties

        Returns:
            Dictionary with edge creation info
        """
        with self._lock:
            if from_node not in self.graph:
                raise ValueError(f"Source node '{from_node}' does not exist")
            if to_node not in self.graph:
                raise ValueError(f"Target node '{to_node}' does not exist")

            edge_attrs = {
                "order": order,
                "properties": properties or {},
            }

            if condition is not None:
                edge_attrs["condition"] = condition

            self.graph.add_edge(from_node, to_node, **edge_attrs)

            return {
                "from": from_node,
                "to": to_node,
                "status": "added",
            }

    def remove_edge(self, from_node: str, to_node: str) -> Dict[str, Any]:
        """Remove an edge from the graph.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            Dictionary with edge removal info
        """
        with self._lock:
            if not self.graph.has_edge(from_node, to_node):
                raise ValueError(f"Edge from '{from_node}' to '{to_node}' does not exist")

            self.graph.remove_edge(from_node, to_node)

            return {
                "from": from_node,
                "to": to_node,
                "status": "removed",
            }

    def set_edge_order(self, from_node: str, to_node: str, order: int) -> Dict[str, Any]:
        """Set execution order for an edge.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            order: New order value

        Returns:
            Dictionary with update info
        """
        with self._lock:
            if not self.graph.has_edge(from_node, to_node):
                raise ValueError(f"Edge from '{from_node}' to '{to_node}' does not exist")

            self.graph.edges[from_node, to_node]["order"] = order

            return {
                "from": from_node,
                "to": to_node,
                "order": order,
                "status": "updated",
            }

    def set_edge_condition(self, from_node: str, to_node: str, condition: Optional[str]) -> Dict[str, Any]:
        """Set condition label for an edge.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            condition: Condition label (or None to remove)

        Returns:
            Dictionary with update info
        """
        with self._lock:
            if not self.graph.has_edge(from_node, to_node):
                raise ValueError(f"Edge from '{from_node}' to '{to_node}' does not exist")

            if condition is None:
                if "condition" in self.graph.edges[from_node, to_node]:
                    del self.graph.edges[from_node, to_node]["condition"]
            else:
                self.graph.edges[from_node, to_node]["condition"] = condition

            return {
                "from": from_node,
                "to": to_node,
                "condition": condition,
                "status": "updated",
            }

    def get_graph_info(self) -> Dict[str, Any]:
        """Get information about the graph.

        Returns:
            Dictionary with graph information
        """
        with self._lock:
            node_types = {}
            phases = set()
            decision_count = 0
            loop_count = 0

            for node in self.graph.nodes():
                node_data = self.graph.nodes[node]
                node_type = node_data.get("node_type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1

                if "phase" in node_data:
                    phases.add(node_data["phase"])

                if node_type == "decision":
                    decision_count += 1
                elif node_type == "loop":
                    loop_count += 1

            return {
                "graph_id": self.graph_id,
                "num_nodes": self.graph.number_of_nodes(),
                "num_edges": self.graph.number_of_edges(),
                "node_types": node_types,
                "phases": sorted(list(phases)) if phases else [],
                "decision_points": decision_count,
                "loops": loop_count,
            }

    def validate_graph(self) -> Dict[str, Any]:
        """Validate graph structure.

        Returns:
            Dictionary with validation results (warnings only, cycles allowed)
        """
        with self._lock:
            warnings: List[str] = []

            # Check for isolated nodes
            isolated = list(nx.isolates(self.graph))
            if isolated:
                warnings.append(f"Graph has isolated nodes: {isolated}")

            # Check for nodes with no incoming edges (potential entry points)
            entry_points = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
            if len(entry_points) > 1:
                warnings.append(f"Graph has multiple entry points: {entry_points}")

            # Check for cycles (informational, not an error)
            try:
                cycles = list(nx.simple_cycles(self.graph))
                if cycles:
                    warnings.append(f"Graph contains {len(cycles)} cycle(s) (allowed in state-transition graphs)")
            except Exception:
                pass

            return {
                "valid": True,  # Always valid, cycles allowed
                "warnings": warnings,
            }

    def get_node(self, node_id: str) -> Dict[str, Any]:
        """Get node details.

        Args:
            node_id: Node ID

        Returns:
            Dictionary with node data
        """
        with self._lock:
            if node_id not in self.graph:
                raise ValueError(f"Node '{node_id}' does not exist")

            return dict(self.graph.nodes[node_id])

    def list_nodes(self) -> List[Dict[str, Any]]:
        """List all nodes in the graph.

        Returns:
            List of node dictionaries
        """
        with self._lock:
            nodes = []
            for node_id in self.graph.nodes():
                node_data = dict(self.graph.nodes[node_id])
                node_data["node_id"] = node_id
                nodes.append(node_data)
            return nodes

    def get_edges(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all edges, optionally filtered by node.

        Args:
            node_id: Optional node ID to filter edges (incoming and outgoing)

        Returns:
            List of edge dictionaries
        """
        with self._lock:
            edges = []
            if node_id is not None:
                if node_id not in self.graph:
                    raise ValueError(f"Node '{node_id}' does not exist")
                # Get both incoming and outgoing edges
                for from_node, to_node, attrs in self.graph.in_edges(node_id, data=True):
                    edge_data = dict(attrs)
                    edge_data["from"] = from_node
                    edge_data["to"] = to_node
                    edges.append(edge_data)
                for from_node, to_node, attrs in self.graph.out_edges(node_id, data=True):
                    edge_data = dict(attrs)
                    edge_data["from"] = from_node
                    edge_data["to"] = to_node
                    edges.append(edge_data)
            else:
                for from_node, to_node, attrs in self.graph.edges(data=True):
                    edge_data = dict(attrs)
                    edge_data["from"] = from_node
                    edge_data["to"] = to_node
                    edges.append(edge_data)
            return edges

    def get_node_edges(self, node_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get incoming and outgoing edges for a node.

        Args:
            node_id: Node ID

        Returns:
            Dictionary with 'incoming' and 'outgoing' edge lists
        """
        with self._lock:
            if node_id not in self.graph:
                raise ValueError(f"Node '{node_id}' does not exist")

            incoming = []
            for from_node, to_node, attrs in self.graph.in_edges(node_id, data=True):
                edge_data = dict(attrs)
                edge_data["from"] = from_node
                edge_data["to"] = to_node
                incoming.append(edge_data)

            outgoing = []
            for from_node, to_node, attrs in self.graph.out_edges(node_id, data=True):
                edge_data = dict(attrs)
                edge_data["from"] = from_node
                edge_data["to"] = to_node
                outgoing.append(edge_data)

            return {
                "node_id": node_id,
                "incoming": incoming,
                "outgoing": outgoing,
            }

    def find_path(self, from_node: str, to_node: str) -> List[str]:
        """Find a path between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            List of node IDs in the path, or empty list if no path exists
        """
        with self._lock:
            if from_node not in self.graph:
                raise ValueError(f"Source node '{from_node}' does not exist")
            if to_node not in self.graph:
                raise ValueError(f"Target node '{to_node}' does not exist")

            try:
                path = nx.shortest_path(self.graph, from_node, to_node)
                return path
            except nx.NetworkXNoPath:
                return []

