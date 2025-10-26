'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { useTheme } from '@/contexts/ThemeContext';

// Dynamically import ForceGraph to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });
const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false });

interface GraphVisualizerProps {
  kgFiles?: string[];
}

interface GraphNode {
  id: string;
  label?: string;
  type?: string;
  color?: string;
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

type GraphMode = '2d' | '3d';

// Color mapping for different node types
const NODE_COLORS: Record<string, string> = {
  'exmed:Condition': '#E57373',
  'exmed:Symptom': '#FFA726',
  'exmed:RiskFactor': '#EF5350',
  'exmed:Intervention': '#66BB6A',
  'exmed:DiagnosticTest': '#42A5F5',
  'exmed:AnatomicalSystem': '#AB47BC',
  'exhear:Condition': '#E57373',
  'exhear:Symptom': '#FFA726',
  'expsych:Condition': '#E57373',
  'expsych:Symptom': '#FFA726',
  'schema:Person': '#78909C',
  'Unknown': '#BDBDBD',
};

const LEGEND_ITEMS = [
  { label: 'Condition', color: '#E57373' },
  { label: 'Symptom', color: '#FFA726' },
  { label: 'Intervention', color: '#66BB6A' },
  { label: 'Risk Factor', color: '#EF5350' },
  { label: 'Diagnostic Test', color: '#42A5F5' },
  { label: 'Person', color: '#78909C' },
];

const getNodeColor = (type: string | undefined): string => {
  if (!type) return NODE_COLORS['Unknown'];
  if (NODE_COLORS[type]) return NODE_COLORS[type];
  if (type.includes('Condition')) return NODE_COLORS['exmed:Condition'];
  if (type.includes('Symptom')) return NODE_COLORS['exmed:Symptom'];
  if (type.includes('Person')) return NODE_COLORS['schema:Person'];
  if (type.includes('Intervention') || type.includes('Therapy')) return NODE_COLORS['exmed:Intervention'];
  if (type.includes('Risk')) return NODE_COLORS['exmed:RiskFactor'];
  if (type.includes('Test') || type.includes('Diagnostic')) return NODE_COLORS['exmed:DiagnosticTest'];
  return NODE_COLORS['Unknown'];
};

export default function GraphVisualizer({ kgFiles = [] }: GraphVisualizerProps) {
  const { theme } = useTheme();
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightNodes, setHighlightNodes] = useState(new Set<string>());
  const [highlightLinks, setHighlightLinks] = useState(new Set<GraphLink>());
  const [graphMode, setGraphMode] = useState<GraphMode>('2d');
  const [showLegend, setShowLegend] = useState(true);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const fgRef = useRef<any>();
  const containerRef = useRef<HTMLDivElement>(null);

  const isDark = theme === 'dark';
  const bgColor = isDark ? '#1C1C1C' : '#FDFDFD';
  const textColor = isDark ? '#E5E7EB' : '#1C1C1C';
  const borderColor = isDark ? '#374151' : '#E5E7EB';

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    if (kgFiles.length === 0) {
      setGraphData({ nodes: [], links: [] });
      return;
    }

