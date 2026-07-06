import React, { useState, useEffect } from 'react'

const API = 'http://localhost:8741/api/v1'
const F = (p: string) => fetch(`${API}${p}`).then(r => r.json()).catch(() => null)

// ══════════════════════ 认知年龄计算 ══════════════════════
function calcCognitiveAge(m: any, l: any): { age: number; stage: string; desc: string; traits: string[] } {
  const kg = (m?.knowledge_graph?.entities || 0); const rels = (m?.knowledge_graph?.relationships || 0)
  const qlpct = l?.q_learning?.nonzero_pct || 0; const em = m?.p3_episodic_memory?.total || 0
  const pm = (m?.procedural_memory?.total_rules || rules?.length || 0)
  const ece = l?.metacognition?.ece ?? 0.5; const acc = l?.metacognition?.accuracy || 0
  const neural = l?.neural?.train_steps > 0; const wm = l?.world_model?.train_steps > 0

  let age = 3
  if (kg >= 3) age += 1; if (kg >= 10) age += 1; if (kg >= 30) age += 2
  if (rels >= 5) age += 1; if (rels >= 20) age += 1
  if (qlpct >= 20) age += 1; if (qlpct >= 40) age += 1; if (qlpct >= 60) age += 2
  if (em >= 10) age += 1; if (em >= 50) age += 1
  if (pm >= 5) age += 1
  if (ece < 0.3) age += 1; if (acc > 0.5) age += 1
  if (neural) age += 1; if (wm) age += 1

  const traits: string[] = []
  if (kg >= 10) traits.push('能识别常见概念')
  if (qlpct >= 30) traits.push('开始从经验中学习')
  if (pm >= 5) traits.push('形成了初步规则')
  if (ece < 0.3) traits.push('自我认知较准')
  if (neural || wm) traits.push('具备抽象推理雏形')

  if (age <= 5) return { age, stage: '幼儿期', desc: '正在建立基础认知，像人类3-5岁的幼儿一样探索世界', traits }
  if (age <= 8) return { age, stage: '学龄期', desc: '具备了结构化的记忆和简单的学习能力，相当于6-8岁儿童', traits }
  if (age <= 12) return { age, stage: '少年期', desc: '规则系统开始形成，能自主学习和巩固记忆，达到9-12岁水平', traits }
  return { age, stage: '青春期', desc: '元认知觉醒，世界模型建立，具备抽象推理能力，相当于13-15岁青少年', traits }
}

