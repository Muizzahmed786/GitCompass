import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import NodeInspector from './NodeInspector';

// Abstracted layout function
const layoutGraph = (nodes, edges, direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  
  const nodeWidth = 172;
  const nodeHeight = 50;

  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: direction === 'TB' ? 'top' : 'left',
      sourcePosition: direction === 'TB' ? 'bottom' : 'right',
      // Shift to center the node
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};


export default function ArchitectureGraph({ repoId, graphData }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeId, setSelectedNodeId] = useState(null);

  // Initialize graph
  useEffect(() => {
    if (!graphData || !graphData.nodes) return;

    // Transform backend UI-agnostic domain models to React Flow models
    const initialNodes = graphData.nodes.map((n) => ({
      id: n.id,
      data: { label: n.label, category: n.category, type: n.type },
      style: {
        background: n.type === 'dependency' ? '#ecfdf5' : '#eff6ff',
        border: '1px solid #94a3b8',
        borderRadius: '8px',
        fontWeight: 'bold'
      }
    }));

    const initialEdges = graphData.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.type,
      markerEnd: { type: MarkerType.ArrowClosed },
      animated: e.type === 'imports',
      style: { stroke: '#64748b' }
    }));

    const { nodes: layoutedNodes, edges: layoutedEdges } = layoutGraph(initialNodes, initialEdges);

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [graphData, setNodes, setEdges]);

  const onNodeClick = useCallback((event, node) => {
    setSelectedNodeId(node.id);
  }, []);

  const closeInspector = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const selectedNode = useMemo(() => {
    if (!selectedNodeId || !graphData) return null;
    return graphData.nodes.find(n => n.id === selectedNodeId);
  }, [selectedNodeId, graphData]);

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full w-full bg-slate-50 border border-slate-200 rounded-lg">
        <p className="text-slate-500">No architectural dependency data available for this repository.</p>
      </div>
    );
  }

  // Handle explicit large-graph limits (Requirement #3)
  const isTruncated = graphData.is_truncated;

  return (
    <div className="relative w-full h-full flex overflow-hidden rounded-xl border border-slate-200 shadow-sm">
      <div className="flex-1 relative">
        {isTruncated && (
          <div className="absolute top-2 left-2 z-10 bg-amber-100 text-amber-800 text-xs px-3 py-1.5 rounded-full shadow-sm font-medium">
            Graph truncated for performance (exceeded node/edge limits)
          </div>
        )}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          minZoom={0.1}
          maxZoom={1.5}
        >
          <Controls />
          <MiniMap />
          <Background variant="dots" gap={12} size={1} />
        </ReactFlow>
      </div>

      {selectedNode && (
        <NodeInspector
          repoId={repoId}
          node={selectedNode}
          onClose={closeInspector}
        />
      )}
    </div>
  );
}
