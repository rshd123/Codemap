import ForceGraph2D from 'react-force-graph-2d'
import { useSearch } from '../context/SearchContext'

const NODE_COLORS = {
  Package: '#3b82f6',
  Vulnerability: '#ef4444',
  Issue: '#eab308',
  Commit: '#22c55e',
}

function nodeColor(node) {
  const type = node.label || node.type || 'Package'
  return NODE_COLORS[type] || '#3b82f6'
}

function nodeRadius(node) {
  return node.label === 'Vulnerability' ? 8 : 6
}

export default function GraphVisualization() {
  const { graphData, selectNode } = useSearch()
  const nodes = graphData?.nodes || []
  const links = graphData?.links || []

  if (nodes.length === 0) {
    return (
      <div className="flex h-full min-h-[320px] items-center justify-center rounded-xl border border-navy-700 bg-navy-900/60">
        <p className="text-sm text-slate-500">
          No graph data yet — run a search to visualize dependencies.
        </p>
      </div>
    )
  }

  return (
    <div className="h-full min-h-[420px] w-full overflow-hidden rounded-xl border border-navy-700 bg-navy-900/60">
      <ForceGraph2D
        graphData={{ nodes, links }}
        nodeId="id"
        linkSource="source"
        linkTarget="target"
        backgroundColor="#071225"
        nodeColor={nodeColor}
        nodeVal={nodeRadius}
        nodeRelSize={4}
        nodeLabel={(n) => `${n.label || 'Node'}: ${n.name || n.id || ''}`}
        linkColor={() => '#1a3a6b'}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkCanvasObjectMode={() => 'after'}
        linkCanvasObject={(link, ctx, globalScale) => {
          if (typeof link.source !== 'object' || typeof link.target !== 'object') return
          const x = (link.source.x + link.target.x) / 2
          const y = (link.source.y + link.target.y) / 2
          const fontSize = Math.max(10 / globalScale, 4)
          ctx.font = `${fontSize}px ui-sans-serif, system-ui, sans-serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillStyle = '#7f9cc4'
          ctx.fillText(link.type || '', x, y)
        }}
        onNodeClick={(node) => selectNode(node)}
        onBackgroundClick={() => selectNode(null)}
        cooldownTicks={100}
      />
    </div>
  )
}
