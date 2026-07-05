import React, { useState, useEffect } from 'react'

const API = 'http://localhost:8741/api/v1'
const F = (p: string) => fetch(`${API}${p}`).then(r => r.json()).catch(() => null)

type CardProps = { children: React.ReactNode; style?: React.CSSProperties }
const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.95)', borderRadius: 12, padding: 20,
  boxShadow: '0 4px 6px rgba(0,0,0,0.1)', transition: 'all .3s',
}
function Card({ children, style }: CardProps) {
  return <div style={{...cardStyle, ...style}}>{children}</div>
}
function CardHeader({ title, badge }: { title: string; badge: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 }}>
      <span style={{ fontSize: 18, fontWeight: 600, color: '#333' }}>{title}</span>
      <span style={{ background: '#667eea', color: 'white', padding: '4px 12px', borderRadius: 12, fontSize: 14 }}>{badge}</span>
    </div>
  )
}

function ProgressBar({ label, value, sub, color }: { label: string; value: number; sub?: string; color?: string }) {
  const pct = Math.min(100, Math.max(0, value))
  return (
    <div style={{ margin: '10px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 14, color: '#333' }}>{label}</span>
        <span style={{ fontSize: 12, color: value >= 70 ? '#51cf66' : value >= 40 ? '#ff922b' : '#868e96', fontWeight: 600 }}>
          {value >= 70 ? '置信度' : ''} {pct}%
        </span>
      </div>
      <div style={{ background: '#e0e0e0', height: 24, borderRadius: 12, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`, borderRadius: 12,
          background: color || 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'white', fontSize: 14, fontWeight: 600, transition: 'width 1s ease-in-out',
        }}>{'█'.repeat(Math.floor(pct / 10))}</div>
      </div>
      {sub && <div style={{ fontSize: 12, color: '#868e96', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

function MemoryCard({ time, content }: { time: string; content: string }) {
  return (
    <div style={{
      background: '#f8f9fa', borderLeft: '4px solid #667eea', padding: 12, margin: '8px 0',
      borderRadius: 6, cursor: 'pointer', transition: 'all .3s',
    }} onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = '#e9ecef'; (e.currentTarget as HTMLElement).style.transform = 'translateX(4px)' }}
       onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = '#f8f9fa'; (e.currentTarget as HTMLElement).style.transform = 'translateX(0)' }}>
      <div style={{ fontSize: 12, color: '#868e96', marginBottom: 4 }}>🕐 {time}</div>
      <div style={{ fontSize: 14, color: '#333' }}>{content}</div>
    </div>
  )
}

const btnPrimary: React.CSSProperties = {
  width: '100%', marginTop: 10, padding: '10px 16px', border: 'none', borderRadius: 6,
  background: '#667eea', color: 'white', fontSize: 14, cursor: 'pointer', transition: 'all .3s',
}

// ── CSS 知识图谱节点（非 D3，纯 CSS 定位）─────────────────────────────────
function CSKnowledgeGraph({ entities, onExpand }: { entities: any[]; onExpand: () => void }) {
  const positions = [
    { left: 120, top: 100 }, { left: 240, top: 40 }, { left: 60, top: 160 },
    { left: 200, top: 180 }, { left: 140, top: 40 }, { left: 40, top: 80 },
  ]
  const icons = ['📦', '💡', '🎬', '⚙️', '🔧', '📄']
  return (
    <div style={{ width: '100%', height: 260, background: '#f8f9fa', borderRadius: 8, position: 'relative', overflow: 'hidden' }}>
      {entities.slice(0, 6).map((e: any, i: number) => (
        <div key={i} title={`${e.name} (${e.type})`} style={{
          position: 'absolute', left: positions[i]?.left || 100, top: positions[i]?.top || 100,
          background: 'white', border: '2px solid #667eea', borderRadius: '50%',
          width: 60, height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, cursor: 'pointer', transition: 'all .3s', zIndex: 2,
        }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(1.2)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 8px rgba(102,126,234,0.4)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(1)'; (e.currentTarget as HTMLElement).style.boxShadow = 'none' }}>
          {icons[i] || '●'}
        </div>
      ))}
      <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
        {entities.length >= 2 && <line x1={150} y1={130} x2={270} y2={70} stroke="#667eea" strokeWidth={2} />}
        {entities.length >= 3 && <line x1={150} y1={130} x2={90} y2={190} stroke="#868e96" strokeWidth={1} />}
        {entities.length >= 4 && <line x1={270} y1={70} x2={230} y2={210} stroke="#868e96" strokeWidth={1} />}
      </svg>
      <button style={{ position: 'absolute', bottom: 8, right: 8, zIndex: 3, ...btnPrimary, width: 'auto', marginTop: 0, fontSize: 12, padding: '4px 12px' }} onClick={onExpand}>展开图谱</button>
    </div>
  )
}

function SkillCard({ label, level, color }: { label: string; level: number; color: string }) {
  return (
    <div style={{ flex: 1, textAlign: 'center', padding: 10, background: '#f8f9fa', borderRadius: 6 }}>
      <div style={{ fontSize: 12, color: '#868e96' }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 600, color, marginTop: 4 }}>Lv.{level}</div>
      <div style={{ background: '#e0e0e0', height: 8, borderRadius: 4, marginTop: 6, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${level * 20}%`, background: color, borderRadius: 4, transition: 'width 1s' }} />
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
export default function Dashboard() {
  const [mem, setMem] = useState<any>(null)
  const [lrn, setLrn] = useState<any>(null)
  const [graph, setGraph] = useState<any>(null)
  const [rules, setRules] = useState<any[]>([])
  const [episodes, setEpisodes] = useState<any[]>([])
  const [heatmap, setHeatmap] = useState<any>(null)
  const [dream, setDream] = useState<any>(null)
  const [achievements, setAchievements] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      F('/memory/overview'), F('/learning/overview'), F('/kg/graph'),
      F('/pm/rules'), F('/em/timeline?limit=60'), F('/ql/heatmap'),
      F('/dream/status'), F('/achievements'),
    ]).then(([mR, lR, gR, rR, eR, hR, dR, aR]) => {
      if (!mR && !lR) { setError('无法连接后端 API (localhost:8741)'); setLoading(false); return }
      setMem(mR || {}); setLrn(lR || {}); setGraph(gR); setRules(rR || []);
      setEpisodes(eR || []); setHeatmap(hR); setDream(dR);
      setAchievements(aR?.achievements || []); setLoading(false)
    }).catch((e: any) => { setError(`加载失败: ${e.message}`); setLoading(false) })

    let ws: WebSocket
    try {
      ws = new WebSocket('ws://localhost:8741/ws')
      ws.onmessage = e => {
        const d = JSON.parse(e.data)
        setLrn((p: any) => p?.q_learning ? { ...p, q_learning: { ...p.q_learning, nonzero: d.ql_nonzero, buffer: d.ql_buffer }, metacognition: { ...p.metacognition, health: d.health, accuracy: d.accuracy, score: d.score } } : p)
      }
    } catch { }
    return () => { try { ws?.close() } catch { } }
  }, [])

  if (loading) return <div style={{ padding: 80, textAlign: 'center', color: 'white', fontSize: 18 }}>🧠 正在唤醒记忆系统…</div>
  if (error) return <div style={{ padding: 80, textAlign: 'center', background: 'rgba(255,255,255,0.95)', borderRadius: 12 }}>
    <div style={{ fontSize: 22, fontWeight: 700, color: '#e03131' }}>连接失败</div>
    <div style={{ marginTop: 8, color: '#868e96', fontSize: 13 }}>{error}</div>
    <div style={{ marginTop: 16, fontSize: 12, color: '#868e96' }}>请确认：<code style={{ background: '#f8f9fa', padding: '4px 8px', borderRadius: 4 }}>python start_server.py</code></div>
  </div>

  const m = mem || {}; const l = lrn || {}
  const qlpct = l?.q_learning?.nonzero_pct || 0
  const qlnz = l?.q_learning?.nonzero || 0
  const qlt = l?.q_learning?.total || 700
  const entities = graph?.nodes || []

  return (
    <div>
      {/* 成就徽章 */}
      {achievements.length > 0 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
          {achievements.map((a: any) => (
            <div key={a.id} style={{ background: 'rgba(255,255,255,0.9)', padding: '6px 14px', borderRadius: 20, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
              {a.icon} {a.title} {a.level >= 2 && <span style={{ fontSize: 10, background: '#667eea', color: '#fff', borderRadius: 8, padding: '1px 6px' }}>Lv{a.level}</span>}
            </div>
          ))}
        </div>
      )}

      {/* 6 模块网格 — 完全按照原型 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20, marginBottom: 20 }}>
        {/* 1. 📒 情景记忆 */}
        <Card>
          <CardHeader title="📒 情景记忆" badge={`${m?.p3_episodic_memory?.total ?? 0} 条`} />
          {episodes.slice(0, 3).map((ep: any, i: number) => (
            <MemoryCard key={i} time={(ep.when || '').slice(0, 16) || '未知时间'} content={ep.what || '无内容'} />
          ))}
          {episodes.length === 0 && <div style={{ color: '#868e96', padding: 20, textAlign: 'center' }}>暂无记忆</div>}
          <button style={btnPrimary}>查看全部</button>
        </Card>

        {/* 2. 📝 程序记忆 */}
        <Card>
          <CardHeader title="📝 程序记忆" badge={`${rules.length} 条`} />
          {rules.slice(0, 2).map((r: any, i: number) => (
            <div key={i} style={{ margin: '10px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 14 }}>{r.name}</span>
                <span style={{ fontSize: 12, color: (r.success_rate || 0) >= 0.7 ? '#51cf66' : '#ff922b', fontWeight: 600 }}>
                  置信度 {(r.success_rate * 100).toFixed(0)}%
                </span>
              </div>
              <ProgressBar label="" value={(r.success_rate || 0) * 100} color="linear-gradient(90deg, #667eea 0%, #764ba2 100%)" />
              <div style={{ fontSize: 12, color: '#868e96', marginTop: 4 }}>
                应用 {r.attempts || 0} 次 | 成功率 {(r.success_rate * 100).toFixed(0)}%
              </div>
            </div>
          ))}
          {rules.length === 0 && <div style={{ color: '#868e96', padding: 20, textAlign: 'center' }}>暂无规则</div>}
          <button style={btnPrimary}>查看全部</button>
        </Card>

        {/* 3. 🕸️ 知识图谱 */}
        <Card>
          <CardHeader title="🕸️ 知识图谱" badge={`${m?.knowledge_graph?.entities ?? 0} 实体`} />
          <CSKnowledgeGraph entities={entities} onExpand={() => { }} />
        </Card>

        {/* 4. 🎯 学习进度 */}
        <Card>
          <CardHeader title="🎯 学习进度" badge={`${qlpct.toFixed(0)}%`} />
          <ProgressBar label="总体进度" value={qlpct} color="linear-gradient(90deg, #667eea 0%, #764ba2 100%)" />
          <div style={{ fontSize: 14, color: '#495057', margin: '10px 0', lineHeight: 1.8 }}>
            ✅ 状态空间: {qlt} 个 | 已学习: <strong>{qlnz}</strong> 个<br />
            ✅ 动作空间: 7 个 | 模式: <strong>{l?.q_learning?.mode || 'tabular'}</strong>
          </div>
          <div style={{ marginTop: 15 }}>
            <div style={{ fontSize: 14, marginBottom: 8 }}>🎮 技能树 (Top 3)</div>
            <div style={{ display: 'flex', gap: 10 }}>
              {(heatmap?.rows || []).slice(0, 3).map((row: any, i: number) => {
                const maxQ = Math.max(...(row.values || []).map(Math.abs))
                const level = Math.min(5, Math.ceil(maxQ * 5))
                const colors = ['#667eea', '#764ba2', '#51cf66']
                return <SkillCard key={i} label={`状态 #${row.state}`} level={level} color={colors[i]} />
              })}
              {(!heatmap?.rows || heatmap.rows.length === 0) && <div style={{ color: '#868e96', fontSize: 12, padding: 10 }}>等待训练数据…</div>}
            </div>
          </div>
        </Card>

        {/* 5. 🌙 记忆巩固 */}
        <Card>
          <CardHeader title="🌙 记忆巩固" badge={dream?.phases ? '✅ 正常' : '⏳ 等待'} />
          <div style={{ fontSize: 14, margin: '10px 0', lineHeight: 1.8 }}>
            🕐 上次运行: <strong>{dream?.last?.slice(0, 19) || '无'}</strong><br />
            ⏱️ 共运行: <strong>{dream?.total || 0} 次</strong>
          </div>
          {dream?.phases && (
            <div style={{ background: '#f8f9fa', padding: 12, borderRadius: 6, margin: '10px 0' }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>📋 最近一次运行报告</div>
              <div style={{ fontSize: 13, color: '#495057', lineHeight: 1.6 }}>
                {Object.entries(dream.phases as Record<string, number>).map(([k, v]) => (
                  v !== undefined && v > 0 ? <div key={k}>✅ {k}: {v}</div> : null
                ))}
              </div>
            </div>
          )}
          <button style={btnPrimary} onClick={async () => { const r = await F('/dream/run'); if (r) setDream(r) }}>🌙 立即运行</button>
        </Card>

        {/* 6. 📊 记忆分布 */}
        <Card>
          <CardHeader title="📊 记忆分布" badge="" />
          <ProgressBar label="📒 情景记忆" value={45} color="linear-gradient(90deg, #667eea 0%, #4c6ef5 100%)" />
          <ProgressBar label="📝 程序记忆" value={15} color="linear-gradient(90deg, #51cf66 0%, #37b24d 100%)" />
          <ProgressBar label="🕸️ 知识图谱" value={25} color="linear-gradient(90deg, #ff922b 0%, #f76707 100%)" />
          <ProgressBar label="🧠 工作记忆" value={10} color="linear-gradient(90deg, #cc5de8 0%, #9c36b5 100%)" />
          <ProgressBar label="其他" value={5} color="linear-gradient(90deg, #868e96 0%, #495057 100%)" />
        </Card>
      </div>
    </div>
  )
}
