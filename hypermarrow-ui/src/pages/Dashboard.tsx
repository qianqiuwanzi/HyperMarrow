import React, { useState, useEffect, useRef } from 'react'
import * as d3 from 'd3'

const API = 'http://localhost:8741/api/v1'
const F = (p: string) => fetch(`${API}${p}`).then(r => r.json()).catch(() => null)

const cardStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg,rgba(15,30,60,0.85),rgba(20,40,80,0.7))',
  borderRadius:14, padding:'18px 20px',
  border:'1px solid rgba(80,150,255,0.12)', backdropFilter:'blur(8px)',
}

function KPICard({ label, value, sub, accent }: { label:string, value:any, sub?:string, accent?:string }) {
  return (
    <div style={{...cardStyle, flex:1, minWidth:170, borderTop:`3px solid ${accent||'#60a5fa'}`}}>
      <div style={{fontSize:12,color:'rgba(160,200,240,0.7)',marginBottom:6}}>{label}</div>
      <div style={{fontSize:30,fontWeight:800,color:'#e0e8f0'}}>{value ?? '—'}</div>
      {sub ? <div style={{fontSize:11,color:'rgba(140,180,220,0.5)',marginTop:4}}>{sub}</div> : null}
    </div>
  )
}

function Section({ title, children }: { title:string, children:React.ReactNode }) {
  return (
    <div style={{...cardStyle, marginBottom:18}}>
      <h3 style={{margin:'0 0 14px',fontSize:14,fontWeight:600,color:'rgba(130,180,240,0.9)',letterSpacing:1,borderBottom:'1px solid rgba(80,150,255,0.1)',paddingBottom:8}}>{title}</h3>
      {children}
    </div>
  )
}

function Badge({ text, color }: { text:string, color?:string }) {
  return <span style={{display:'inline-block',padding:'2px 8px',borderRadius:10,fontSize:10,fontWeight:600,
    background:`${color||'#60a5fa'}22`,color:color||'#60a5fa',border:`1px solid ${color||'#60a5fa'}33`,marginRight:4}}>{text}</span>
}

function ForceGraph({ data, w = 580, h = 380 }: { data:any, w?:number, h?:number }) {
  const svgRef = useRef<SVGSVGElement>(null)
  useEffect(() => {
    if (!data?.nodes?.length || !svgRef.current) return
    const svg = d3.select(svgRef.current); svg.selectAll('*').remove()
    const nodes = (data.nodes || []).slice(0, 50)
    const edges = (data.edges || []).filter((e:any) =>
      nodes.find((n:any) => n.id === e.source) && nodes.find((n:any) => n.id === e.target)
    ).slice(0, 80)

    const sim = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(edges).id((d:any) => d.id).distance(70))
      .force('charge', d3.forceManyBody().strength(-180))
      .force('center', d3.forceCenter(w / 2, h / 2))

    const color = d3.scaleOrdinal<string>()
      .domain(['tool','skill','concept','phase','error_type','action'])
      .range(['#60a5fa','#34d399','#a78bfa','#fbbf24','#f87171','#94a3b8'])

    svg.append('g').selectAll('line').data(edges).join('line')
      .attr('stroke', 'rgba(80,150,255,0.25)').attr('stroke-width', (d:any) => d.weight * 3)

    const node = svg.append('g').selectAll('circle').data(nodes).join('circle')
      .attr('r', (d:any) => d.central ? 9 : 5).attr('fill', (d:any) => color(d.type))
      .attr('stroke', 'rgba(255,255,255,0.2)').attr('stroke-width', 1.5)
      .call(d3.drag<any,any>()
        .on('start', (e:any, d:any) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag', (e:any, d:any) => { d.fx = e.x; d.fy = e.y })
        .on('end', (e:any, d:any) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null }))

    svg.append('g').selectAll('text').data(nodes.slice(0, 25)).join('text')
      .text((d:any) => d.name && d.name.length > 14 ? d.name.slice(0, 13) + '…' : (d.name || ''))
      .attr('font-size', 9).attr('dx', 8).attr('dy', 3).attr('fill', 'rgba(160,200,240,0.6)')

    sim.on('tick', () => {
      svg.selectAll('line').attr('x1', (d:any) => d.source.x).attr('y1', (d:any) => d.source.y)
        .attr('x2', (d:any) => d.target.x).attr('y2', (d:any) => d.target.y)
      node.attr('cx', (d:any) => d.x).attr('cy', (d:any) => d.y)
      svg.selectAll('text').attr('x', (d:any) => d.x).attr('y', (d:any) => d.y)
    })
  }, [data, w, h])

  return <svg ref={svgRef} width={w} height={h} style={{ borderRadius: 12 }} />
}

