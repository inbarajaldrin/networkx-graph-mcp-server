let network = null;
let selectedNodeData = null;
let currentGraphData = null;

// File upload handler
document.getElementById('fileInput').addEventListener('change', async function(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        document.getElementById('fileName').textContent = `Loading ${file.name}...`;
        
        const response = await fetch('/api/load-file', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to load file');
        }
        
        const data = await response.json();
        currentGraphData = data;
        
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('graphInfo').textContent = `${data.stats.total_nodes} nodes • ${data.stats.total_edges} edges`;
        
        renderGraph(data);
        
    } catch (error) {
        console.error('Error loading file:', error);
        const errorMsg = error.message || 'Unknown error occurred';
        document.getElementById('fileName').textContent = `Error: ${errorMsg}`;
        document.getElementById('graphInfo').textContent = 'Error loading graph';
        alert(`Failed to load file: ${errorMsg}\n\nCheck the browser console for details.`);
    }
});

async function loadGraph(graphName) {
    try {
        const response = await fetch(`/api/graph/${graphName}`);
        if (!response.ok) {
            throw new Error('Failed to load graph');
        }
        
        const data = await response.json();
        currentGraphData = data;
        
        document.getElementById('graphInfo').textContent = `${data.stats.total_nodes} nodes • ${data.stats.total_edges} edges`;
        
        renderGraph(data);
        
    } catch (error) {
        console.error('Error loading graph:', error);
        alert(`Failed to load graph: ${error.message}`);
    }
}

function renderGraph(data) {
    const nodes = new vis.DataSet(
        data.nodes.map(n => ({
            id: n.id,
            label: n.label || n.id,
            title: `${n.id}\nType: ${n.type}`,
            color: getNodeColor(n.type),
            data: n
        }))
    );
    
    const edges = new vis.DataSet(
        data.edges.map((e, i) => ({
            id: i,
            from: e.from,
            to: e.to,
            arrows: 'to',
            smooth: { type: 'cubicBezier' },
            label: e.condition ? e.condition : (e.order !== undefined && e.order !== 0 ? `order:${e.order}` : ''),
            font: { size: 10, color: '#94a3b8' }
        }))
    );
    
    const container = document.getElementById('graph');
    const graphData = { nodes, edges };
    const options = {
        physics: {
            enabled: true,
            stabilization: { iterations: 300 },
            barnesHut: {
                gravitationalConstant: -20000,
                centralGravity: 0.3,
                springLength: 250
            }
        },
        interaction: {
            navigationButtons: true,
            keyboard: true,
            zoomView: true,
            dragView: true
        }
    };
    
    if (network) {
        network.destroy();
    }
    
    network = new vis.Network(container, graphData, options);
    
    network.on('click', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            selectedNodeData = nodes.get(nodeId).data;
            updateSelectedNode();
        } else {
            clearSelection();
        }
    });
    
    updateStats(data);
    setTimeout(fitGraph, 500);
}

function getNodeColor(type) {
    const colors = {
        'action': '#06b6d4',         // Cyan - Do something
        'decision': '#f59e0b',       // Orange - Branch point
        'verification': '#8b5cf6',   // Purple - Check/Guard
        'loop': '#ec4899',           // Pink - Loop entry
        'success': '#10b981',        // Green - Terminal success
        'failure': '#ef4444'         // Red - Terminal failure
    };
    return colors[type] || '#64748b';
}

function updateStats(data) {
    const stats = data.stats;
    const nodeTypes = stats.node_types || {};
    
    let html = `
        <h3>📊 Statistics</h3>
        <div class="stat-row">
            <span class="stat-label">Total Nodes</span>
            <span class="stat-value">${stats.total_nodes}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Total Edges</span>
            <span class="stat-value">${stats.total_edges}</span>
        </div>
    `;
    
    if (stats.phases && stats.phases.length > 0) {
        html += `
            <div class="stat-row">
                <span class="stat-label">Phases</span>
                <span class="stat-value">${stats.phases.join(', ')}</span>
            </div>
        `;
    }
    
    if (stats.decision_points > 0) {
        html += `
            <div class="stat-row">
                <span class="stat-label">Decision Points</span>
                <span class="stat-value">${stats.decision_points}</span>
            </div>
        `;
    }
    
    if (stats.loops > 0) {
        html += `
            <div class="stat-row">
                <span class="stat-label">Loops</span>
                <span class="stat-value">${stats.loops}</span>
            </div>
        `;
    }
    
    html += `
        <h3 style="margin-top: 16px;">🎨 Node Types</h3>
        <div class="legend">
    `;
    
    const typeLabels = {
        'action': 'Action (do something)',
        'decision': 'Decision (branch point)',
        'verification': 'Verification (check/guard)',
        'loop': 'Loop (cycle entry)',
        'success': 'Success (terminal)',
        'failure': 'Failure (terminal)'
    };
    
    for (const [type, count] of Object.entries(nodeTypes)) {
        if (count > 0) {
            html += `
                <div class="legend-item">
                    <div class="legend-color" style="background: ${getNodeColor(type)};"></div>
                    <span>${typeLabels[type] || type} (${count})</span>
                </div>
            `;
        }
    }
    
    html += '</div>';
    document.getElementById('stats').innerHTML = html;
}

function updateSelectedNode() {
    if (!selectedNodeData) {
        document.getElementById('selectedNode').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
        return;
    }
    
    document.getElementById('emptyState').style.display = 'none';
    
    let html = `
        <h3>🔍 Selected Node</h3>
        <div class="node-details">
            <div class="detail-row">
                <div class="detail-label">ID</div>
                <div class="detail-value">${selectedNodeData.id}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Type</div>
                <div class="detail-value">${selectedNodeData.type}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Label</div>
                <div class="detail-value">${selectedNodeData.label || selectedNodeData.id}</div>
            </div>
    `;
    
    if (selectedNodeData.phase !== undefined && selectedNodeData.phase !== null) {
        html += `
            <div class="detail-row">
                <div class="detail-label">Phase</div>
                <div class="detail-value">${selectedNodeData.phase}</div>
            </div>
        `;
    }
    
    if (selectedNodeData.tool) {
        html += `
            <div class="detail-row">
                <div class="detail-label">Tool</div>
                <div class="detail-value">${selectedNodeData.tool}</div>
            </div>
        `;
    }
    
    if (selectedNodeData.properties && Object.keys(selectedNodeData.properties).length > 0) {
        html += `
            <div class="detail-row">
                <div class="detail-label">Properties</div>
                <div class="detail-value">${JSON.stringify(selectedNodeData.properties, null, 2)}</div>
            </div>
        `;
    }
    
    html += '</div>';
    document.getElementById('selectedNode').innerHTML = html;
    document.getElementById('selectedNode').style.display = 'block';
}

function fitGraph() {
    if (network) {
        network.fit({ animation: { duration: 1000 } });
    }
}

function clearSelection() {
    selectedNodeData = null;
    if (network) network.unselectAll();
    updateSelectedNode();
}

window.fitGraph = fitGraph;
window.clearSelection = clearSelection;

