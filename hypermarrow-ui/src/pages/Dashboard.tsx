import React, { useState, useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { Brain, GitGraph, Shield, Activity, Users, Search, Share2, Download, Sun, Moon } from 'lucide-react'

const API = 'http://localhost:8741/api/v1'

async function fetchJSON(path: string) {
  const r = await fetch(`${API}${path}`)
  return r.json()
}

function KPICard({ icon: Icon, label, value, sub, color, dark }: any) {
  return (
    <div style={{ background: dark ? '#161b22' : '#fff', borderRadius: 12, padding: '20px 24px', border: `1px solid ${dark ? '#21262d' : '#d0d7de'}`, display: 'flex', alignItems: 'center', gap: 16, flex: 1, minWidth: 200 }}>
      <div style={{ width: 44, height: 44, borderRadius: 10, background: `${color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon size={22} color={color} />
      </div>
      <div>
        <div style={{ fontSize: 12, color: dark ? '#8b949e' : '#656d76', marginBottom: 4 }}>{label}</div>
        <div style={{ fontSize: 26, fontWeight: 700, color: dark ? '#e6edf3' : '#1f2328' }}>{value}</div>
        {sub && <div style={{ fontSize: 11, color: dark ? '#8b949e' : '#656d76', marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  )
}

function ForceGraph({ data, dark, width = 600, height = 400 }: any) {
  const svgRef = useRef<SVGSVGElement>(null)
  useEffect(() => {
    if (!data || !svgRef.current) return
    const svg = d3.select(svgRef.current); svg.selectAll('*').remove()
    const nodes = data.nodes?.slice(0, 40) || []
    const edges = (data.edges || []).filter((e: any) => nodes.find((n: any) => n.id === e.source) && nodes.find((n: any) => n.id === e.target)).slice(0, 60)

    const sim = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(edges).id((d: any) => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))

    const color = d3.scaleOrdinal<string>()
      .domain(['tool', 'skill', 'concept', 'phase', 'error_type', 'action'])
      .range(['#58a6ff', '#3fb950', '#d2a8ff', '#f0883e', '#f85149', '#8b949e'])

    const link = svg.append('g').selectAll('line').data(edges).join('line')
      .attr('stroke', dark ? '#21262d' : '#d0d7de').attr('stroke-width', (d: any) => d.weight * 3)

    const node = svg.append('g').selectAll('circle').data(nodes).join('circle')
      .attr('r', (d: any) => d.central ? 8 : 5)
      .attr('fill', (d: any) => color(d.type))
      .call(d3.drag<SVGCircleElement, any>().on('start', (e: any, d: any) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag', (e: any, d: any) => { d.fx = e.x; d.fy = e.y })
        .on('end', (e: any, d: any) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null }))

    const label = svg.append('g').selectAll('text').data(nodes.slice(0, 20)).join('text')
      .text((d: any) => d.name.length > 15 ? d.name.slice(0, 14) + '…' : d.name)
      .attr('font-size', 9).attr('dx', 8).attr('dy', 3)
      .attr('fill', dark ? '#8b949e' : '#656d76')

    sim.on('tick', () => {
      link.attr('x1', (d: any) => d.source.x).attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x).attr('y2', (d: any) => d.target.y)
      node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y)
      label.attr('x', (d: any) => d.x).attr('y', (d: any) => d.y)
    })
  }, [data, dark])

  return <svg ref={svgRef} width={width} height={height} style={{ borderRadius: 12, background: dark ? '#0d1117' : '#fff' }} />
}

export default function Dashboard({ dark }: { dark: boolean }) {
  const [stats, setStats] = useState<any>(null)
  const [graph, setGraph] = useState<any>(null)
  const [rules, setRules] = useState<any[]>([])
  const [searchQ, setSearchQ] = useState('')
  const [searchResult, setSearchResult] = useState<any>(null)

  useEffect(() => {
    fetchJSON('/stats').then(setStats)
    fetchJSON('/kg/graph').then(setGraph)
    fetchJSON('/pm/rules').then(setRules)
    const ws = new WebSocket('ws://localhost:8741/ws')
    ws.onmessage = (e) => { const d = JSON.parse(e.data); setStats((s: any) => s ? { ...s, ql: { ...s.ql, nonzero: d.ql_nonzero, buffer: d.ql_buffer }, meta: { ...s.meta, health: d.health, accuracy: d.accuracy } } : s) }
    return () => ws.close()
  }, [])

  const doSearch = async () => {
    if (!searchQ) return
    const r = await fetchJSON(`/search?q=${encodeURIComponent(searchQ)}&limit=5`)
    setSearchResult(r)
  }

  if (!stats) return <div style={{ padding: 40, textAlign: 'center', color: '#58a6ff' }}>Loading Crystal Core…</div>

  const kpis = [
    { icon: GitGraph, label: 'Knowledge Graph', value: stats.kg.entities, sub: `${stats.kg.relationships} relationships`, color: '#58a6ff' },
    { icon: Shield, label: 'Procedural Rules', value: stats.pm.rules, sub: 'automation levels', color: '#3fb950' },
    { icon: Brain, label: 'Q-Learning', value: `${stats.ql.nonzero}/${stats.ql.total}`, sub: `${stats.ql.nonzero_pct}% non-zero`, color: '#d2a8ff' },
    { icon: Activity, label: 'Health Score', value: `${stats.meta.score?.toFixed(0) || '?'}%`, sub: `${stats.meta.health} · ECE ${stats.meta.ece?.toFixed(3)}`, color: '#f0883e' },
  ]

  return (
    <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      {/* KPI Cards */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        {kpis.map((k, i) => <KPICard key={i} {...k} dark={dark} />)}
      </div>

      {/* Knowledge Graph + Rules */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ flex: 2, minWidth: 500, background: dark ? '#161b22' : '#fff', borderRadius: 12, padding: 16, border: `1px solid ${dark ? '#21262d' : '#d0d7de'}` }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600, color: dark ? '#e6edf3' : '#1f2328' }}>Knowledge Graph</h3>
          {graph && <ForceGraph data={graph} dark={dark} />}
        </div>
        <div style={{ flex: 1, minWidth: 260, background: dark ? '#161b22' : '#fff', borderRadius: 12, padding: 16, border: `1px solid ${dark ? '#21262d' : '#d0d7de'}`, maxHeight: 440, overflowY: 'auto' }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600, color: dark ? '#e6edf3' : '#1f2328' }}>Top Rules</h3>
          {rules.slice(0, 12).map((r: any, i: number) => (
            <div key={i} style={{ padding: '8px 0', borderBottom: `1px solid ${dark ? '#21262d' : '#d0d7de'}` }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: dark ? '#e6edf3' : '#1f2328' }}>{r.name}</div>
              <div style={{ display: 'flex', gap: 12, fontSize: 11, color: dark ? '#8b949e' : '#656d76', marginTop: 4 }}>
                <span>L{r.level}</span><span>SR {(r.success_rate * 100).toFixed(0)}%</span><span>{r.attempts} attempts</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Search + Agents */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 300, background: dark ? '#161b22' : '#fff', borderRadius: 12, padding: 16, border: `1px solid ${dark ? '#21262d' : '#d0d7de'}` }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600, color: dark ? '#e6edf3' : '#1f2328' }}>Search Memory</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && doSearch()}
              placeholder="Search entities, episodes…" style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: `1px solid ${dark ? '#30363d' : '#d0d7de'}`, background: dark ? '#0d1117' : '#f6f8fa', color: dark ? '#e6edf3' : '#1f2328', fontSize: 13 }} />
            <button onClick={doSearch} style={{ padding: '8px 16px', borderRadius: 8, background: '#58a6ff', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13 }}>Search</button>
          </div>
          {searchResult && (
            <div style={{ marginTop: 12 }}>
              {searchResult.kg?.map((e: any, i: number) => <div key={`kg-${i}`} style={{ fontSize: 12, padding: '4px 0', color: dark ? '#8b949e' : '#656d76' }}>[{e.type}] {e.name}</div>)}
              {searchResult.em?.map((e: any, i: number) => <div key={`em-${i}`} style={{ fontSize: 12, padding: '4px 0', color: dark ? '#8b949e' : '#656d76' }}>[{e.outcome}] {e.what}</div>)}
            </div>
          )}
        </div>

        <div style={{ flex: 1, minWidth: 260, background: dark ? '#161b22' : '#fff', borderRadius: 12, padding: 16, border: `1px solid ${dark ? '#21262d' : '#d0d7de'}` }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600, color: dark ? '#e6edf3' : '#1f2328' }}>Agents</h3>
          {stats.agents?.map((aid: string) => (
            <div key={aid} style={{ padding: '8px 0', borderBottom: `1px solid ${dark ? '#21262d' : '#d0d7de'}`, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Users size={16} color="#58a6ff" />
              <span style={{ fontSize: 13, fontWeight: 500, color: dark ? '#e6edf3' : '#1f2328' }}>{aid}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Share/Export bar */}
      <div style={{ display: 'flex', gap: 12, marginTop: 24, justifyContent: 'center' }}>
        <button style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 20px', borderRadius: 8, background: dark ? '#21262d' : '#eaeef2', border: 'none', color: dark ? '#e6edf3' : '#1f2328', cursor: 'pointer', fontSize: 13 }}>
          <Share2 size={16} /> Share Card
        </button>
        <button style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 20px', borderRadius: 8, background: dark ? '#21262d' : '#eaeef2', border: 'none', color: dark ? '#e6edf3' : '#1f2328', cursor: 'pointer', fontSize: 13 }}>
          <Download size={16} /> Export Data
        </button>
      </div>
    </div>
  )
}
