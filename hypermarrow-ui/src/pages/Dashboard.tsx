import React, { useState, useEffect } from 'react'

const API = 'http://localhost:8741/api/v1'
const F = (p: string) => fetch(`${API}${p}`).then(r => r.json()).catch(() => null)

// ══════════════════════ 原型精确样式 ══════════════════════
const cardStyle: React.CSSProperties = { background: 'rgba(255,255,255,0.95)', borderRadius: 12, padding: 20, boxShadow: '0 4px 6px rgba(0,0,0,0.1)', transition: 'all .3s' }
function Card({ children, style }: any) { return <div style={{ ...cardStyle, ...style }}>{children}</div> }
function CardHeader({ title, badge, badgeColor }: { title: string; badge: string; badgeColor?: string }) {
  return <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 }}>
    <span style={{ fontSize: 18, fontWeight: 600, color: '#333' }}>{title}</span>
    <span style={{ background: badgeColor || '#667eea', color: 'white', padding: '4px 12px', borderRadius: 12, fontSize: 14 }}>{badge}</span>
  </div>
}
function ProgressBar({ label, value, sub, color }: { label: string; value: number; sub?: string; color?: string }) {
  const p = Math.min(100, Math.max(0, value))
  return <div style={{ margin: '10px 0' }}>
    {label ? <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span style={{ fontSize: 14, color: '#333' }}>{label}</span><span style={{ fontSize: 14, fontWeight: 600, color: p >= 70 ? '#51cf66' : p >= 40 ? '#ff922b' : '#868e96' }}>{p}%</span></div> : null}
    <div style={{ background: '#e0e0e0', height: 24, borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ height: '100%', width: `${p}%`, borderRadius: 12, background: color || 'linear-gradient(90deg,#667eea,#764ba2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 14, fontWeight: 600, transition: 'width 1s ease-in-out' }}>{'█'.repeat(Math.floor(p / 10))}</div>
    </div>
    {sub ? <div style={{ fontSize: 12, color: '#868e96', marginTop: 4 }}>{sub}</div> : null}
  </div>
}
function MemoryCard({ time, content }: { time: string; content: string }) {
  return <div style={{ background: '#f8f9fa', borderLeft: '4px solid #667eea', padding: 12, margin: '8px 0', borderRadius: 6, cursor: 'pointer', transition: 'all .3s' }}
    onMouseEnter={e => { const t = e.currentTarget as HTMLElement; t.style.background = '#e9ecef'; t.style.transform = 'translateX(4px)' }}
    onMouseLeave={e => { const t = e.currentTarget as HTMLElement; t.style.background = '#f8f9fa'; t.style.transform = 'translateX(0)' }}>
    <div style={{ fontSize: 12, color: '#868e96', marginBottom: 4 }}>🕐 {time}</div>
    <div style={{ fontSize: 14, color: '#333' }}>{content}</div>
  </div>
}
const btnPrimary: React.CSSProperties = { width: '100%', marginTop: 10, padding: '10px 16px', border: 'none', borderRadius: 6, background: '#667eea', color: 'white', fontSize: 14, cursor: 'pointer', transition: 'all .3s' }
function Tag({ text, color }: { text: string; color?: string }) { return <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600, background: (color || '#667eea') + '18', color: color || '#667eea', marginRight: 4 }}>{text}</span> }
function SkillCard({ label, level, color }: { label: string; level: number; color: string }) {
  return <div style={{ flex: 1, textAlign: 'center', padding: 10, background: '#f8f9fa', borderRadius: 6 }}>
    <div style={{ fontSize: 12, color: '#868e96' }}>{label}</div>
    <div style={{ fontSize: 18, fontWeight: 600, color, marginTop: 4 }}>Lv.{level}</div>
    <div style={{ background: '#e0e0e0', height: 8, borderRadius: 4, marginTop: 6, overflow: 'hidden' }}><div style={{ height: '100%', width: `${level * 20}%`, background: color, borderRadius: 4, transition: 'width 1s' }} /></div>
  </div>
}
function CSKnowledgeGraph({ entities }: any) {
  const positions = [{ left: 120, top: 100 }, { left: 240, top: 40 }, { left: 60, top: 160 }, { left: 200, top: 180 }, { left: 140, top: 40 }, { left: 40, top: 80 }]
  const icons = ['📦', '💡', '🎬', '⚙️', '🔧', '📄']
  return <div style={{ width: '100%', height: 260, background: '#f8f9fa', borderRadius: 8, position: 'relative', overflow: 'hidden' }}>
    {(entities || []).slice(0, 6).map((e: any, i: number) => <div key={i} title={`${e.name} (${e.type})`} style={{ position: 'absolute', left: positions[i]?.left || 100, top: positions[i]?.top || 100, background: 'white', border: '2px solid #667eea', borderRadius: '50%', width: 60, height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, cursor: 'pointer', transition: 'all .3s', zIndex: 2 }}
      onMouseEnter={e => { const t = e.currentTarget as HTMLElement; t.style.transform = 'scale(1.2)'; t.style.boxShadow = '0 4px 8px rgba(102,126,234,0.4)' }}
      onMouseLeave={e => { const t = e.currentTarget as HTMLElement; t.style.transform = 'scale(1)'; t.style.boxShadow = 'none' }}>{icons[i] || '●'}</div>)}
    <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
      {(entities || []).length >= 2 && <line x1={150} y1={130} x2={270} y2={70} stroke="#667eea" strokeWidth={2} />}
      {(entities || []).length >= 3 && <line x1={150} y1={130} x2={90} y2={190} stroke="#868e96" strokeWidth={1} />}
      {(entities || []).length >= 4 && <line x1={270} y1={70} x2={230} y2={210} stroke="#868e96" strokeWidth={1} />}
    </svg>
  </div>
}