    const loadKGData = async () => {
      setLoading(true);
      setError(null);

      try {
        const allNodes = new Map<string, GraphNode>();
        const allLinks: GraphLink[] = [];

        for (const kgFile of kgFiles) {
          const response = await fetch(kgFile);
          if (!response.ok) throw new Error(`Failed to load ${kgFile}`);

          const jsonLd = await response.json();
          const graph = jsonLd['@graph'] || [];

          graph.forEach((item: any) => {
            const nodeId = item['@id'];
            if (!nodeId) return;

            // Skip OWL ontology class definitions (they're just schema)
            const nodeType = item.type || item['@type'] || 'Unknown';
            if (nodeType === 'Class' || nodeType === 'owl:Class' ||
                nodeType === 'ObjectProperty' || nodeType === 'owl:ObjectProperty') {
              return;
            }

            if (!allNodes.has(nodeId)) {
              allNodes.set(nodeId, {
                id: nodeId,
                label: item.label || item['rdfs:label'] || nodeId.split(/[/#]/).pop() || nodeId,
                type: nodeType,
                color: getNodeColor(nodeType),
              });
            }

            // Extract relationships (links)
            Object.entries(item).forEach(([key, value]) => {
              if (key.startsWith('@') || key === 'label' || key === 'type' ||
                  key === 'rdfs:label' || key === 'comment') return;

              const targets = Array.isArray(value) ? value : [value];
              targets.forEach((target: any) => {
                if (typeof target === 'string' && target.startsWith('ex')) {
                  allLinks.push({
                    source: nodeId,
                    target: target,
                    label: key.split(/[/#:]/).pop() || key,
                  });

                  if (!allNodes.has(target)) {
                    allNodes.set(target, {
                      id: target,
                      label: target.split(/[/#]/).pop() || target,
                      type: 'Unknown',
                      color: NODE_COLORS['Unknown'],
                    });
                  }
                }
              });
            });
          });
        }

        // Filter out isolated nodes (nodes with no connections)
        const connectedNodeIds = new Set<string>();
        allLinks.forEach(link => {
          connectedNodeIds.add(typeof link.source === 'string' ? link.source : (link.source as any).id);
          connectedNodeIds.add(typeof link.target === 'string' ? link.target : (link.target as any).id);
        });

        const filteredNodes = Array.from(allNodes.values()).filter(node =>
          connectedNodeIds.has(node.id)
        );

        setGraphData({
          nodes: filteredNodes,
          links: allLinks,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load knowledge graph');
        console.error('Error loading KG:', err);
      } finally {
        setLoading(false);
      }
    };

    loadKGData();
  }, [kgFiles]);

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
    const neighbors = new Set<string>();
    const connectedLinks = new Set<GraphLink>();

    graphData.links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : (link.source as any).id;
      const targetId = typeof link.target === 'string' ? link.target : (link.target as any).id;

      if (sourceId === node.id) {
        neighbors.add(targetId);
        connectedLinks.add(link);
      }
      if (targetId === node.id) {
        neighbors.add(sourceId);
        connectedLinks.add(link);
      }
    });

    neighbors.add(node.id);
    setHighlightNodes(neighbors);
    setHighlightLinks(connectedLinks);
  }, [graphData.links]);

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
  }, []);

  const hasData = graphData.nodes.length > 0;

  const commonProps = {
    graphData,
    nodeLabel: (node: any) => node.label,
    nodeColor: (node: any) => node.color,
    nodeRelSize: 4,
    nodeVal: (node: any) => {
      if (selectedNode?.id === node.id) return 3;
      if (highlightNodes.has(node.id)) return 2;
      return 1;
    },
    linkColor: (link: any) => highlightLinks.has(link) ? '#E57373' : (isDark ? '#374151' : '#E5E7EB'),
    linkWidth: (link: any) => highlightLinks.has(link) ? 6 : 3,
    linkDirectionalArrowLength: 6,
    linkDirectionalArrowRelPos: 1,
    onNodeClick: handleNodeClick,
    onBackgroundClick: handleBackgroundClick,
    backgroundColor: bgColor,
    cooldownTicks: 150,
    d3VelocityDecay: 0.2,
    d3AlphaDecay: 0.005,
    d3AlphaMin: 0.0001,
    warmupTicks: 150,
  };

