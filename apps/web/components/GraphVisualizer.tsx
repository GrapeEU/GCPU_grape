'use client';

import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useTheme } from '@/contexts/ThemeContext';
import { forceCollide, forceX, forceY } from 'd3-force';

// Dynamically import ForceGraph to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });
const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false });

interface GraphNode {
  id: string;
  label?: string;
  type?: string;
  color?: string;
  sourceRepo?: string;
  sourceRepos?: string[];
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
  relation?: string;
  sourceRepo?: string;
  sourceRepos?: string[];
}

export interface GraphStep {
  title: string;
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface ScenarioGraphData {
  title: string;
  summary: string;
  nodes: GraphNode[];
  links: GraphLink[];
  trace?: string[];
  repo?: string | null;
  graph_steps?: GraphStep[];
}

interface GraphVisualizerProps {
  kgFiles?: string[];
  scenarioData?: ScenarioGraphData | null;
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

const REPO_LABELS: Record<string, string> = {
  hearing: 'Hearing & Tinnitus KG',
  psychiatry: 'Psychiatry KG',
  unified: 'Unified KG',
};

const REPO_COLORS: Record<string, string> = {
  hearing: '#2563EB',
  psychiatry: '#9333EA',
  unified: '#F97316',
};

export default function GraphVisualizer({ kgFiles = [], scenarioData = null }: GraphVisualizerProps) {
  const { theme } = useTheme();
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  const defaultRepos = useMemo(
    () => (kgFiles.includes('unified') ? ['unified'] : [...kgFiles]),
    [kgFiles],
  );
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightNodes, setHighlightNodes] = useState(new Set<string>());
  const [highlightLinks, setHighlightLinks] = useState(new Set<GraphLink>());
  const [graphMode, setGraphMode] = useState<GraphMode>('3d');
  const [showLegend, setShowLegend] = useState(false);
  const [selectedRepos, setSelectedRepos] = useState<string[]>(defaultRepos);
  const [nodeDetails, setNodeDetails] = useState<any | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const fgRef = useRef<any>();
  const containerRef = useRef<HTMLDivElement>(null);

  const arraysEqual = useCallback((a: string[], b: string[]) => {
    if (a === b) return true;
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i += 1) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  }, []);