// ══════════════════════ 样式 ══════════════════════
const c: any = {
  card: { background: 'rgba(255,255,255,0.95)', borderRadius: 16, padding: 22, boxShadow: '0 2px 12px rgba(0,0,0,0.06)', transition: 'all .3s', position: 'relative', overflow: 'hidden' } as React.CSSProperties,
  cardHover: { transform: 'translateY(-3px)', boxShadow: '0 8px 24px rgba(102,126,234,0.15)' } as React.CSSProperties,
}
function Card({ children, style }: any) {
  const [h, setH] = useState(false)
  return <div style={{ ...c.card, ...(h ? c.cardHover : {}), ...style }} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}>{children}</div>
}
function CardHead({ icon, title, badge, badgeColor }: any) {
  return <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, borderBottom: '2px solid #f1f3f5', paddingBottom: 12 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <span style={{ fontSize: 22 }}>{icon}</span>
      <span style={{ fontSize: 16, fontWeight: 700, color: '#2c3e50' }}>{title}</span>
    </div>
    <span style={{ background: badgeColor || '#667eea', color: 'white', padding: '5px 14px', borderRadius: 14, fontSize: 13, fontWeight: 600, letterSpacing: 0.5 }}>{badge}</span>
  </div>
}
function Progress({ label, value, color, sub }: any) {
  const p = Math.min(100, Math.max(0, value))
  return <div style={{ margin: '10px 0' }}>
    {label ? <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span style={{ fontSize: 13, color: '#495057' }}>{label}</span><span style={{ fontSize: 13, fontWeight: 700, color: p >= 70 ? '#40c057' : p >= 40 ? '#fd7e14' : '#868e96' }}>{p}%</span></div> : null}
    <div style={{ background: '#f1f3f5', height: 22, borderRadius: 11, overflow: 'hidden' }}>
      <div style={{ height: '100%', width: `${p}%`, borderRadius: 11, background: color || 'linear-gradient(90deg,#667eea,#764ba2)', transition: 'width 1.2s cubic-bezier(0.4, 0, 0.2, 1)' }} />
    </div>
    {sub ? <div style={{ fontSize: 11, color: '#adb5bd', marginTop: 4 }}>{sub}</div> : null}
  </div>
}
function MemCard({ time, content }: any) {
  return <div style={{ background: '#f8f9fa', borderLeft: '4px solid #667eea', padding: 12, margin: '8px 0', borderRadius: 8, cursor: 'pointer', transition: 'all .25s' }}
    onMouseEnter={e => { const t = e.currentTarget as HTMLElement; t.style.background = '#e9ecef'; t.style.transform = 'translateX(6px)' }}
    onMouseLeave={e => { const t = e.currentTarget as HTMLElement; t.style.background = '#f8f9fa'; t.style.transform = 'translateX(0)' }}>
    <div style={{ fontSize: 11, color: '#adb5bd', marginBottom: 4 }}>{time}</div>
    <div style={{ fontSize: 13, color: '#343a40', lineHeight: 1.5 }}>{content}</div>
  </div>
}
const btnPrimary: React.CSSProperties = { width: '100%', marginTop: 12, padding: '11px', border: 'none', borderRadius: 10, background: 'linear-gradient(135deg,#667eea,#764ba2)', color: 'white', fontSize: 14, fontWeight: 600, cursor: 'pointer', transition: 'all .3s', letterSpacing: 0.5 }
function Tag({ text, color }: any) { return <span style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 600, background: (color || '#667eea') + '15', color: color || '#667eea', marginRight: 5, marginBottom: 4 }}>{text}</span> }
function SkillCard({ label, level, color }: any) {
  return <div style={{ flex: 1, textAlign: 'center', padding: 12, background: '#f8f9fa', borderRadius: 10 }}>
    <div style={{ fontSize: 11, color: '#868e96', fontWeight: 600 }}>{label}</div>
    <div style={{ fontSize: 22, fontWeight: 800, color, margin: '4px 0' }}>Lv.{level}</div>
    <div style={{ background: '#e9ecef', height: 6, borderRadius: 3, overflow: 'hidden' }}><div style={{ height: '100%', width: `${level * 20}%`, background: color, borderRadius: 3, transition: 'width 1s' }} /></div>
  </div>
}
function CSGraph({ entities }: any) {
  const pos = [{ left: '45%', top: '35%' }, { left: '70%', top: '15%' }, { left: '20%', top: '55%' }, { left: '65%', top: '60%' }, { left: '35%', top: '10%' }, { left: '15%', top: '25%' }]
  const icons = ['📦', '💡', '🎬', '⚙️', '🔧', '📄']
  return <div style={{ height: 220, background: '#f8f9fa', borderRadius: 10, position: 'relative', overflow: 'hidden' }}>
    {(entities || []).slice(0, 6).map((e: any, i: number) => <div key={i} title={e.name} style={{ position: 'absolute', ...pos[i], background: 'white', border: '2.5px solid #667eea', borderRadius: '50%', width: 56, height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, cursor: 'pointer', transition: 'all .3s', zIndex: 2, transform: 'translate(-50%,-50%)' }}
      onMouseEnter={e => { const t = e.currentTarget as HTMLElement; t.style.transform = 'translate(-50%,-50%) scale(1.25)'; t.style.boxShadow = '0 6px 16px rgba(102,126,234,0.35)' }}
      onMouseLeave={e => { const t = e.currentTarget as HTMLElement; t.style.transform = 'translate(-50%,-50%) scale(1)'; t.style.boxShadow = 'none' }}>{icons[i] || '●'}</div>)}
    {(entities || []).length >= 2 && <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}><line x1="50%" y1="35%" x2="70%" y2="15%" stroke="#667eea" strokeWidth={2.5} /><line x1="50%" y1="35%" x2="20%" y2="55%" stroke="#adb5bd" strokeWidth={1.5} /><line x1="70%" y1="15%" x2="65%" y2="60%" stroke="#adb5bd" strokeWidth={1.5} /></svg>}
  </div>
}