  return (
    <div className={`flex flex-col h-full rounded-lg border ${isDark ? 'bg-[#111827] border-[#374151]' : 'bg-white border-[#E5E7EB]'}`}>
      {/* Header */}
      <div className={`px-6 py-4 border-b ${isDark ? 'border-[#374151]' : 'border-[#E5E7EB]'}`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>
              Knowledge Graph Visualizer
            </h3>
          </div>

          {hasData && (
            <div className="flex items-center gap-2">
              {/* 2D/3D Toggle */}
              <div className={`flex items-center gap-1 p-1 rounded-lg ${isDark ? 'bg-[#1F2937]' : 'bg-[#F3F4F6]'}`}>
                <button
                  onClick={() => setGraphMode('2d')}
                  className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                    graphMode === '2d'
                      ? 'bg-[#E57373] text-white'
                      : isDark
                      ? 'text-[#9CA3AF] hover:text-white'
                      : 'text-[#6B7280] hover:text-[#1C1C1C]'
                  }`}
                >
                  2D
                </button>
                <button
                  onClick={() => setGraphMode('3d')}
                  className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                    graphMode === '3d'
                      ? 'bg-[#E57373] text-white'
                      : isDark
                      ? 'text-[#9CA3AF] hover:text-white'
                      : 'text-[#6B7280] hover:text-[#1C1C1C]'
                  }`}
                >
                  3D
                </button>
              </div>

              {/* Legend Toggle */}
              <button
                onClick={() => setShowLegend(!showLegend)}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  isDark
                    ? 'bg-[#1F2937] text-[#9CA3AF] hover:text-white'
                    : 'bg-[#F3F4F6] text-[#6B7280] hover:text-[#1C1C1C]'
                }`}
              >
                {showLegend ? 'Hide' : 'Show'} Legend
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Graph Display */}
      <div ref={containerRef} className="flex-1 overflow-hidden relative" style={{ width: '100%', height: '100%' }}>
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-[#E57373]" />
            <p className={`mt-4 ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>Loading knowledge graph...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg className="w-16 h-16 text-[#EF4444] mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h4 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>Error Loading Graph</h4>
            <p className={isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}>{error}</p>
          </div>
        ) : hasData ? (
          <>
            {graphMode === '2d' ? (
              <ForceGraph2D
                ref={fgRef}
                {...commonProps}
                width={dimensions.width}
                height={dimensions.height}
                d3Force={(force: any) => {
                  force('link').distance(500);
                  force('charge').strength(-1000);
                }}
                linkCanvasObjectMode={() => 'after'}
                linkCanvasObject={(link: any, ctx: any) => {
                  const start = link.source;
                  const end = link.target;
                  if (typeof start !== 'object' || typeof end !== 'object') return;

                  const textPos = { x: start.x + (end.x - start.x) / 2, y: start.y + (end.y - start.y) / 2 };
                  const label = link.label;
                  const fontSize = 10;
                  ctx.font = `${fontSize}px Sans-Serif`;
                  const textWidth = ctx.measureText(label).width;
                  const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

                  ctx.fillStyle = isDark ? 'rgba(28, 28, 28, 0.9)' : 'rgba(255, 255, 255, 0.9)';
                  ctx.fillRect(textPos.x - bckgDimensions[0] / 2, textPos.y - bckgDimensions[1] / 2, ...bckgDimensions);

                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'middle';
                  ctx.fillStyle = isDark ? '#9CA3AF' : '#6B7280';
                  ctx.fillText(label, textPos.x, textPos.y);
                }}
              />
            ) : (
              <ForceGraph3D
                ref={fgRef}
                {...commonProps}
                width={dimensions.width}
                height={dimensions.height}
                d3Force={(force: any) => {
                  force('link').distance(500);
                  force('charge').strength(-1000);
                }}
              />
            )}

            {/* Legend */}
            {showLegend && (
              <div className={`absolute top-4 left-4 rounded-lg shadow-lg p-4 ${isDark ? 'bg-[#1F2937] border border-[#374151]' : 'bg-white border border-[#E5E7EB]'}`}>
                <h4 className={`text-sm font-semibold mb-3 ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>Node Types</h4>
                <div className="space-y-2">
                  {LEGEND_ITEMS.map(item => (
                    <div key={item.label} className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className={`text-xs ${isDark ? 'text-[#E5E7EB]' : 'text-[#1C1C1C]'}`}>{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Node Info Panel */}
            {selectedNode && (
              <div className={`absolute top-4 right-4 w-80 rounded-lg shadow-lg p-4 max-h-[80vh] overflow-y-auto ${isDark ? 'bg-[#1F2937] border border-[#374151]' : 'bg-white border border-[#E5E7EB]'}`}>
                <div className="flex items-start justify-between mb-3">
                  <h4 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>Node Details</h4>
                  <button onClick={handleBackgroundClick} className={isDark ? 'text-[#9CA3AF] hover:text-white' : 'text-[#6B7280] hover:text-[#1C1C1C]'}>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <div className="space-y-3">
                  <div>
                    <div className={`text-xs ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>Label</div>
                    <div className={`text-sm font-medium ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>{selectedNode.label}</div>
                  </div>
                  <div>
                    <div className={`text-xs ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>Type</div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: selectedNode.color }} />
                      <div className={`text-sm ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>{selectedNode.type}</div>
                    </div>
                  </div>

                  {/* Relations */}
                  <div>
                    <div className={`text-xs font-semibold mb-2 ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>
                      Relations ({Array.from(highlightLinks).length})
                    </div>
                    <div className={`space-y-1 max-h-48 overflow-y-auto ${isDark ? 'text-[#E5E7EB]' : 'text-[#1C1C1C]'}`}>
                      {Array.from(highlightLinks).map((link, idx) => {
                        const sourceId = typeof link.source === 'string' ? link.source : (link.source as any).id;
                        const targetId = typeof link.target === 'string' ? link.target : (link.target as any).id;
                        const isOutgoing = sourceId === selectedNode.id;
                        const connectedNodeId = isOutgoing ? targetId : sourceId;
                        const connectedNode = graphData.nodes.find(n => n.id === connectedNodeId);

                        return (
                          <div key={idx} className={`text-xs p-2 rounded ${isDark ? 'bg-[#111827]' : 'bg-[#F9FAFB]'}`}>
                            <div className="flex items-center gap-1">
                              <span className={`font-medium ${isDark ? 'text-[#E57373]' : 'text-[#E57373]'}`}>
                                {isOutgoing ? '→' : '←'} {link.label}
                              </span>
                            </div>
                            <div className="flex items-center gap-1 mt-1">
                              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: connectedNode?.color || '#BDBDBD' }} />
                              <span className={isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}>
                                {connectedNode?.label || connectedNodeId.split(/[/#]/).pop()}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className={`flex flex-col items-center justify-center h-full ${isDark ? 'bg-[#111827]' : 'bg-[#FDFDFD]'}`}>
            <div className="mb-4">
              <svg className={`w-24 h-24 ${isDark ? 'text-[#374151]' : 'text-[#E5E7EB]'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h4 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>No Knowledge Graph Loaded</h4>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className={`px-6 py-3 border-t ${isDark ? 'bg-[#111827] border-[#374151]' : 'bg-[#FDFDFD] border-[#E5E7EB]'}`}>
        <div className={`flex items-center justify-between text-xs ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${loading ? 'bg-[#F59E0B]' : error ? 'bg-[#EF4444]' : hasData ? 'bg-[#10B981]' : 'bg-[#6B7280]'}`} />
              {loading ? 'Loading...' : error ? 'Error' : hasData ? 'Loaded' : 'Ready'}
            </span>
            {hasData && (
              <>
                <span>Nodes: {graphData.nodes.length}</span>
                <span>Edges: {graphData.links.length}</span>
              </>
            )}
          </div>
          <span>{hasData ? `${kgFiles.length} KG file(s) • ${graphMode.toUpperCase()} mode` : 'Awaiting agent selection'}</span>
        </div>
      </div>
    </div>
  );
}
