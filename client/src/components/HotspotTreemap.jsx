import { useMemo, useState } from "react";
import * as d3 from "d3";

function buildTree(hotspots) {
  const root = { name: "root", children: [] };
  
  (hotspots || []).forEach(hotspot => {
    if (!hotspot.file_path) return;
    const cleanPath = hotspot.file_path.replace(/^\//, "");
    const parts = cleanPath.split("/");
    let currentLevel = root.children;
    
    parts.forEach((part, index) => {
      if (index === parts.length - 1) {
        currentLevel.push({
          name: part,
          path: hotspot.file_path,
          value: Math.max((hotspot.total_insertions || 0) + (hotspot.total_deletions || 0), 1),
          commits: hotspot.commits_count || 0,
          insertions: hotspot.total_insertions || 0,
          deletions: hotspot.total_deletions || 0,
          authors: hotspot.authors || [],
          top_author: hotspot.top_author,
          top_author_share: hotspot.top_author_share,
          is_orphan_risk: hotspot.is_orphan_risk,
          commit_types: hotspot.commit_types || {},
        });
      } else {
        let existingNode = currentLevel.find(n => n.name === part && n.children);
        if (!existingNode) {
          existingNode = { name: part, children: [] };
          currentLevel.push(existingNode);
        }
        currentLevel = existingNode.children;
      }
    });
  });
  
  return root;
}

const THEMES = {
  neon: {
    name: "Midnight Neon",
    colors: ["#06b6d4", "#3b82f6", "#8b5cf6", "#f43f5e"],
    bg: "#090d16",
    dirFill: "#111827",
    dirStroke: "#1f2937",
    dirHeader: "#1f2937",
    iconColor: "#38bdf8"
  },
  plasma: {
    name: "Cyber Plasma",
    colors: ["#312e81", "#7e22ce", "#ea580c", "#facc15"],
    bg: "#0d0914",
    dirFill: "#171026",
    dirStroke: "#2e2145",
    dirHeader: "#2e2145",
    iconColor: "#c084fc"
  },
  emerald: {
    name: "Emerald Tech",
    colors: ["#064e3b", "#059669", "#10b981", "#a3e635"],
    bg: "#06120e",
    dirFill: "#0a1f18",
    dirStroke: "#14382c",
    dirHeader: "#14382c",
    iconColor: "#34d399"
  },
  volcano: {
    name: "Volcanic Sunset",
    colors: ["#450a0a", "#dc2626", "#ea580c", "#fbbf24"],
    bg: "#140808",
    dirFill: "#241010",
    dirStroke: "#3d1b1b",
    dirHeader: "#3d1b1b",
    iconColor: "#f87171"
  }
};

export default function HotspotTreemap({ hotspots, couplingData = [] }) {
  const width = 1200;
  const [mapHeight, setMapHeight] = useState(800);
  const [viewMode, setViewMode] = useState("nested");
  const [selectedTheme, setSelectedTheme] = useState("neon");

  const [hoveredLeaf, setHoveredLeaf] = useState(null);
  const [hoveredDir, setHoveredDir] = useState(null);

  const activeTheme = THEMES[selectedTheme] || THEMES.neon;

  // Build lookup map for temporal coupling
  const couplingLookup = useMemo(() => {
    const map = {};
    (couplingData || []).forEach(item => {
      if (!map[item.file_a]) map[item.file_a] = [];
      if (!map[item.file_b]) map[item.file_b] = [];
      map[item.file_a].push({ coupledFile: item.file_b, degree: item.degree, coChanges: item.co_changes });
      map[item.file_b].push({ coupledFile: item.file_a, degree: item.degree, coChanges: item.co_changes });
    });
    return map;
  }, [couplingData]);

  const activeCoupledFiles = useMemo(() => {
    if (!hoveredLeaf) return new Set();
    const list = couplingLookup[hoveredLeaf.path] || [];
    return new Set(list.map(x => x.coupledFile));
  }, [hoveredLeaf, couplingLookup]);

  const rootData = useMemo(() => {
    if (viewMode === "flat") {
      return {
        name: "root",
        children: (hotspots || []).map(h => ({
          name: h.file_path.split("/").pop() || h.file_path,
          path: h.file_path,
          value: Math.max((h.total_insertions || 0) + (h.total_deletions || 0), 1),
          commits: h.commits_count || 0,
          insertions: h.total_insertions || 0,
          deletions: h.total_deletions || 0,
          authors: h.authors || [],
          top_author: h.top_author,
          top_author_share: h.top_author_share,
          is_orphan_risk: h.is_orphan_risk,
          commit_types: h.commit_types || {},
        }))
      };
    }
    return buildTree(hotspots);
  }, [hotspots, viewMode]);

  const hierarchy = useMemo(() => {
    return d3.hierarchy(rootData)
      .sum(d => d.value || 0)
      .sort((a, b) => b.value - a.value);
  }, [rootData]);

  const root = useMemo(() => {
    const treemap = d3.treemap()
      .size([width, mapHeight])
      .tile(d3.treemapResquarify.ratio(1.1))
      .paddingOuter(viewMode === "nested" ? 10 : 5)
      .paddingTop(node => (node.children && viewMode === "nested" ? 34 : 0))
      .paddingInner(6)
      .round(true);
    return treemap(hierarchy);
  }, [hierarchy, width, mapHeight, viewMode]);

  const maxCommits = useMemo(() => d3.max(hotspots || [], d => d.commits_count) || 1, [hotspots]);

  const colorScale = useMemo(() => {
    const colors = activeTheme.colors;
    const domainStep = maxCommits / (colors.length - 1);
    const domain = colors.map((_, i) => i * domainStep);

    return d3.scaleLinear()
      .domain(domain)
      .range(colors)
      .interpolate(d3.interpolateRgb);
  }, [maxCommits, activeTheme]);

  const getTextColor = (commits) => {
    const colorStr = colorScale(commits);
    const hsl = d3.hsl(colorStr);
    return hsl.l < 0.65 ? "#ffffff" : "#090d16";
  };

  const handleExportSvg = () => {
    const svgElement = document.getElementById("gitcompass-treemap-svg");
    if (!svgElement) return;
    const svgData = new XMLSerializer().serializeToString(svgElement);
    const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "gitcompass_architecture_map.svg";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!hotspots || hotspots.length === 0) {
    return (
      <div className="card-flat h-[450px] flex items-center justify-center text-text-tertiary text-sm">
        No hotspot data available for visualization.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 shadow-2xl bg-[#090d16] text-slate-100 transition-all duration-300">
      {/* ── Header & Toolbar ────────────────────────────── */}
      <div className="px-6 py-5 border-b border-slate-800/80 bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 flex flex-col gap-4">
        {/* Top Row: Prominent Title & Description */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/60 pb-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0 shadow-2xs">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                </svg>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                Repository Architecture Map
              </h2>
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 shadow-2xs">
                {hotspots.length} files tracked
              </span>
            </div>
            <p className="text-sm font-medium text-slate-200 mt-2 max-w-4xl leading-relaxed">
              Enlarged structural map sized by code volume changes and colored by commit volatility.
            </p>
          </div>

          <button
            onClick={handleExportSvg}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 hover:text-white hover:bg-slate-700 text-xs font-semibold border border-slate-700 transition-colors shadow-2xs self-start sm:self-auto cursor-pointer"
          >
            <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export SVG
          </button>
        </div>

        {/* Bottom Row: Controls Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-1">
          {/* Theme Selector */}
          <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
            <span className="text-[11px] text-slate-400 pl-2 font-medium">Theme:</span>
            {Object.keys(THEMES).map(key => (
              <button
                key={key}
                onClick={() => setSelectedTheme(key)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                  selectedTheme === key
                    ? "bg-slate-800 text-cyan-300 font-semibold shadow-xs border border-slate-700"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {THEMES[key].name}
              </button>
            ))}
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center p-1 rounded-xl bg-slate-950 border border-slate-800">
            <button
              onClick={() => setViewMode("nested")}
              className={`px-3 py-1 rounded-lg text-[11px] font-medium transition-all ${
                viewMode === "nested"
                  ? "bg-slate-800 text-white font-semibold shadow-xs border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Nested Folders
            </button>
            <button
              onClick={() => setViewMode("flat")}
              className={`px-3 py-1 rounded-lg text-[11px] font-medium transition-all ${
                viewMode === "flat"
                  ? "bg-slate-800 text-white font-semibold shadow-xs border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Flat File Grid
            </button>
          </div>

          {/* Canvas Height Selector */}
          <div className="flex items-center p-1 rounded-xl bg-slate-950 border border-slate-800">
            <button
              onClick={() => setMapHeight(650)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                mapHeight === 650
                  ? "bg-slate-800 text-white font-semibold shadow-xs border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Standard
            </button>
            <button
              onClick={() => setMapHeight(800)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                mapHeight === 800
                  ? "bg-slate-800 text-white font-semibold shadow-xs border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Large
            </button>
            <button
              onClick={() => setMapHeight(1000)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                mapHeight === 1000
                  ? "bg-slate-800 text-white font-semibold shadow-xs border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Max Frame
            </button>
          </div>

          {/* Color Legend Bar */}
          <div className="flex items-center gap-1.5 shrink-0 pl-1">
            <span className="text-[11px] text-slate-400">Low</span>
            <div 
              className="w-20 h-2.5 rounded-full border border-slate-700/80 shadow-2xs" 
              style={{ 
                background: `linear-gradient(to right, ${activeTheme.colors[0]}, ${activeTheme.colors[1]}, ${activeTheme.colors[2]}, ${activeTheme.colors[3]})` 
              }}
            />
            <span className="text-[11px] text-slate-400">High Churn</span>
          </div>
        </div>
      </div>

      {/* ── Dynamic Hover Detail Bar ──────────────────────── */}
      <div className="px-6 py-3 bg-slate-950/80 border-b border-slate-800/80 text-xs min-h-[44px] flex items-center justify-between transition-colors">
        {hoveredLeaf ? (
          <div className="flex items-center gap-4 flex-wrap text-slate-200 w-full justify-between">
            <div className="flex items-center gap-2 truncate max-w-[55%]">
              <svg className="w-4 h-4 text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="font-semibold text-white text-sm truncate">{hoveredLeaf.path}</span>

              {hoveredLeaf.is_orphan_risk && (
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-950 text-rose-300 border border-rose-800 shrink-0">
                  Orphan Risk
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-3 shrink-0 text-slate-300 flex-wrap">
              {hoveredLeaf.top_author && (
                <span className="text-slate-300 text-xs font-medium">
                  Owner: <strong className="text-white">{hoveredLeaf.top_author}</strong> ({Math.round(hoveredLeaf.top_author_share * 100)}%)
                </span>
              )}
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-amber-950/80 text-amber-300 text-xs font-semibold border border-amber-800/60">
                {hoveredLeaf.commits} {hoveredLeaf.commits === 1 ? "commit" : "commits"}
              </span>
              <span className="text-emerald-400 font-semibold">+{(hoveredLeaf.insertions || 0).toLocaleString()}</span>
              <span className="text-rose-400 font-semibold">-{(hoveredLeaf.deletions || 0).toLocaleString()}</span>

              {activeCoupledFiles.size > 0 && (
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800 shrink-0 animate-pulse">
                  ⚡ {activeCoupledFiles.size} Coupled Files
                </span>
              )}
            </div>
          </div>
        ) : hoveredDir ? (
          <div className="flex items-center gap-2 text-slate-200">
            <svg className="w-4 h-4 text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 002 2z" />
            </svg>
            <span className="font-semibold text-white text-sm">{hoveredDir.name}</span>
            <span className="text-slate-400 text-xs">
              ({hoveredDir.leavesCount} files, {hoveredDir.totalCommits} total commits)
            </span>
          </div>
        ) : (
          <span className="text-slate-400 italic text-xs">
            Hover over any file block to inspect metrics & highlight temporal coupling dependencies.
          </span>
        )}
      </div>

      {/* ── Treemap SVG Canvas ────────────────────────────── */}
      <div className="p-6 bg-[#060911]">
        <svg 
          id="gitcompass-treemap-svg"
          viewBox={`0 0 ${width} ${mapHeight}`} 
          className="w-full h-auto drop-shadow-xl font-sans select-none overflow-visible"
        >
          {/* Layer 1: Directory Container Rectangles */}
          {viewMode === "nested" && root.descendants().filter(d => d.depth > 0 && d.children).map((node, i) => {
            const nodeWidth = node.x1 - node.x0;
            const nodeHeight = node.y1 - node.y0;
            const isHovered = hoveredDir?.name === node.data.name;

            return (
              <g 
                key={`dir-bg-${i}`} 
                transform={`translate(${node.x0},${node.y0})`}
                onMouseEnter={() => setHoveredDir({
                  name: node.data.name,
                  leavesCount: node.leaves().length,
                  totalCommits: d3.sum(node.leaves(), d => d.data.commits || 0)
                })}
                onMouseLeave={() => setHoveredDir(null)}
              >
                {/* Outer Directory Frame Box */}
                <rect
                  width={nodeWidth}
                  height={nodeHeight}
                  fill={isHovered ? "#162032" : activeTheme.dirFill}
                  stroke={isHovered ? "#38bdf8" : activeTheme.dirStroke}
                  strokeWidth={isHovered ? 1.5 : 1}
                  rx={8}
                  className="transition-colors duration-150"
                />
                {/* Directory Header Accent Bar */}
                <rect
                  width={nodeWidth}
                  height={Math.min(32, nodeHeight)}
                  fill={isHovered ? "#1e293b" : activeTheme.dirHeader}
                  rx={7}
                  className="transition-colors duration-150"
                >
                  <title>{`Directory: ${node.data.name}\n${node.leaves().length} files`}</title>
                </rect>
              </g>
            );
          })}

          {/* Layer 2: File Leaf Blocks */}
          {root.leaves().map((leaf, i) => {
            const blockWidth = leaf.x1 - leaf.x0;
            const blockHeight = leaf.y1 - leaf.y0;
            const isHovered = hoveredLeaf?.path === leaf.data.path;
            const isCoupled = activeCoupledFiles.has(leaf.data.path);

            const textColor = getTextColor(leaf.data.commits);
            const showTitle = blockWidth > 26 && blockHeight > 16;
            const showSubtitle = blockHeight > 42 && blockWidth > 55;

            let strokeColor = "rgba(255, 255, 255, 0.12)";
            let strokeWidth = 1;
            if (isHovered) {
              strokeColor = "#ffffff";
              strokeWidth = 2.5;
            } else if (isCoupled) {
              strokeColor = "#38bdf8";
              strokeWidth = 3;
            }

            return (
              <g 
                key={`leaf-${i}`} 
                transform={`translate(${leaf.x0},${leaf.y0})`}
                onMouseEnter={() => setHoveredLeaf(leaf.data)}
                onMouseLeave={() => setHoveredLeaf(null)}
                className="cursor-pointer"
              >
                <rect
                  width={blockWidth}
                  height={blockHeight}
                  fill={colorScale(leaf.data.commits)}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  rx={4}
                  className={`transition-all duration-150 ${isCoupled ? "brightness-125" : "hover:brightness-115"}`}
                >
                  <title>{`${leaf.data.path}\nCommits: ${leaf.data.commits}\nVolume: +${leaf.data.insertions} / -${leaf.data.deletions}${leaf.data.is_orphan_risk ? "\n[Orphan Risk Flagged]" : ""}`}</title>
                </rect>
                
                {showTitle && (
                  <foreignObject
                    x={0}
                    y={0}
                    width={blockWidth}
                    height={blockHeight}
                    className="pointer-events-none"
                  >
                    <div className="w-full h-full p-1.5 flex flex-col justify-between overflow-hidden select-none">
                      <div className="flex items-center justify-between gap-1">
                        <span 
                          className="font-semibold text-xs leading-tight truncate drop-shadow-xs"
                          style={{ color: textColor }}
                        >
                          {leaf.data.name}
                        </span>
                        {leaf.data.is_orphan_risk && (
                          <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" title="Orphan Risk" />
                        )}
                      </div>

                      {showSubtitle && (
                        <div 
                          className="text-[10px] font-medium leading-tight opacity-90 truncate"
                          style={{ color: textColor }}
                        >
                          {leaf.data.commits} {leaf.data.commits === 1 ? "commit" : "commits"}
                        </div>
                      )}
                    </div>
                  </foreignObject>
                )}
              </g>
            );
          })}

          {/* Layer 3: Directory Header Titles (Layered ON TOP so never covered) */}
          {viewMode === "nested" && root.descendants().filter(d => d.depth > 0 && d.children).map((node, i) => {
            const nodeWidth = node.x1 - node.x0;
            const nodeHeight = node.y1 - node.y0;

            if (nodeWidth <= 24 || nodeHeight <= 18) return null;

            return (
              <foreignObject
                key={`dir-title-${i}`}
                x={node.x0 + 8}
                y={node.y0 + 4}
                width={Math.max(nodeWidth - 16, 0)}
                height={26}
                className="pointer-events-none"
              >
                <div 
                  className="flex items-center gap-1.5 h-full overflow-hidden text-ellipsis whitespace-nowrap select-none"
                  title={`Directory: ${node.data.name}`}
                >
                  <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ color: activeTheme.iconColor }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 002 2z" />
                  </svg>
                  <span className="text-xs sm:text-sm font-bold text-slate-200 tracking-tight truncate">
                    {node.data.name}
                  </span>
                </div>
              </foreignObject>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