export default function Dashboard() {
  const [mem, setMem] = useState<any>({})
  const [lrn, setLrn] = useState<any>({})
  const [graph, setGraph] = useState<any>(null)
  const [rules, setRules] = useState<any[]>([])
  const [episodes, setEpisodes] = useState<any[]>([])
  const [agents, setAgents] = useState<any[]>([])
  const [heatmap, setHeatmap] = useState<any>(null)
  const [calibration, setCalibration] = useState<any>(null)
  const [dream, setDream] = useState<any>(null)
  const [skills, setSkills] = useState<any[]>([])
  const [searchQ, setSearchQ] = useState('')
  const [searchR, setSearchR] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      F('/memory/overview'), F('/learning/overview'), F('/kg/graph'),
      F('/pm/rules'), F('/em/timeline?limit=60'), F('/agents'),
      F('/ql/heatmap'), F('/meta/calibration'), F('/dream/status'),
      F('/skills/list')
    ]).then(([memR, lrnR, graphR, rulesR, epR, agR, hmR, calR, dreamR, skR]) => {
      if (!memR && !lrnR) { setError('无法连接后端 API (localhost:8741)'); setLoading(false); return }
      setMem(memR || {})
      setLrn(lrnR || {})
      setGraph(graphR)
      setRules(rulesR || [])
      setEpisodes(epR || [])
      setAgents(agR || [])
      setHeatmap(hmR)
      setCalibration(calR)
      setDream(dreamR)
      setSkills(Object.values(skR || {}))
      setLoading(false)
    }).catch((e: any) => {
      setError(`加载失败: ${e.message}`)
      setLoading(false)
    })

    let ws: WebSocket
    try {
      ws = new WebSocket('ws://localhost:8741/ws')
      ws.onmessage = e => {
        const d = JSON.parse(e.data)
        setLrn((p: any) => p?.q_learning ? {
          ...p, q_learning: { ...p.q_learning, nonzero: d.ql_nonzero, buffer: d.ql_buffer },
          metacognition: { ...p.metacognition, health: d.health, accuracy: d.accuracy, score: d.score }
        } : p)
      }
    } catch { /* WebSocket optional */ }
    return () => { try { ws?.close() } catch { } }
  }, [])

  const doSearch = async () => {
    if (!searchQ) return
    setSearchR(await F(`/search?q=${encodeURIComponent(searchQ)}&limit=8`))
  }

  if (loading) {
    return <div style={{ padding: 80, textAlign: 'center' }}>
      <div style={{ fontSize: 28, fontWeight: 800, background: 'linear-gradient(90deg,#60a5fa,#818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
        藏慧晶核启动中…
      </div>
      <div style={{ marginTop: 12, color: 'rgba(160,200,240,0.5)', fontSize: 13 }}>正在连接 localhost:8741</div>
    </div>
  }

  if (error) {
    return <div style={{ padding: 80, textAlign: 'center' }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#f87171' }}>连接失败</div>
      <div style={{ marginTop: 8, color: 'rgba(160,200,240,0.5)', fontSize: 13 }}>{error}</div>
      <div style={{ marginTop: 16, color: 'rgba(160,200,240,0.4)', fontSize: 12 }}>
        请确认后端已启动：<code style={{background:'rgba(255,255,255,0.05)',padding:'4px 8px',borderRadius:4}}>python start_server.py</code>
      </div>
    </div>
  }

  const m: any = mem || {}; const l: any = lrn || {}
  const kpis = [
    { label: '知识图谱', value: m?.knowledge_graph?.entities ?? '—', sub: `${m?.knowledge_graph?.relationships ?? 0} 条关系`, accent: '#60a5fa' },
    { label: '程序规则', value: m?.procedural_memory?.total_rules ?? '—', sub: '5级自动化', accent: '#34d399' },
    { label: '情景记忆', value: m?.p3_episodic_memory?.total ?? '—', sub: `重要性 ${m?.p3_episodic_memory?.avg_importance ?? 0}`, accent: '#a78bfa' },
    { label: 'Q学习', value: `${l?.q_learning?.nonzero ?? '?'}/${l?.q_learning?.total ?? '?'}`, sub: `Buffer ${l?.q_learning?.buffer ?? 0}`, accent: '#fbbf24' },
    { label: '健康分', value: `${l?.metacognition?.score?.toFixed(0) ?? '?'}%`, sub: `${l?.metacognition?.health ?? '?'} · ECE ${l?.metacognition?.ece?.toFixed(3) ?? '?'}`, accent: '#f87171' },
    { label: '向量记忆', value: m?.p2_vector_memory?.total_vectors ?? 0, sub: m?.p2_vector_memory?.collection || 'ChromaDB', accent: '#38bdf8' },
  ]

  return (
    <div style={{ padding: '20px 28px', maxWidth: 1400, margin: '0 auto' }}>
      {/* KPI Cards */}
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 18 }}>
        {kpis.map((k, i) => <KPICard key={i} {...k} />)}
      </div>

      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
        {/* Left column */}
        <div style={{ flex: 2, minWidth: 550 }}>
          <Section title="🧠 知识图谱">
            {graph?.nodes?.length ? <ForceGraph data={graph} /> : <div style={{ color: 'rgba(160,200,240,0.3)', padding: 40, textAlign: 'center' }}>暂无图谱数据</div>}
          </Section>

          <Section title="🎯 Q学习热力图">
            {heatmap?.rows?.length ? (
              <div style={{ overflowX: 'auto' }}>
                <div style={{ display: 'flex', marginBottom: 6, gap: 4 }}>
                  <div style={{ width: 40 }} />
                  {(heatmap.actions || []).map((a: string, i: number) => (
                    <div key={i} style={{ flex: 1, fontSize: 10, color: 'rgba(160,200,240,0.6)', textAlign: 'center', minWidth: 60 }}>{a}</div>
                  ))}
                </div>
                {(heatmap.rows || []).slice(0, 15).map((row: any, i: number) => (
                  <div key={i} style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 2 }}>
                    <div style={{ width: 40, fontSize: 10, color: 'rgba(160,200,240,0.5)' }}>S{row.state}</div>
                    {(row.values || []).map((v: number, j: number) => {
                      const intensity = Math.min(1, Math.abs(v) / 0.5)
                      const hue = v > 0 ? '34,211,144' : '248,113,113'
                      return (
                        <div key={j} style={{
                          flex: 1, height: 14, minWidth: 60, borderRadius: 3,
                          background: `rgba(${hue},${intensity * 0.8})`,
                          border: j === row.best ? '1px solid rgba(255,255,255,0.4)' : 'none',
                          fontSize: 8, color: 'rgba(255,255,255,0.7)', textAlign: 'center', lineHeight: '14px'
                        }}>{v.toFixed(2)}</div>
                      )
                    })}
                  </div>
                ))}
              </div>
            ) : <div style={{ color: 'rgba(160,200,240,0.3)', padding: 20, textAlign: 'center' }}>暂无Q表数据</div>}
          </Section>

          <Section title="📅 情景记忆时间线">
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {episodes.length > 0 ? episodes.slice(0, 25).map((e: any, i: number) => (
                <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid rgba(80,150,255,0.06)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Badge text={e.outcome || '?'} color={e.outcome === 'success' ? '#34d399' : e.outcome === 'failure' ? '#f87171' : '#94a3b8'} />
                  <span style={{ fontSize: 12, flex: 1 }}>{e.what || ''}</span>
                  <span style={{ fontSize: 10, color: 'rgba(160,200,240,0.4)' }}>{(e.when || '').slice(0, 10)}</span>
                </div>
              )) : <div style={{ color: 'rgba(160,200,240,0.3)', padding: 20, textAlign: 'center' }}>暂无情景记录</div>}
            </div>
          </Section>
        </div>

        {/* Right column */}
        <div style={{ flex: 1, minWidth: 340 }}>
          <Section title="📦 记忆系统 (P1/P2/P3/PM)">
            <div style={{ fontSize: 12, lineHeight: 2.2 }}>
              <div><b style={{ color: '#60a5fa' }}>P1 工作记忆：</b>任务={m?.p1_working_memory?.task || '无'}，栈深={m?.p1_working_memory?.stack_depth ?? 0}</div>
              <div><b style={{ color: '#38bdf8' }}>P2 向量记忆：</b>{m?.p2_vector_memory?.total_vectors ?? 0} 向量，维度 {m?.p2_vector_memory?.embedding_dim ?? 0}</div>
              <div><b style={{ color: '#a78bfa' }}>P3 情景记忆：</b>{m?.p3_episodic_memory?.total ?? 0} 条，含教训 {m?.p3_episodic_memory?.with_lessons ?? 0} 条</div>
              <div><b style={{ color: '#34d399' }}>程序记忆：</b>{m?.procedural_memory?.total_rules ?? 0} 条规则</div>
              <div><b style={{ color: '#d4d4d8' }}>前瞻记忆：</b>{m?.prospective?.active ?? 0} 活跃意图</div>
            </div>
          </Section>

          <Section title="🧬 学习系统 (QL/Meta/Consolidation)">
            <div style={{ fontSize: 12, lineHeight: 2.2 }}>
              <div><b style={{ color: '#fbbf24' }}>Q学习：</b>{l?.q_learning?.nonzero ?? '?'}/{l?.q_learning?.total ?? '?'} 非零 (α={l?.q_learning?.alpha ?? '?'}, ε={l?.q_learning?.epsilon ?? '?'})</div>
              <div><b style={{ color: '#f87171' }}>元认知：</b>健康{l?.metacognition?.health ?? '?'}，决策{l?.metacognition?.decisions ?? 0}次，异常{l?.metacognition?.anomalies ?? 0}个</div>
              <div><b style={{ color: '#34d399' }}>巩固：</b>{l?.consolidation?.total ?? 0}次，LTP+{l?.consolidation?.ltp_total ?? 0}，LTD-{l?.consolidation?.ltd_total ?? 0}</div>
              <div><b style={{ color: '#818cf8' }}>迁移：</b>{l?.transfer?.total_transfers ?? 0}次迁移，{l?.transfer?.total_profiles ?? 0}档案</div>
              {(l?.neural?.train_steps ?? 0) > 0 ? <div><b style={{ color: '#a78bfa' }}>神经模式：</b>{l.neural.train_steps}步，loss={l.neural.recent_loss}</div> : null}
              <div><b style={{ color: '#d4d4d8' }}>元学习器：</b>{l?.meta_learner?.adjustments ?? 0}次调节</div>
            </div>
          </Section>

          <Section title="📐 置信度校准 (ECE)">
            {calibration ? (
              <div>
                <div style={{ fontSize: 24, fontWeight: 800, color: calibration.ece < 0.1 ? '#34d399' : calibration.ece < 0.2 ? '#fbbf24' : '#f87171' }}>
                  ECE = {calibration.ece?.toFixed(4) ?? '?'}
                </div>
                <div style={{ fontSize: 11, color: 'rgba(160,200,240,0.5)', marginTop: 4 }}>
                  过度自信={calibration.overconfidence?.toFixed(4) ?? '?'}
                </div>
                {(calibration.bins || []).map((b: any, i: number) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6, fontSize: 11 }}>
                    <span style={{ width: 60, color: 'rgba(160,200,240,0.5)' }}>{b.conf_low?.toFixed(1)}-{b.conf_high?.toFixed(1)}</span>
                    <div style={{ flex: 1, height: 10, background: 'rgba(255,255,255,0.05)', borderRadius: 5, overflow: 'hidden' }}>
                      <div style={{ width: `${(b.accuracy || 0) * 100}%`, height: '100%', background: 'linear-gradient(90deg,#60a5fa,#818cf8)', borderRadius: 5 }} />
                    </div>
                    <span style={{ width: 30, textAlign: 'right', color: 'rgba(160,200,240,0.6)' }}>{b.count ?? 0}</span>
                  </div>
                ))}
              </div>
            ) : <div style={{ color: 'rgba(160,200,240,0.3)', padding: 12, textAlign: 'center' }}>暂无校准数据</div>}
          </Section>

          <Section title="🌙 Dream Cycle 巩固">
            {dream?.phases ? (
              <div>
                <div style={{ fontSize: 12, color: 'rgba(160,200,240,0.6)', marginBottom: 8 }}>
                  {dream.last ? `上次: ${(dream.last || '').slice(0, 19)}` : ''} · 共 {dream.total ?? 0} 次
                </div>
                {Object.entries(dream.phases as Record<string,number>).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, fontSize: 11 }}>
                    <span style={{ width: 70, color: 'rgba(160,200,240,0.5)' }}>{k}</span>
                    <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 3 }}>
                      <div style={{ width: `${Math.min(100, v * 5)}%`, height: '100%', background: 'linear-gradient(90deg,#34d399,#60a5fa)', borderRadius: 3 }} />
                    </div>
                    <span style={{ width: 24, textAlign: 'right', color: v ? '#60a5fa' : 'rgba(160,200,240,0.3)' }}>{v}</span>
                  </div>
                ))}
              </div>
            ) : <div style={{ color: 'rgba(160,200,240,0.3)', padding: 12, textAlign: 'center' }}>暂无巩固数据</div>}
            <button onClick={async () => { const r = await F('/dream/run'); if (r) setDream(r) }}
              style={{ marginTop: 10, padding: '6px 16px', borderRadius: 8, background: 'linear-gradient(90deg,rgba(96,165,250,0.2),rgba(129,140,248,0.2))', border: '1px solid rgba(96,165,250,0.3)', color: '#60a5fa', cursor: 'pointer', fontSize: 12 }}>
              手动触发巩固
            </button>
          </Section>

          <Section title="⚡ 自动提取技能">
            {skills.length > 0 ? skills.slice(0, 8).map((s: any, i: number) => (
              <div key={i} style={{ fontSize: 11, padding: '4px 0', borderBottom: '1px solid rgba(80,150,255,0.05)' }}>
                <Badge text={s.action || '?'} color="#a78bfa" />
                <span style={{ marginLeft: 6, color: 'rgba(160,200,240,0.5)' }}>{s.success_count ?? 0}次成功</span>
              </div>
            )) : <div style={{ fontSize: 11, color: 'rgba(160,200,240,0.3)' }}>暂无自动提取的技能</div>}
          </Section>

          <Section title="🤖 多Agent">
            {agents.length > 0 ? agents.map((a: any) => (
              <div key={a.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(80,150,255,0.05)', fontSize: 12 }}>
                <span style={{ fontWeight: 600, color: '#e0e8f0' }}>{a.id}</span>
                <span style={{ color: 'rgba(160,200,240,0.5)' }}>{a.actions}动作 · QL{a.ql_nonzero}/{a.ql_total} · 情景{a.em_episodes} · 健康{a.health}</span>
              </div>
            )) : <div style={{ fontSize: 11, color: 'rgba(160,200,240,0.3)' }}>暂无Agent数据</div>}
          </Section>
        </div>
      </div>

      {/* Bottom: search + social */}
      <div style={{ display: 'flex', gap: 14, marginTop: 18, flexWrap: 'wrap', ...cardStyle }}>
        <div style={{ flex: 1, minWidth: 300 }}>
          <h3 style={{ margin: '0 0 10px', fontSize: 13, fontWeight: 600, color: 'rgba(130,180,240,0.9)' }}>🔍 统一搜索</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={searchQ} onChange={e => setSearchQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && doSearch()}
              placeholder="搜索实体、情景、规则…" style={{ flex: 1, padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(80,150,255,0.2)', background: 'rgba(10,20,40,0.6)', color: '#e0e8f0', fontSize: 13 }} />
            <button onClick={doSearch} style={{ padding: '8px 20px', borderRadius: 8, background: 'linear-gradient(90deg,#3b82f6,#6366f1)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>搜索</button>
          </div>
          {searchR && (
            <div style={{ marginTop: 10, fontSize: 12 }}>
              {(searchR.kg || []).map((e: any, i: number) => <span key={`k${i}`} style={{ marginRight: 8 }}><Badge text={e.type || '?'} color="#60a5fa" /> {e.name}</span>)}
              {(searchR.em || []).map((e: any, i: number) => <div key={`e${i}`} style={{ marginTop: 4, color: 'rgba(160,200,240,0.6)' }}>[{e.outcome}] {e.what}</div>)}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <button style={{ padding: '8px 18px', borderRadius: 8, background: 'rgba(96,165,250,0.15)', border: '1px solid rgba(96,165,250,0.25)', color: '#60a5fa', cursor: 'pointer', fontSize: 12 }}>📊 分享卡片</button>
          <button style={{ padding: '8px 18px', borderRadius: 8, background: 'rgba(96,165,250,0.15)', border: '1px solid rgba(96,165,250,0.25)', color: '#60a5fa', cursor: 'pointer', fontSize: 12 }}>⬇ 导出数据</button>
        </div>
      </div>
    </div>
  )
}
