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
      .paddingTop(24) // Space for directory labels
      .paddingRight(2)
      .paddingInner(2)
      .paddingOuter(4)
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
          {/* Render Directory Labels */}
          {root.descendants().filter(d => d.depth > 0 && d.children && d.y1 - d.y0 > 24).map((node, i) => (
            <g key={`dir-${i}`} transform={`translate(${node.x0},${node.y0})`}>
              <text 
                x={4} 
                y={16} 
                fill="#64748b" 
                fontSize={12} 
                fontWeight="600" 
                className="pointer-events-none select-none"
              >
                {node.data.name}
              </text>
            </g>
          ))}

          {/* Render File Leaves */}
          {root.leaves().map((leaf, i) => {
            const blockWidth = leaf.x1 - leaf.x0;
            const blockHeight = leaf.y1 - leaf.y0;
            
            // Only render text if the block is large enough
            const showText = blockWidth > 40 && blockHeight > 18;

            return (
              <g key={`leaf-${i}`} transform={`translate(${leaf.x0},${leaf.y0})`}>
                <rect
                  width={blockWidth}
                  height={blockHeight}
                  fill={colorScale(leaf.data.commits)}
                  stroke="#ffffff"
                  strokeWidth={1}
                  rx={2} // Slight rounding for a minimalist, modern feel
                  className="hover:opacity-80 transition-opacity cursor-pointer stroke-white/50"
                >
                  <title>{`${leaf.data.path}\nCommits: ${leaf.data.commits}\nVolume (Lines Changed): ${leaf.data.value}`}</title>
                </rect>
                
                {showText && (
                  <text 
                    x={4} 
                    y={14} 
                    fill={leaf.data.commits > maxCommits * 0.6 ? "#fff" : "#1e293b"} // Contrast text for dark blocks
                    fontSize={10} 
                    className="pointer-events-none select-none overflow-hidden"
                  >
                    {leaf.data.name.length > blockWidth / 6 ? leaf.data.name.substring(0, Math.floor(blockWidth / 6)) + '…' : leaf.data.name}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