// ══════════════════════ 仪表盘 ══════════════════════
export default function Dashboard() {
  const [mem, setMem] = useState<any>(null); const [lrn, setLrn] = useState<any>(null)
  const [graph, setGraph] = useState<any>(null); const [rules, setRules] = useState<any[]>([])
  const [episodes, setEpisodes] = useState<any[]>([]); const [agents, setAgents] = useState<any[]>([])
  const [heatmap, setHeatmap] = useState<any>(null); const [calibration, setCalibration] = useState<any>(null)
  const [dream, setDream] = useState<any>(null); const [skills, setSkills] = useState<any[]>([])
  const [achievements, setAchievements] = useState<any[]>([]); const [searchQ, setSearchQ] = useState(''); const [searchR, setSearchR] = useState<any>(null)
  const [loading, setLoading] = useState(true); const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([F('/memory/overview'), F('/learning/overview'), F('/kg/graph'), F('/pm/rules'), F('/em/timeline?limit=60'), F('/agents'), F('/ql/heatmap'), F('/meta/calibration'), F('/dream/status'), F('/skills/list'), F('/achievements')])
      .then(([mR, lR, gR, rR, eR, aR, hR, cR, dR, sR, achR]) => {
        if (!mR && !lR) { setError('无法连接后端 API (localhost:8741)'); setLoading(false); return }
        setMem(mR || {}); setLrn(lR || {}); setGraph(gR); setRules(rR || []); setEpisodes(eR || []); setAgents(aR || []); setHeatmap(hR); setCalibration(cR); setDream(dR); setSkills(Object.values(sR || {})); setAchievements(achR?.achievements || []); setLoading(false)
      }).catch((e: any) => { setError(`加载失败: ${e.message}`); setLoading(false) })
    let ws: WebSocket; try { ws = new WebSocket('ws://localhost:8741/ws'); ws.onmessage = e => { const d = JSON.parse(e.data); setLrn((p: any) => p?.q_learning ? { ...p, q_learning: { ...p.q_learning, nonzero: d.ql_nonzero, buffer: d.ql_buffer }, metacognition: { ...p.metacognition, health: d.health, accuracy: d.accuracy, score: d.score } } : p) } } catch { }
    return () => { try { ws?.close() } catch { } }
  }, [])

  if (loading) return <div style={{ padding: 80, textAlign: 'center', color: 'white', fontSize: 18 }}>🧠 正在唤醒记忆系统…</div>
  if (error) return <div style={{ ...cardStyle, padding: 60, textAlign: 'center' }}><div style={{ fontSize: 22, fontWeight: 700, color: '#e03131' }}>连接失败</div><div style={{ marginTop: 8, color: '#868e96' }}>{error}</div></div>

  const m: any = mem || {}; const l: any = lrn || {}
  const qlpct = l?.q_learning?.nonzero_pct || 0; const qlnz = l?.q_learning?.nonzero || 0
  const entities = graph?.nodes || []

  return <div>
    {/* 成就 */}
    {achievements.length > 0 && <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
      {achievements.map((a: any) => <div key={a.id} style={{ background: 'rgba(255,255,255,0.9)', padding: '6px 14px', borderRadius: 20, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>{a.icon} {a.title} {a.level >= 2 && <span style={{ fontSize: 10, background: '#667eea', color: '#fff', borderRadius: 8, padding: '1px 6px' }}>Lv{a.level}</span>}</div>)}
    </div>}

    {/* 全模块网格 */}
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20, marginBottom: 20 }}>

      {/* 1. 情景记忆 */}
      <Card><CardHeader title="📒 情景记忆" badge={`${m?.p3_episodic_memory?.total ?? 0} 条`} />
        {episodes.slice(0, 3).map((ep: any, i: number) => <MemoryCard key={i} time={(ep.when || '').slice(0, 16) || '未知时间'} content={ep.what || '无内容'} />)}
        {episodes.length === 0 && <div style={{ color: '#868e96', padding: 20, textAlign: 'center' }}>暂无记忆</div>}
      </Card>

      {/* 2. 程序记忆 */}
      <Card><CardHeader title="📝 程序记忆" badge={`${rules.length} 条`} />
        {rules.slice(0, 2).map((r: any, i: number) => <div key={i} style={{ margin: '10px 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}><span style={{ fontSize: 14 }}>{r.name}</span><span style={{ fontSize: 12, color: (r.success_rate || 0) >= 0.7 ? '#51cf66' : '#ff922b', fontWeight: 600 }}>置信度 {(r.success_rate * 100).toFixed(0)}%</span></div>
          <ProgressBar label="" value={(r.success_rate || 0) * 100} />
          <div style={{ fontSize: 12, color: '#868e96', marginTop: 4 }}>应用 {r.attempts || 0} 次 | 成功率 {(r.success_rate * 100).toFixed(0)}%</div>
        </div>)}
      </Card>

      {/* 3. 知识图谱 */}
      <Card><CardHeader title="🕸️ 知识图谱" badge={`${m?.knowledge_graph?.entities ?? 0} 实体`} /><CSKnowledgeGraph entities={entities} /></Card>

      {/* 4. 学习进度 */}
      <Card><CardHeader title="🎯 学习进度" badge={`${qlpct.toFixed(0)}%`} />
        <ProgressBar label="总体进度" value={qlpct} />
        <div style={{ fontSize: 14, color: '#495057', margin: '10px 0', lineHeight: 1.8 }}>✅ 状态空间: {l?.q_learning?.total || 700} 个 | 已学习: <strong>{qlnz}</strong> 个<br />✅ 动作空间: 7 个 | 模式: <strong>{l?.q_learning?.mode || 'tabular'}</strong></div>
        <div style={{ marginTop: 15 }}><div style={{ fontSize: 14, marginBottom: 8 }}>🎮 技能树 (Top 3)</div><div style={{ display: 'flex', gap: 10 }}>
          {(heatmap?.rows || []).slice(0, 3).map((row: any, i: number) => {
            const maxQ = Math.max(...(row.values || []).map(Math.abs)); const level = Math.min(5, Math.ceil(maxQ * 5)); const colors = ['#667eea', '#764ba2', '#51cf66']
            return <SkillCard key={i} label={`状态 #${row.state}`} level={level} color={colors[i]} />
          })}
          {(!heatmap?.rows || heatmap.rows.length === 0) && <div style={{ color: '#868e96', fontSize: 12, padding: 10 }}>等待训练数据…</div>}
        </div></div>
      </Card>

      {/* 5. 记忆巩固 */}
      <Card><CardHeader title="🌙 记忆巩固" badge={dream?.phases ? '✅ 正常' : '⏳ 等待'} badgeColor={dream?.phases ? '#51cf66' : '#868e96'} />
        <div style={{ fontSize: 14, margin: '10px 0', lineHeight: 1.8 }}>🕐 上次运行: <strong>{dream?.last?.slice(0, 19) || '无'}</strong><br />⏱️ 共运行: <strong>{dream?.total || 0} 次</strong></div>
        {dream?.phases && <div style={{ background: '#f8f9fa', padding: 12, borderRadius: 6, margin: '10px 0' }}><div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>📋 运行报告</div><div style={{ fontSize: 13, color: '#495057', lineHeight: 1.6 }}>{Object.entries(dream.phases as Record<string, number>).filter(([, v]) => v !== undefined && v > 0).map(([k, v]) => <div key={k}>✅ {k}: {v}</div>)}</div></div>}
        <button style={btnPrimary} onClick={async () => { const r = await F('/dream/run'); if (r) setDream(r) }}>🌙 立即运行</button>
      </Card>

      {/* 6. 记忆分布 */}
      <Card><CardHeader title="📊 记忆分布" badge="" />
        <ProgressBar label="📒 情景记忆" value={(m?.p3_episodic_memory?.total || 1) / Math.max(1, (m?.p3_episodic_memory?.total || 1) + rules.length + (m?.knowledge_graph?.entities || 1)) * 100} color="linear-gradient(90deg,#667eea,#4c6ef5)" />
        <ProgressBar label="📝 程序记忆" value={rules.length / Math.max(1, (m?.p3_episodic_memory?.total || 1) + rules.length + (m?.knowledge_graph?.entities || 1)) * 100} color="linear-gradient(90deg,#51cf66,#37b24d)" />
        <ProgressBar label="🕸️ 知识图谱" value={(m?.knowledge_graph?.entities || 1) / Math.max(1, (m?.p3_episodic_memory?.total || 1) + rules.length + (m?.knowledge_graph?.entities || 1)) * 100} color="linear-gradient(90deg,#ff922b,#f76707)" />
        <ProgressBar label="🧠 工作记忆" value={10} color="linear-gradient(90deg,#cc5de8,#9c36b5)" />
        <ProgressBar label="🎯 Q学习" value={qlpct} color="linear-gradient(90deg,#fbbf24,#f59e0b)" />
      </Card>

      {/* 7. 便签板 P1 */}
      <Card><CardHeader title="📝 便签板" badge={m?.p1_working_memory?.task ? '活跃' : '空闲'} badgeColor={m?.p1_working_memory?.task ? '#51cf66' : '#868e96'} />
        <div style={{ fontSize: 14, color: '#495057', lineHeight: 2 }}>
          <div>📌 任务: <strong>{m?.p1_working_memory?.task || '空闲'}</strong></div>
          <div>🎯 目标: {m?.p1_working_memory?.goal || '无'}</div>
          <div>📚 任务栈深度: {m?.p1_working_memory?.stack_depth ?? 0}</div>
          <div>🔑 上下文: {(m?.p1_working_memory?.context_keys || []).slice(0, 5).join(', ') || '无'}</div>
        </div>
      </Card>

      {/* 8. 语义搜索 P2 */}
      <Card><CardHeader title="🔍 语义搜索" badge={`${m?.p2_vector_memory?.total_vectors ?? 0} 向量`} />
        <div style={{ fontSize: 14, color: '#495057', lineHeight: 2 }}>
          <div>📦 集合: <strong>{m?.p2_vector_memory?.collection || 'ChromaDB'}</strong></div>
          <div>📐 嵌入维度: {m?.p2_vector_memory?.embedding_dim || 0}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <input value={searchQ} onChange={e => setSearchQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && F(`/search?q=${encodeURIComponent(searchQ)}&limit=5`).then(setSearchR)} placeholder="搜索记忆…" style={{ flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid #dee2e6', fontSize: 13 }} />
          <button onClick={async () => setSearchR(await F(`/search?q=${encodeURIComponent(searchQ)}&limit=5`))} style={{ padding: '8px 14px', borderRadius: 6, background: '#667eea', color: 'white', border: 'none', cursor: 'pointer', fontSize: 13 }}>搜索</button>
        </div>
        {searchR && <div style={{ marginTop: 10, fontSize: 12 }}>
          {(searchR.kg || []).map((e: any, i: number) => <Tag key={`k${i}`} text={`${e.name} (${e.type})`} color="#667eea" />)}
          {(searchR.em || []).map((e: any, i: number) => <div key={`e${i}`} style={{ marginTop: 4, color: '#868e96' }}>[{e.outcome}] {e.what?.slice(0, 60)}</div>)}
        </div>}
      </Card>

      {/* 9. 自我诊断 Meta */}
      <Card><CardHeader title="🩺 自我诊断" badge={l?.metacognition?.health || '?'} badgeColor={l?.metacognition?.health === 'good' ? '#51cf66' : l?.metacognition?.health === 'warning' ? '#ff922b' : '#e03131'} />
        <div style={{ fontSize: 14, color: '#495057', lineHeight: 2 }}>
          <div>📊 健康分: <strong>{l?.metacognition?.score?.toFixed(0) || '?'}%</strong></div>
          <div>📐 ECE: <strong style={{ color: (calibration?.ece || 0) < 0.1 ? '#51cf66' : (calibration?.ece || 0) < 0.2 ? '#ff922b' : '#e03131' }}>{calibration?.ece?.toFixed(4) || '?'}</strong></div>
          <div>🎯 决策总数: {l?.metacognition?.decisions || 0}</div>
          <div>⚠️ 连续失败: {l?.metacognition?.failures || 0}</div>
          <div>🔍 近期异常: {l?.metacognition?.anomalies || 0}</div>
          <div>📈 准确率: <strong>{(l?.metacognition?.accuracy * 100).toFixed(0)}%</strong></div>
        </div>
      </Card>

      {/* 10. 自动技能 */}
      <Card><CardHeader title="⚡ 自动技能" badge={`${skills.length} 个`} badgeColor="#f472b6" />
        {skills.length > 0 ? skills.slice(0, 5).map((s: any, i: number) => <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid #f1f3f5' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ fontSize: 13, fontWeight: 500 }}>{s.action}</span><span style={{ fontSize: 11, color: '#868e96' }}>{s.success_count} 次成功</span></div>
          <div style={{ fontSize: 11, color: '#868e96', marginTop: 2 }}>触发词: {(s.context_patterns || []).slice(0, 4).join(', ')}</div>
        </div>) : <div style={{ color: '#868e96', padding: 16, textAlign: 'center' }}>暂无自动提取的技能</div>}
      </Card>

      {/* 11. Agent 中心 */}
      <Card><CardHeader title="🤖 Agent 中心" badge={`${agents.length} 个`} />
        {agents.map((a: any) => <div key={a.id} style={{ padding: '8px 0', borderBottom: '1px solid #f1f3f5' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{a.id}</span>
            <Tag text={`${a.actions} 动作`} color="#667eea" />
          </div>
          <div style={{ fontSize: 11, color: '#868e96', marginTop: 4 }}>QL: {a.ql_nonzero}/{a.ql_total} · 情景: {a.em_episodes} · 健康: {a.health}</div>
        </div>)}
      </Card>

      {/* 12. 前瞻记忆 */}
      <Card><CardHeader title="⏰ 前瞻记忆" badge={`${m?.prospective?.active ?? 0} 活跃`} badgeColor={m?.prospective?.active > 0 ? '#51cf66' : '#868e96'} />
        <div style={{ fontSize: 14, color: '#495057', lineHeight: 2 }}>
          <div>✅ 已完成: {m?.prospective?.completed || 0}</div>
          <div>⏰ 已过期: {m?.prospective?.expired || 0}</div>
          <div>❌ 已取消: {m?.prospective?.cancelled || 0}</div>
        </div>
      </Card>

      {/* 13. 知识迁移 */}
      <Card><CardHeader title="🔄 知识迁移" badge={`${l?.transfer?.total_transfers || 0} 次`} />
        <div style={{ fontSize: 14, color: '#495057', lineHeight: 2 }}>
          <div>📦 档案库: <strong>{l?.transfer?.total_profiles || 0}</strong> 个项目档案</div>
          <div>🔁 总迁移次数: <strong>{l?.transfer?.total_transfers || 0}</strong></div>
          {l?.transfer?.recent_transfers?.length > 0 && <div style={{ marginTop: 6 }}>
            <div style={{ fontSize: 12, color: '#868e96', marginBottom: 4 }}>最近迁移:</div>
            {l.transfer.recent_transfers.slice(0, 3).map((t: any, i: number) => <div key={i} style={{ fontSize: 11, color: '#495057' }}>{t.source_project} → {t.target_project} (相似度 {t.similarity?.toFixed(2)})</div>)}
          </div>}
        </div>
      </Card>

      {/* 14. 成就系统 */}
      {achievements.length > 0 && <Card>
        <CardHeader title="🏆 成就" badge={`${achievements.length} 个`} badgeColor="#fbbf24" />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {achievements.map((a: any) => <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0' }}>
            <span style={{ fontSize: 20 }}>{a.icon}</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#333' }}>{a.title} {a.level >= 2 && <span style={{ fontSize: 10, background: '#fbbf24', color: '#000', borderRadius: 8, padding: '1px 6px' }}>Lv{a.level}</span>}</div>
              <div style={{ fontSize: 11, color: '#868e96' }}>{a.desc}</div>
            </div>
          </div>)}
        </div>
      </Card>}

      {/* 15. 感知通道 */}
      <Card><CardHeader title="👁️ 感知通道" badge={m?.perception?.screen?.captures > 0 ? '活跃' : '待机'} badgeColor={m?.perception?.screen?.captures > 0 ? '#51cf66' : '#868e96'} />
        <div style={{ fontSize: 14, color: '#495057', lineHeight: 2 }}>
          <div>🖥️ 屏幕: {m?.perception?.screen?.captures || 0} 次捕获 (OCR: {m?.perception?.screen?.ocr_available ? '✅' : '❌'})</div>
          <div>💬 对话: {m?.perception?.conversation?.total_turns || 0} 轮, 话题: {m?.perception?.conversation?.current_topic || '无'}</div>
        </div>
      </Card>

      {/* 16. 世界模型 + 神经模式 */}
      <Card><CardHeader title="🧬 高级认知" badge={l?.world_model?.train_steps > 0 ? '活跃' : '待机'} badgeColor={l?.world_model?.train_steps > 0 ? '#a78bfa' : '#868e96'} />
        <div style={{ fontSize: 14, color: '#495057', lineHeight: 2 }}>
          <div>🌍 世界模型: <strong>{l?.world_model?.train_steps || 0}</strong> 步训练</div>
          {l?.world_model?.recent_state_loss != null && <div>📉 状态损失: {l.world_model.recent_state_loss?.toFixed(4)}</div>}
          {l?.world_model?.recent_reward_loss != null && <div>📉 奖励损失: {l.world_model.recent_reward_loss?.toFixed(4)}</div>}
          <div style={{ marginTop: 6 }}>🧠 神经模式: {l?.neural?.train_steps > 0 ? <strong>{l.neural.train_steps}</strong> + ' 步' : '未启用'}</div>
          {l?.neural?.recent_loss != null && <div>📉 损失: {l.neural.recent_loss?.toFixed(6)}</div>}
          <div>⚙️ 元学习器: {l?.meta_learner?.adjustments || 0} 次调节</div>
        </div>
      </Card>

    </div>
  </div>
}