// ══════════════════════ 主仪表盘 ══════════════════════
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
        if (!mR && !lR) { setError('无法连接后端'); setLoading(false); return }
        setMem(mR || {}); setLrn(lR || {}); setGraph(gR); setRules(rR || []); setEpisodes(eR || []); setAgents(aR || []); setHeatmap(hR); setCalibration(cR); setDream(dR); setSkills(Object.values(sR || {})); setAchievements(achR?.achievements || []); setLoading(false)
      }).catch((e: any) => { setError(`加载失败: ${e.message}`); setLoading(false) })
    let ws: WebSocket; try { ws = new WebSocket('ws://localhost:8741/ws'); ws.onmessage = e => { const d = JSON.parse(e.data); setLrn((p: any) => p?.q_learning ? { ...p, q_learning: { ...p.q_learning, nonzero: d.ql_nonzero, buffer: d.ql_buffer }, metacognition: { ...p.metacognition, health: d.health, accuracy: d.accuracy, score: d.score } } : p) } } catch { }
    return () => { try { ws?.close() } catch { } }
  }, [])

  if (loading) return <div style={{ padding: 100, textAlign: 'center', color: 'white' }}><div style={{ fontSize: 56, marginBottom: 16 }}>🧠</div><div style={{ fontSize: 20, fontWeight: 700 }}>藏慧晶核正在唤醒…</div><div style={{ marginTop: 8, opacity: 0.6, fontSize: 13 }}>连接记忆与学习系统</div></div>
  if (error) return <div style={{ ...c.card, padding: 60, textAlign: 'center', maxWidth: 500, margin: '60px auto' }}><div style={{ fontSize: 24, fontWeight: 700, color: '#e03131' }}>连接失败</div><div style={{ marginTop: 8, color: '#868e96' }}>{error}</div><div style={{ marginTop: 16, fontSize: 12, color: '#adb5bd' }}>请确认后端已启动: <code>python start_server.py</code></div></div>

  const m: any = mem || {}; const l: any = lrn || {}
  const qlpct = l?.q_learning?.nonzero_pct || 0; const qlnz = l?.q_learning?.nonzero || 0
  const entities = graph?.nodes || []
  const cognitive = calcCognitiveAge(m, l)

  // 人物形象：根据年龄选择
  const avatarEmoji = cognitive.age <= 5 ? '👶' : cognitive.age <= 8 ? '🧒' : cognitive.age <= 12 ? '🧑' : '🧑‍🎓'
  const avatarColors = ['#fcc2d7', '#d0bfff', '#a5d8ff', '#ffd8a8']

  return <div>
    {/* ═══════════ 认知年龄 Hero ═══════════ */}
    <div style={{ background: 'rgba(255,255,255,0.92)', borderRadius: 20, padding: '30px 36px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap', boxShadow: '0 4px 20px rgba(102,126,234,0.1)', position: 'relative', overflow: 'hidden' }}>
      {/* 装饰背景 */}
      <div style={{ position: 'absolute', right: -20, top: -30, fontSize: 140, opacity: 0.06, pointerEvents: 'none' }}>🧠</div>
      <div style={{ position: 'absolute', left: '40%', bottom: -10, width: 200, height: 4, background: 'linear-gradient(90deg, transparent, #667eea44, transparent)', borderRadius: 2 }} />

      {/* 人物形象 */}
      <div style={{ textAlign: 'center', minWidth: 100 }}>
        <div style={{ fontSize: 64, filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.1))', transition: 'transform .3s', cursor: 'pointer' }}
          onMouseEnter={e => (e.currentTarget as HTMLElement).style.transform = 'scale(1.1)'}
          onMouseLeave={e => (e.currentTarget as HTMLElement).style.transform = 'scale(1)'}>
          {avatarEmoji}
        </div>
        <div style={{ marginTop: 8, fontSize: 11, color: '#868e96', fontWeight: 600, letterSpacing: 1 }}>{cognitive.stage}</div>
      </div>

      {/* 年龄信息 */}
      <div style={{ flex: 1, minWidth: 200 }}>
        <div style={{ fontSize: 13, color: '#adb5bd', fontWeight: 600, letterSpacing: 2, marginBottom: 6, textTransform: 'uppercase' }}>认知年龄评估</div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontSize: 56, fontWeight: 900, color: '#667eea', lineHeight: 1, fontFamily: 'Georgia, serif' }}>{cognitive.age}</span>
          <span style={{ fontSize: 18, color: '#868e96', fontWeight: 600 }}>岁</span>
          <span style={{ fontSize: 14, color: '#adb5bd' }}>— 相当于人类 {cognitive.age} 岁{cognitive.age <= 5 ? '幼儿' : cognitive.age <= 8 ? '儿童' : cognitive.age <= 12 ? '少年' : '青少年'}</span>
        </div>
        <div style={{ marginTop: 12, color: '#495057', fontSize: 14, lineHeight: 1.7 }}>{cognitive.desc}</div>
        {cognitive.traits.length > 0 && <div style={{ marginTop: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {cognitive.traits.map((t: string, i: number) => <Tag key={i} text={t} color={avatarColors[i % 4]} />)}
        </div>}
      </div>

      {/* 关键指标摘要 */}
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        {[{ v: m?.knowledge_graph?.entities || 0, l: '知识实体', c: '#667eea' }, { v: qlnz, l: '已学习状态', c: '#764ba2' }, { v: m?.p3_episodic_memory?.total || 0, l: '情景记忆', c: '#51cf66' }, { v: rules.length, l: '程序规则', c: '#ff922b' }].map((k, i) => (
          <div key={i} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 30, fontWeight: 900, color: k.c, fontFamily: 'Georgia, serif' }}>{k.v}</div>
            <div style={{ fontSize: 11, color: '#adb5bd', marginTop: 4 }}>{k.l}</div>
          </div>
        ))}
      </div>
    </div>

    {/* ═══════════ Agent 中心（与认知年龄同级） ═══════════ */}
    <div style={{ background: 'rgba(255,255,255,0.92)', borderRadius: 20, padding: '24px 30px', marginBottom: 24, boxShadow: '0 4px 20px rgba(102,126,234,0.1)' }}>
      <div style={{ fontSize: 12, color: '#868e96', fontWeight: 700, letterSpacing: 3, marginBottom: 18, textTransform: 'uppercase' }}>🤖 Agent 中心 · 实时连接状态</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
        {agents.map((a: any) => {
          const statusColors: Record<string,string> = {active:'#40c057',standby:'#fd7e14',registered:'#adb5bd',offline:'#868e96'}
          const sc = statusColors[a.status] || '#adb5bd'
          const neuralActive = a.neural_active
          const wmActive = a.wm_active
          return (
            <div key={a.id} style={{ background: '#f8f9fa', borderRadius: 14, padding: '18px 20px', border: `2px solid ${connected ? 'rgba(64,192,87,0.2)' : 'rgba(173,181,189,0.2)'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ width: 40, height: 40, borderRadius: '50%', background: connected ? 'linear-gradient(135deg,#40c057,#2f9e44)' : 'linear-gradient(135deg,#adb5bd,#868e96)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, color: 'white' }}>{a.id[0].toUpperCase()}</div>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#2c3e50' }}>{a.id}</div>
                    <div style={{ fontSize: 11, color: statusColor, fontWeight: 600 }}>{statusText}</div>
                  </div>
                </div>
                <span style={{ background: '#667eea', color: 'white', padding: '3px 10px', borderRadius: 10, fontSize: 11 }}>{a.actions} 动作</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 14px', fontSize: 12, color: '#495057' }}>
                <div>🧠 Q学习: <strong>{a.ql_nonzero}/{a.ql_total}</strong></div>
                <div>📒 情景: <strong>{a.em_episodes} 条</strong></div>
                <div>🩺 健康: <strong style={{color: a.health==='good'?'#40c057':'#fd7e14'}}>{a.health}</strong></div>
                <div>📐 准确率: <strong>{(a.accuracy*100).toFixed(0)}%</strong></div>
                <div>🧬 神经: <strong style={{color:neuralActive?'#40c057':'#adb5bd'}}>{neuralActive?'已激活':'未激活'}</strong></div>
                <div>🌍 WM: <strong style={{color:wmActive?'#40c057':'#adb5bd'}}>{wmActive?`${l?.world_model?.train_steps||0}步`:'就绪'}</strong></div>
              </div>
            </div>
          )
        })}
      </div>
    </div>

    {/* ═══════════ 成就 ═══════════ */}
    {achievements.length > 0 && <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
      {achievements.map((a: any) => <div key={a.id} style={{ background: 'rgba(255,255,255,0.88)', padding: '7px 16px', borderRadius: 20, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 1px 4px rgba(0,0,0,0.06)', backdropFilter: 'blur(4px)' }}>{a.icon} {a.title} {a.level >= 2 && <span style={{ fontSize: 10, background: '#667eea', color: '#fff', borderRadius: 8, padding: '1px 6px', fontWeight: 700 }}>Lv{a.level}</span>}</div>)}
    </div>}

    {/* ═══════════ 核心记忆模块 ═══════════ */}
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontWeight: 700, letterSpacing: 3, marginBottom: 14, textTransform: 'uppercase' }}>核心记忆系统</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 18, marginBottom: 24 }}>
        <Card><CardHead icon="📒" title="情景记忆" badge={`${m?.p3_episodic_memory?.total ?? 0} 条`} badgeColor="#667eea" />
          {episodes.slice(0, 3).map((ep: any, i: number) => <MemCard key={i} time={(ep.when || '').slice(0, 16) || '未知时间'} content={ep.what || '无内容'} />)}
        </Card>
        <Card><CardHead icon="📝" title="程序记忆" badge={`${rules.length} 条`} badgeColor="#51cf66" />
          {rules.slice(0, 2).map((r: any, i: number) => <div key={i} style={{ margin: '10px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}><span style={{ fontSize: 14, fontWeight: 600, color: '#2c3e50' }}>{r.name}</span><span style={{ fontSize: 12, color: (r.success_rate || 0) >= 0.7 ? '#40c057' : '#fd7e14', fontWeight: 700 }}>{(r.success_rate * 100).toFixed(0)}%</span></div>
            <Progress label="" value={(r.success_rate || 0) * 100} />
            <div style={{ fontSize: 11, color: '#adb5bd', marginTop: 4 }}>{r.attempts || 0} 次应用</div>
          </div>)}
        </Card>
        <Card><CardHead icon="🕸️" title="知识图谱" badge={`${m?.knowledge_graph?.entities ?? 0} 实体`} badgeColor="#764ba2" /><CSGraph entities={entities} /></Card>
      </div>
    </div>

    {/* ═══════════ 学习系统 ═══════════ */}
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontWeight: 700, letterSpacing: 3, marginBottom: 14, textTransform: 'uppercase' }}>学习与认知</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 18, marginBottom: 24 }}>
        <Card><CardHead icon="🎯" title="学习进度" badge={`${qlpct.toFixed(0)}%`} badgeColor={qlpct >= 50 ? '#40c057' : '#fd7e14'} />
          <Progress label="Q表非零覆盖率" value={qlpct} color="linear-gradient(90deg,#667eea,#764ba2)" sub={`${qlnz} / ${l?.q_learning?.total || 700} 状态已学习`} />
          <div style={{ marginTop: 16 }}><div style={{ fontSize: 13, fontWeight: 700, color: '#2c3e50', marginBottom: 10 }}>技能树 Top 3</div><div style={{ display: 'flex', gap: 10 }}>
            {(heatmap?.rows || []).slice(0, 3).map((row: any, i: number) => {
              const lv = Math.min(5, Math.ceil(Math.max(...(row.values || []).map(Math.abs)) * 5))
              return <SkillCard key={i} label={`状态 #${row.state}`} level={lv} color={['#667eea', '#764ba2', '#40c057'][i]} />
            })}
          </div></div>
        </Card>
        <Card><CardHead icon="🩺" title="自我诊断" badge={l?.metacognition?.health || '?'} badgeColor={l?.metacognition?.health === 'good' ? '#40c057' : l?.metacognition?.health === 'warning' ? '#fd7e14' : '#e03131'} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[{ l: '健康分', v: `${l?.metacognition?.score?.toFixed(0) || '?'}%`, c: '#667eea' }, { l: 'ECE', v: calibration?.ece?.toFixed(4) || '?', c: (calibration?.ece || 0) < 0.1 ? '#40c057' : '#fd7e14' }, { l: '决策数', v: l?.metacognition?.decisions || 0, c: '#764ba2' }, { l: '准确率', v: `${(l?.metacognition?.accuracy * 100).toFixed(0)}%`, c: '#51cf66' }, { l: '连续失败', v: l?.metacognition?.failures || 0, c: l?.metacognition?.failures > 2 ? '#e03131' : '#868e96' }, { l: '异常数', v: l?.metacognition?.anomalies || 0, c: '#adb5bd' }].map((k, i) => (
              <div key={i} style={{ textAlign: 'center', padding: 12, background: '#f8f9fa', borderRadius: 10 }}>
                <div style={{ fontSize: 22, fontWeight: 900, color: k.c, fontFamily: 'Georgia, serif' }}>{k.v}</div>
                <div style={{ fontSize: 11, color: '#868e96', marginTop: 4 }}>{k.l}</div>
              </div>
            ))}
          </div>
        </Card>
        <Card><CardHead icon="🌙" title="记忆巩固" badge={dream?.phases ? '已运行' : '待运行'} badgeColor={dream?.phases ? '#40c057' : '#adb5bd'} />
          <div style={{ fontSize: 13, color: '#495057', lineHeight: 2 }}>
            <div>🕐 上次: <strong>{dream?.last?.slice(0, 19) || '无'}</strong></div>
            <div>⏱️ 累计: <strong>{dream?.total || 0} 次</strong></div>
          </div>
          {dream?.phases && <div style={{ background: '#f8f9fa', padding: 12, borderRadius: 10, margin: '10px 0', maxHeight: 160, overflowY: 'auto' }}>
            {Object.entries(dream.phases as Record<string, number>).filter(([, v]) => v !== undefined && v > 0).map(([k, v]) => <div key={k} style={{ fontSize: 12, color: '#495057', padding: '2px 0' }}>✅ {k}: {v}</div>)}
          </div>}
          <button style={btnPrimary} onClick={async () => { const r = await F('/dream/run'); if (r) setDream(r) }}>🌙 立即运行巩固</button>
        </Card>
      </div>
    </div>

    {/* ═══════════ 工具与协作 ═══════════ */}
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontWeight: 700, letterSpacing: 3, marginBottom: 14, textTransform: 'uppercase' }}>工具与协作</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 18, marginBottom: 24 }}>
        {/* 便签板 */}
        <Card><CardHead icon="📝" title="便签板" badge={m?.p1_working_memory?.task ? '活跃' : '空闲'} badgeColor={m?.p1_working_memory?.task ? '#40c057' : '#adb5bd'} />
          <div style={{ fontSize: 13, color: '#495057', lineHeight: 2.2 }}>
            <div>📌 <strong>{m?.p1_working_memory?.task || '空闲'}</strong></div>
            <div>🎯 {m?.p1_working_memory?.goal || '无目标'}</div>
            <div>📚 栈深: {m?.p1_working_memory?.stack_depth ?? 0}</div>
            <div>🔑 {(m?.p1_working_memory?.context_keys || []).slice(0, 5).join(' · ') || '无上下文'}</div>
          </div>
        </Card>
        {/* 搜索 */}
        <Card><CardHead icon="🔍" title="记忆搜索" badge={`${m?.p2_vector_memory?.total_vectors ?? 0} 向量`} badgeColor="#667eea" />
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={searchQ} onChange={e => setSearchQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && F(`/search?q=${encodeURIComponent(searchQ)}&limit=5`).then(setSearchR)} placeholder="搜索实体、情景…" style={{ flex: 1, padding: '10px 14px', borderRadius: 10, border: '2px solid #e9ecef', fontSize: 13, outline: 'none', transition: 'border-color .3s' }} onFocus={e => e.currentTarget.style.borderColor = '#667eea'} onBlur={e => e.currentTarget.style.borderColor = '#e9ecef'} />
            <button onClick={async () => setSearchR(await F(`/search?q=${encodeURIComponent(searchQ)}&limit=5`))} style={{ padding: '10px 18px', borderRadius: 10, background: '#667eea', color: 'white', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>搜索</button>
          </div>
          {searchR && <div style={{ marginTop: 12, fontSize: 12 }}>
            {(searchR.kg || []).map((e: any, i: number) => <Tag key={`k${i}`} text={`${e.name} (${e.type})`} color="#667eea" />)}
            {(searchR.em || []).map((e: any, i: number) => <div key={`e${i}`} style={{ marginTop: 4, color: '#868e96', padding: '4px 0' }}>[{e.outcome}] {e.what?.slice(0, 60)}</div>)}
          </div>}
          <div style={{ marginTop: 12, fontSize: 11, color: '#adb5bd' }}>📐 嵌入维度: {m?.p2_vector_memory?.embedding_dim || 0} · 集合: {m?.p2_vector_memory?.collection || 'ChromaDB'}</div>
        </Card>
      </div>
    </div>

    {/* ═══════════ 高级认知 ═══════════ */}
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontWeight: 700, letterSpacing: 3, marginBottom: 14, textTransform: 'uppercase' }}>高级认知能力</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 18, marginBottom: 24 }}>
        <Card><CardHead icon="⚡" title="自动技能" badge={`${skills.length} 个`} badgeColor="#f472b6" />
          {skills.length > 0 ? skills.slice(0, 5).map((s: any, i: number) => <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #f1f3f5' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ fontSize: 13, fontWeight: 600 }}>{s.action}</span><span style={{ fontSize: 11, color: '#868e96' }}>{s.success_count} 次</span></div>
            <div style={{ fontSize: 11, color: '#adb5bd', marginTop: 2 }}>{(s.context_patterns || []).slice(0, 4).join(', ')}</div>
          </div>) : <div style={{ color: '#adb5bd', padding: 20, textAlign: 'center' }}>暂无自动提取的技能</div>}
        </Card>
        <Card><CardHead icon="🔄" title="知识迁移" badge={`${l?.transfer?.total_transfers || 0} 次`} badgeColor="#667eea" />
          <div style={{ fontSize: 13, color: '#495057', lineHeight: 2.2 }}>
            <div>📦 档案: <strong>{l?.transfer?.total_profiles || 0}</strong> 个项目</div>
            <div>🔁 迁移: <strong>{l?.transfer?.total_transfers || 0}</strong> 次</div>
          </div>
        </Card>
        <Card><CardHead icon="🧬" title="高级认知" badge={l?.world_model?.train_steps > 0 ? '活跃' : l?.neural?.train_steps > 0 ? '部分活跃' : '待机'} badgeColor={l?.world_model?.train_steps > 0 ? '#40c057' : l?.neural?.train_steps > 0 ? '#fd7e14' : '#adb5bd'} />
          <div style={{ fontSize: 13, color: '#495057', lineHeight: 2.2 }}>
            <div>🌍 世界模型: {l?.world_model?.train_steps > 0 ? <strong>{l?.world_model?.train_steps} 步</strong> : <span style={{color:'#fd7e14'}}>{l?.world_model?.status || '就绪（新数据自动训练）'}</span>}</div>
            <div>🧠 神经模式: {l?.neural?.train_steps > 0 ? <strong>{l?.neural?.train_steps} 步</strong> : <span style={{color:'#adb5bd'}}>未启用（neural_mode=tabular）</span>}</div>
            <div>⚙️ 元学习: {l?.meta_learner?.adjustments || 0} 次调节</div>
            <div>⏰ 前瞻: {m?.prospective?.active || 0} 活跃 · {m?.prospective?.completed || 0} 完成</div>
            <div>👁️ 感知: 屏幕 {m?.perception?.screen?.captures || 0} 次 · 对话 {m?.perception?.conversation?.total_turns || 0} 轮</div>
          </div>
        </Card>
      </div>
    </div>

    {/* ═══════════ 记忆分布 ═══════════ */}
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontWeight: 700, letterSpacing: 3, marginBottom: 14, textTransform: 'uppercase' }}>记忆分布</div>
      <Card>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <Progress label="📒 情景记忆" value={Math.round((m?.p3_episodic_memory?.total || 0) / Math.max(1, (m?.p3_episodic_memory?.total || 0) + rules.length + (m?.knowledge_graph?.entities || 1)) * 100)} color="linear-gradient(90deg,#667eea,#4c6ef5)" />
          <Progress label="📝 程序记忆" value={Math.round(rules.length / Math.max(1, (m?.p3_episodic_memory?.total || 0) + rules.length + (m?.knowledge_graph?.entities || 1)) * 100)} color="linear-gradient(90deg,#40c057,#2f9e44)" />
          <Progress label="🕸️ 知识图谱" value={Math.round((m?.knowledge_graph?.entities || 0) / Math.max(1, (m?.p3_episodic_memory?.total || 0) + rules.length + (m?.knowledge_graph?.entities || 1)) * 100)} color="linear-gradient(90deg,#fd7e14,#e8590c)" />
          <Progress label="🧠 工作记忆" value={10} color="linear-gradient(90deg,#cc5de8,#9c36b5)" />
          <Progress label="🎯 Q学习" value={qlpct} color="linear-gradient(90deg,#fcc419,#f59f00)" />
        </div>
      </Card>
    </div>
  </div>
}
