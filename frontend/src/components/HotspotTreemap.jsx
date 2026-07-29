import { useMemo } from "react";
import * as d3 from "d3";

function buildTree(hotspots) {
  const root = { name: "root", children: [] };
  
  hotspots.forEach(hotspot => {
    const parts = hotspot.file_path.split("/");
    let currentLevel = root.children;
    
    parts.forEach((part, index) => {
      if (index === parts.length - 1) {
        currentLevel.push({
          name: part,
          path: hotspot.file_path,
          value: Math.max(hotspot.total_insertions + hotspot.total_deletions, 1),
          commits: hotspot.commits_count,
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

export default function HotspotTreemap({ hotspots }) {
  const width = 1000;
  const height = 500;

  const rootData = useMemo(() => buildTree(hotspots), [hotspots]);

  const hierarchy = useMemo(() => {
    return d3.hierarchy(rootData)
      .sum(d => d.value || 0)
      .sort((a, b) => b.value - a.value);
  }, [rootData]);

  const root = useMemo(() => {
    const treemap = d3.treemap()
      .size([width, height])
      .paddingTop(node => (node.children ? 28 : 0)) // Reserve 28px at the top of parent directories
      .paddingInner(4)                             // 4px spacing between sibling boxes
      .paddingOuter(6)                             // 6px padding inside container borders
      .round(true);
    return treemap(hierarchy);
  }, [hierarchy, width, height]);

  // Heatmap color scale based on commit frequency
  // Using a clean, non-gamery Orange/Red gradient for hotspots
  const maxCommits = d3.max(hotspots, d => d.commits_count) || 1;
  const colorScale = d3.scaleSequential(d3.interpolateOranges).domain([0, maxCommits]);

  if (!hotspots || hotspots.length === 0) {
    return (
      <div className="card-flat h-[400px] flex items-center justify-center text-text-tertiary text-sm">
        No hotspot data available for visualization.
      </div>
    );
  }

  return (
    <div className="card-flat overflow-hidden bg-white">
      <div className="px-6 py-4 border-b border-border bg-surface-hover/30">
        <h2 className="text-sm font-semibold text-text-primary">Repository Architecture Map</h2>
        <p className="text-xs text-text-tertiary mt-0.5">
          Blocks are sized by total code volume changed and colored by commit churn (darker = more volatile).
        </p>
      </div>
      <div className="p-4">
        <svg 
          viewBox={`0 0 ${width} ${height}`} 
          className="w-full h-auto drop-shadow-sm font-sans"
        >
          {/* Render Parent Directory Containers */}
          {root.descendants().filter(d => d.depth > 0 && d.children).map((node, i) => {
            const nodeWidth = node.x1 - node.x0;
            const nodeHeight = node.y1 - node.y0;
            const showText = nodeWidth > 40;

            return (
              <g key={`dir-rect-${i}`} transform={`translate(${node.x0},${node.y0})`}>
                <rect
                  width={nodeWidth}
                  height={nodeHeight}
                  fill="#f8fafc" // Subtle slate background
                  stroke="#cbd5e1" // Soft border
                  strokeWidth={1}
                  rx={4}
                  className="pointer-events-none"
                />
                
                {showText && (
                  <text
                    x={8}
                    y={18}
                    fill="#64748b"
                    fontSize={12}
                    fontWeight="600"
                    className="pointer-events-none select-none"
                  >
                    {node.data.name}
                  </text>
                )}
              </g>
            );
          })}

          {/* Render File Leaves */}
          {root.leaves().map((leaf, i) => {
            const blockWidth = leaf.x1 - leaf.x0;
            const blockHeight = leaf.y1 - leaf.y0;
            
            // Only render text if the block is large enough
            const showText = blockWidth > 45 && blockHeight > 22;

            return (
              <g key={`leaf-${i}`} transform={`translate(${leaf.x0},${leaf.y0})`}>
                <rect
                  width={blockWidth}
                  height={blockHeight}
                  fill={colorScale(leaf.data.commits)}
                  stroke="#ffffff"
                  strokeWidth={1}
                  rx={2}
                  className="hover:opacity-80 transition-opacity cursor-pointer stroke-white/50"
                >
                  <title>{`${leaf.data.path}\nCommits: ${leaf.data.commits}\nVolume (Lines Changed): ${leaf.data.value}`}</title>
                </rect>
                
                {showText && (
                  <foreignObject
                    x={0}
                    y={0}
                    width={blockWidth}
                    height={blockHeight}
                    className="pointer-events-none"
                  >
                    <div 
                      className="w-full h-full p-1.5 overflow-hidden break-words text-[10px] leading-[1.2] select-none"
                      style={{ 
                        color: leaf.data.commits > maxCommits * 0.6 ? "#ffffff" : "#1e293b" 
                      }}
                    >
                      {leaf.data.name}
                    </div>
                  </foreignObject>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