  const isDark = theme === 'dark';
  const bgColor = isDark ? '#1C1C1C' : '#FDFDFD';

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
    if (scenarioData?.repo) {
      setSelectedRepos(prev => (prev.length === 1 && prev[0] === scenarioData.repo ? prev : [scenarioData.repo]));
      return;
    }
    if (!scenarioData) {
      const target = kgFiles.includes('unified') ? ['unified'] : [...kgFiles];
      setSelectedRepos(prev => (arraysEqual(prev, target) ? prev : target));
    }
  }, [kgFiles, scenarioData, arraysEqual]);

  useEffect(() => {
    if (!scenarioData) {
      return;
    }

    // If graph_steps exists, use current step, otherwise use nodes/links
    const sourceData = scenarioData.graph_steps && scenarioData.graph_steps.length > 0
      ? scenarioData.graph_steps[currentStepIndex]
      : scenarioData;

    const nodes = sourceData.nodes.map(node => ({
      ...node,
      label: node.label || node.id.split(/[/#]/).pop() || node.id,
      color: scenarioData.repo ? (REPO_COLORS[scenarioData.repo] || '#F97316') : '#F97316',
      sourceRepos: scenarioData.repo ? [scenarioData.repo] : node.sourceRepos || [],
      sourceRepo: scenarioData.repo || node.sourceRepo,
    }));

    const links = sourceData.links.map(link => ({
      source: link.source,
      target: link.target,
      label: link.label || link.relation || '',
      relation: link.relation,
      sourceRepos: scenarioData.repo ? [scenarioData.repo] : link.sourceRepos || [],
      sourceRepo: scenarioData.repo || link.sourceRepo,
    }));

    setGraphData({ nodes, links });
    setSelectedNode(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
    setLoading(false);
    setError(null);

    requestAnimationFrame(() => {
      if (fgRef.current && typeof fgRef.current.zoomToFit === 'function') {
        fgRef.current.zoomToFit(400, 40);
      }
    });
  }, [scenarioData, currentStepIndex]);

  useEffect(() => {
    if (scenarioData) {
      return;
    }

    if (!selectedRepos.length) {
      setGraphData({ nodes: [], links: [] });
      return;
    }

    const loadRepoGraphs = async () => {
      setLoading(true);
      setError(null);

      try {
        const responses = await Promise.all(
          selectedRepos.map(async repo => {
            const response = await fetch(`${apiBaseUrl}/api/graph/${repo}/data`);
            if (!response.ok) {
              throw new Error(`Failed to load repository ${repo}`);
            }
            const data = await response.json();
            return { repo, data };
          }),
        );

        const uniqueNodes = new Map<string, GraphNode>();
        const combinedLinks: GraphLink[] = [];
        const linkIndex = new Map<string, number>();

        responses.forEach(({ repo, data }) => {
          data.nodes.forEach((node: any) => {
            const label = node.label || node.id.split(/[/#]/).pop() || node.id;
            const existing = uniqueNodes.get(node.id);
            const repoSet = new Set(existing?.sourceRepos || []);
            const intrinsicRepos = Array.isArray(node.sourceRepos) && node.sourceRepos.length
              ? node.sourceRepos
              : node.sourceRepo
              ? [node.sourceRepo]
              : [];

            intrinsicRepos.forEach((r: string) => repoSet.add(r));
            if (repo !== 'unified' || repoSet.size === 0) {
              repoSet.add(repo);
            }

            uniqueNodes.set(node.id, {
              id: node.id,
              label,
              type: node.type || existing?.type,
              color: existing?.color || '#1C1C1C',
              sourceRepos: Array.from(repoSet),
              sourceRepo: repoSet.size === 1 ? Array.from(repoSet)[0] : undefined,
            });
          });

          data.links.forEach((link: any) => {
            const label = link.label || link.relation || '';
            const key = `${link.source}::${link.target}::${label}`;
            const existingIndex = linkIndex.get(key);
            const intrinsicRepos = Array.isArray(link.sourceRepos) && link.sourceRepos.length
              ? link.sourceRepos
              : link.sourceRepo
              ? [link.sourceRepo]
              : [];

            if (existingIndex === undefined) {
              const repoSet = new Set<string>();
              intrinsicRepos.forEach((r: string) => repoSet.add(r));
              if (repo !== 'unified' || repoSet.size === 0) {
                repoSet.add(repo);
              }

              linkIndex.set(key, combinedLinks.length);
              combinedLinks.push({
                source: link.source,
                target: link.target,
                label,
                relation: link.relation || label,
                sourceRepos: Array.from(repoSet),
                sourceRepo: repoSet.size === 1 ? Array.from(repoSet)[0] : undefined,
              });
            } else {
              const existingLink = combinedLinks[existingIndex];
              const repoSet = new Set(existingLink.sourceRepos || []);
              intrinsicRepos.forEach((r: string) => repoSet.add(r));
              if (repo !== 'unified' || repoSet.size === 0) {
                repoSet.add(repo);
              }
              combinedLinks[existingIndex] = {
                ...existingLink,
                sourceRepos: Array.from(repoSet),
                sourceRepo: repoSet.size === 1 ? Array.from(repoSet)[0] : undefined,
              };
            }
          });
        });

        setGraphData({ nodes: Array.from(uniqueNodes.values()), links: combinedLinks });
        setSelectedNode(null);
        setHighlightNodes(new Set());
        setHighlightLinks(new Set());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load knowledge graph');
        setGraphData({ nodes: [], links: [] });
        console.error('Error loading KG:', err);
      } finally {
        setLoading(false);
      }
    };

    loadRepoGraphs();
  }, [scenarioData, selectedRepos, apiBaseUrl]);

  useEffect(() => {
    if (!selectedNode) {
      setNodeDetails(null);
      setDetailsError(null);
      return;
    }

    const repoForDetails =
      scenarioData?.repo ||
      (Array.isArray(selectedNode.sourceRepos) && selectedNode.sourceRepos.length
        ? selectedNode.sourceRepos[0]
        : selectedRepos[0] || null);

    if (!repoForDetails) {
      setDetailsError(null);
      setNodeDetails(
        scenarioData
          ? { id: selectedNode.id, summary: scenarioData.summary }
          : null,
      );
      return;
    }

    const fetchDetails = async () => {
      setDetailsLoading(true);
      setDetailsError(null);
      try {
        const response = await fetch(`${apiBaseUrl}/api/graph/${repoForDetails}/node?id=${encodeURIComponent(selectedNode.id)}`);
        if (!response.ok) {
          throw new Error('Unable to load node details');
        }
        const data = await response.json();
        setNodeDetails({
          ...data,
          repo: repoForDetails,
          scenarioSummary: scenarioData?.summary || null,
        });
      } catch (err) {
        setDetailsError(err instanceof Error ? err.message : 'Failed to load node details');
        setNodeDetails(
          scenarioData
            ? { id: selectedNode.id, summary: scenarioData.summary }
            : null,
        );
      } finally {
        setDetailsLoading(false);
      }
    };

    fetchDetails();
  }, [selectedNode, selectedRepos, scenarioData, apiBaseUrl]);

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
    setNodeDetails(null);
    setDetailsError(null);
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
    setNodeDetails(null);
    setDetailsError(null);
  }, []);

  const hasData = graphData.nodes.length > 0;
  const baseNodeColor = scenarioData ? '#F97316' : '#1C1C1C';
  const baseLinkColor = scenarioData ? '#F97316' : (isDark ? '#4B5563' : '#CBD5F0');

  const activeRepos = useMemo(() => {
    if (scenarioData?.repo) {
      return [scenarioData.repo];
    }
    const repoSet = new Set<string>();
    graphData.nodes.forEach(node => {
      if (Array.isArray(node.sourceRepos)) {
        node.sourceRepos.forEach(repo => {
          if (repo) repoSet.add(repo);
        });
      } else if (node.sourceRepo) {
        repoSet.add(node.sourceRepo);
      }
    });
    return Array.from(repoSet);
  }, [graphData, scenarioData]);

  const repoPositionMap = useMemo(() => {
    if (scenarioData) {
      return {} as Record<string, { x: number; y: number }>;
    }
    const repos = activeRepos.length ? activeRepos : selectedRepos;
    if (!repos || repos.length <= 1) {
      return {} as Record<string, { x: number; y: number }>;
    }

    const spacing = 380;
    const map: Record<string, { x: number; y: number }> = {};
    repos.forEach((repo, index) => {
      const angle = (index / repos.length) * Math.PI * 2;
      map[repo] = {
        x: Math.cos(angle) * spacing,
        y: Math.sin(angle) * spacing,
      };
    });
    return map;
  }, [activeRepos, selectedRepos, scenarioData]);

  const resolveNodeColor = useCallback(
    (node: GraphNode) => {
      if (node.color) return node.color;
      if (scenarioData) return baseNodeColor;

      const repos = Array.isArray(node.sourceRepos) && node.sourceRepos.length
        ? node.sourceRepos
        : node.sourceRepo
        ? [node.sourceRepo]
        : [];

      if (repos.length === 0) {
        return selectedRepos.length > 1 || activeRepos.length > 1 ? '#4B5563' : baseNodeColor;
      }

      if (repos.length > 1) {
        return '#F59E0B';
      }

      const repoColor = REPO_COLORS[repos[0]];
      return repoColor || baseNodeColor;
    },
    [activeRepos, baseNodeColor, scenarioData, selectedRepos],
  );

  const configureGraphForces = useCallback(
    (force: any) => {
      if (!force) return;
      force('link').distance(220).strength(0.25);
      force('charge').strength(-360);
      force('center').strength(0.12);
      force('collision', forceCollide(32));

      if (!scenarioData && Object.keys(repoPositionMap).length > 1) {
        const targetX = forceX((node: GraphNode) => {
          const repos = Array.isArray(node.sourceRepos) && node.sourceRepos.length
            ? node.sourceRepos
            : node.sourceRepo
            ? [node.sourceRepo]
            : [];
          const anchor = repos.find(r => repoPositionMap[r]);
          if (anchor) return repoPositionMap[anchor].x;
          if (repos.length > 1) return 0;
          return 0;
        }).strength(0.09);

        const targetY = forceY((node: GraphNode) => {
          const repos = Array.isArray(node.sourceRepos) && node.sourceRepos.length
            ? node.sourceRepos
            : node.sourceRepo
            ? [node.sourceRepo]
            : [];
          const anchor = repos.find(r => repoPositionMap[r]);
          if (anchor) return repoPositionMap[anchor].y;
          if (repos.length > 1) return 0;
          return 0;
        }).strength(0.09);

        force('separateX', targetX);
        force('separateY', targetY);
      } else {
        force('separateX', null);
        force('separateY', null);
      }
    },
    [repoPositionMap, scenarioData],
  );

  const commonProps = {
    graphData,
    nodeLabel: (node: any) => node.label,
    nodeColor: (node: GraphNode) => resolveNodeColor(node),
    nodeRelSize: 4,
    nodeVal: (node: any) => {
      if (selectedNode?.id === node.id) return 3;
      if (highlightNodes.has(node.id)) return 2;
      return 1;
    },
    linkColor: (link: any) => highlightLinks.has(link) ? '#F97316' : baseLinkColor,
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
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 pb-3">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>
              {scenarioData ? scenarioData.title : hasData ? 'Interactive knowledge graph view' : 'Waiting for graph data'}
            </p>
            {!scenarioData && kgFiles.length > 0 && (
              <p className={`text-xs ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>
                Sources: {selectedRepos.map(repo => REPO_LABELS[repo] || repo).join(', ')}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            {hasData && (
              <>
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
              </>
            )}
          </div>
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
                d3Force={configureGraphForces}
                linkCanvasObjectMode={() => 'after'}
                linkCanvasObject={(link: any, ctx: any) => {
                  const start = link.source;
                  const end = link.target;
                  if (typeof start !== 'object' || typeof end !== 'object') return;

                  const textPos = { x: start.x + (end.x - start.x) / 2, y: start.y + (end.y - start.y) / 2 };
                  const label = link.label;
                  if (!label) {
                    return;
                  }
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
                d3Force={configureGraphForces}
              />
            )}

            {/* Step Label - Top Left */}
            {scenarioData?.graph_steps && scenarioData.graph_steps.length > 1 && (
              <div className={`absolute top-4 left-4 rounded-lg shadow-lg px-4 py-2 ${isDark ? 'bg-[#1F2937] border border-[#374151]' : 'bg-white border border-[#E5E7EB]'}`}>
                <div className={`text-xs ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'} mb-1`}>
                  Step {currentStepIndex + 1} / {scenarioData.graph_steps.length}
                </div>
                <div className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>
                  {scenarioData.graph_steps[currentStepIndex].title}
                </div>
              </div>
            )}

            {/* Legend */}
            {showLegend && (
              <div className={`absolute ${scenarioData?.graph_steps && scenarioData.graph_steps.length > 1 ? 'top-24' : 'top-4'} left-4 rounded-lg shadow-lg p-4 ${isDark ? 'bg-[#1F2937] border border-[#374151]' : 'bg-white border border-[#E5E7EB]'}`}>
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
              <div className={`absolute top-4 right-4 w-96 rounded-lg shadow-lg p-4 max-h-[85vh] overflow-y-auto ${isDark ? 'bg-[#1F2937] border border-[#374151]' : 'bg-white border border-[#E5E7EB]'}`}>
                <div className="flex items-start justify-between mb-3">
                  <h4 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>Node Details</h4>
                  <button onClick={handleBackgroundClick} className={isDark ? 'text-[#9CA3AF] hover:text-white' : 'text-[#6B7280] hover:text-[#1C1C1C]'}>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <div className={`text-xs ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>
                  <div className="mb-2">
                    <span className="font-semibold">Label:</span> {selectedNode.label}
                  </div>
                  <div className="mb-2 break-words">
                    <span className="font-semibold">Identifier:</span> {selectedNode.id}
                  </div>
                  {selectedNode.sourceRepos && selectedNode.sourceRepos.length > 0 && (
                    <div className="mb-2">
                      <span className="font-semibold">Repositories:</span>{' '}
                      {selectedNode.sourceRepos.map(repo => REPO_LABELS[repo] || repo).join(', ')}
                    </div>
                  )}
                  {selectedNode.type && (
                    <div className="mb-3">
                      <span className="font-semibold">Type hint:</span> {selectedNode.type}
                    </div>
                  )}
                </div>

                {detailsLoading ? (
                  <div className="flex items-center gap-2 text-xs">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#E57373]" />
                    <span className={isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}>Loading node ontology…</span>
                  </div>
                ) : detailsError ? (
                  <div className={`text-xs ${isDark ? 'text-[#FCA5A5]' : 'text-[#B91C1C]'}`}>{detailsError}</div>
                ) : nodeDetails ? (
                  <div className="text-xs space-y-3">
                    {nodeDetails.repo && (
                      <div>
                        <div className="font-semibold mb-1">Details source</div>
                        <p className={isDark ? 'text-[#E5E7EB]' : 'text-[#1C1C1C]'}>
                          {REPO_LABELS[nodeDetails.repo] || nodeDetails.repo}
                        </p>
                      </div>
                    )}

                    {nodeDetails.scenarioSummary && (
                      <div>
                        <div className="font-semibold mb-1">Scenario insight</div>
                        <p className={isDark ? 'text-[#E5E7EB]' : 'text-[#1C1C1C]'}>
                          {nodeDetails.scenarioSummary}
                        </p>
                      </div>
                    )}

                    {nodeDetails.types && nodeDetails.types.length > 0 && (
                      <div>
                        <div className="font-semibold mb-1">Types</div>
                        <ul className={`list-disc ml-4 ${isDark ? 'text-[#E5E7EB]' : 'text-[#1C1C1C]'}`}>
                          {nodeDetails.types.map((type: string) => (
                            <li key={type}>{type}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {nodeDetails.outgoing && nodeDetails.outgoing.length > 0 && (
                      <div>
                        <div className="font-semibold mb-1">Outgoing relations</div>
                        <ul className={`space-y-1 ${isDark ? 'text-[#E5E7EB]' : 'text-[#1C1C1C]'}`}>
                          {nodeDetails.outgoing.map((edge: any, idx: number) => (
                            <li key={`out-${idx}`}>
                              <span className="font-semibold">{edge.predicateLabel}</span> → {edge.targetLabel}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {nodeDetails.incoming && nodeDetails.incoming.length > 0 && (
                      <div>
                        <div className="font-semibold mb-1">Incoming relations</div>
                        <ul className={`space-y-1 ${isDark ? 'text-[#E5E7EB]' : 'text-[#1C1C1C]'}`}>
                          {nodeDetails.incoming.map((edge: any, idx: number) => (
                            <li key={`in-${idx}`}>
                              {edge.sourceLabel} — <span className="font-semibold">{edge.predicateLabel}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {!nodeDetails.types?.length && !nodeDetails.outgoing?.length && !nodeDetails.incoming?.length && (
                      <div>No additional ontology facts available.</div>
                    )}
                  </div>
                ) : (
                  <div className={`text-xs ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>No additional ontology facts available.</div>
                )}
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

      {/* Graph Steps Slider */}
      {scenarioData?.graph_steps && scenarioData.graph_steps.length > 1 && (
        <div className="px-6 py-3 border-t border-opacity-10" style={{ borderColor: isDark ? '#374151' : '#E5E7EB' }}>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setCurrentStepIndex(Math.max(0, currentStepIndex - 1))}
              disabled={currentStepIndex === 0}
              className={`p-2 rounded-lg transition-colors ${
                currentStepIndex === 0
                  ? 'opacity-30 cursor-not-allowed'
                  : isDark
                  ? 'bg-[#1F2937] text-white hover:bg-[#374151]'
                  : 'bg-[#F3F4F6] text-[#1C1C1C] hover:bg-[#E5E7EB]'
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>

            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>
                  {scenarioData.graph_steps[currentStepIndex].title}
                </span>
                <span className={`text-xs ${isDark ? 'text-[#9CA3AF]' : 'text-[#6B7280]'}`}>
                  Step {currentStepIndex + 1} / {scenarioData.graph_steps.length}
                </span>
              </div>

              <div className="relative">
                <input
                  type="range"
                  min="0"
                  max={scenarioData.graph_steps.length - 1}
                  value={currentStepIndex}
                  onChange={(e) => setCurrentStepIndex(parseInt(e.target.value))}
                  className="w-full h-2 rounded-lg appearance-none cursor-pointer slider"
                  style={{
                    background: `linear-gradient(to right, #E57373 0%, #E57373 ${(currentStepIndex / (scenarioData.graph_steps.length - 1)) * 100}%, ${isDark ? '#374151' : '#E5E7EB'} ${(currentStepIndex / (scenarioData.graph_steps.length - 1)) * 100}%, ${isDark ? '#374151' : '#E5E7EB'} 100%)`
                  }}
                />
              </div>
            </div>

            <button
              onClick={() => setCurrentStepIndex(Math.min(scenarioData.graph_steps!.length - 1, currentStepIndex + 1))}
              disabled={currentStepIndex === scenarioData.graph_steps.length - 1}
              className={`p-2 rounded-lg transition-colors ${
                currentStepIndex === scenarioData.graph_steps.length - 1
                  ? 'opacity-30 cursor-not-allowed'
                  : isDark
                  ? 'bg-[#1F2937] text-white hover:bg-[#374151]'
                  : 'bg-[#F3F4F6] text-[#1C1C1C] hover:bg-[#E5E7EB]'
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Footer Info */}
      <div className="px-6 pt-3">
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
          <span>
            {hasData
              ? scenarioData
                ? `${scenarioData.repo ? (REPO_LABELS[scenarioData.repo] || scenarioData.repo) : 'Scenario dataset'} • ${graphMode.toUpperCase()} mode`
                : `${selectedRepos.length} repo(s) visible • ${graphMode.toUpperCase()} mode`
              : 'Awaiting agent selection'}
          </span>
        </div>
      </div>
    </div>
  );
}
