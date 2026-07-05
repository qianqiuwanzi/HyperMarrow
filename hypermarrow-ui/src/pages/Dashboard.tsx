import React, { useState, useEffect, useRef } from 'react'
import * as d3 from 'd3'

const API = 'http://localhost:8741/api/v1'
const F = (p: string) => fetch(`${API}${p}`).then(r => r.json()).catch(() => null)

// ── 设计令牌（Design Tokens）────────────────────────────────────────────
const colors = {
  episodic: '#a78bfa', procedural: '#34d399', kg: '#60a5fa',
  qlearning: '#fbbf24', health: '#f87171', vector: '#38bdf8',
  dream: '#818cf8', skill: '#f472b6', meta: '#94a3b8'
}

const metaphors: Record<string,{icon:string, label:string, desc:string}> = {
  p1: {icon:'📝', label:'便签板', desc:'当前正在想什么'},
  p2: {icon:'🔍', label:'语义搜索', desc:'模糊记忆检索'},
  p3: {icon:'📒', label:'记忆相册', desc:'经历过的每一件事'},
  pm: {icon:'📋', label:'经验笔记', desc:'反复验证的规则'},
  kg: {icon:'🕸️', label:'思维导图', desc:'概念之间的关联'},
  ql: {icon:'🎯', label:'技能树', desc:'从经验中学习'},
  meta: {icon:'🩺', label:'自我诊断', desc:'对自己的判断'},
  dream: {icon:'🌙', label:'睡眠整理', desc:'定期巩固记忆'},
  skill: {icon:'⚡', label:'自动技能', desc:'从经验中涌现'},
  agent: {icon:'🤖', label:'Agent 中心', desc:'多 Agent 协作'},
  perception: {icon:'👁️', label:'感知通道', desc:'屏幕/语音/对话'},
  prospective: {icon:'⏰', label:'前瞻记忆', desc:'在 X 条件下做 Y'},
  transfer: {icon:'🔄', label:'知识迁移', desc:'跨 Agent 经验共享'},
  world: {icon:'🌍', label:'世界模型', desc:'预测行动后果'},
  neural: {icon:'🧬', label:'神经模式', desc:'学习到的表示'},
  calibrate: {icon:'📐', label:'置信度校准', desc:'预测 vs 实际'},
}

// ── 工具组件 ─────────────────────────────────────────────────────────────

function Card({children, style, hover=true, accent}: any) {
  const [h,setH]=useState(false)
  return <div style={{background:'linear-gradient(135deg,rgba(15,30,60,0.88),rgba(20,40,80,0.72))',borderRadius:16,padding:'18px 20px',
    border:`1px solid ${h&&hover?accent||'rgba(96,165,250,0.3)':'rgba(80,150,255,0.1)'}`,
    backdropFilter:'blur(10px)',transition:'all .25s',transform:h&&hover?'translateY(-2px)':'none',
    boxShadow:h&&hover?`0 8px 32px ${accent||'rgba(96,165,250,0.1)'}`:'none',...style}}
    onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)}>{children}</div>
}

function KPI({icon, metaphor, value, sub, accent, detail}: any) {
  const [open,setOpen]=useState(false)
  return <Card accent={accent} style={{flex:1,minWidth:180,cursor:'pointer'}}>
    <div onClick={()=>setOpen(!open)}>
      <div style={{fontSize:28,marginBottom:6}}>{metaphor?.icon||icon}</div>
      <div style={{fontSize:11,color:'rgba(160,200,240,0.5)',marginBottom:2}}>{metaphor?.label}</div>
      <div style={{fontSize:28,fontWeight:800,color:'#e0e8f0'}}>{value??'—'}</div>
      {sub?<div style={{fontSize:10,color:'rgba(140,180,220,0.45)',marginTop:4}}>{sub}</div>:null}
    </div>
    {open&&detail?<div style={{marginTop:10,padding:8,background:'rgba(255,255,255,0.03)',borderRadius:8,fontSize:11,lineHeight:1.6,color:'rgba(180,210,240,0.7)'}}>{detail}</div>:null}
  </Card>
}

function Tooltip({text,children}:any){return <span title={text} style={{cursor:'help',borderBottom:'1px dashed rgba(160,200,240,0.3)'}}>{children}</span>}

function Badge({text,color}:any){return <span style={{display:'inline-block',padding:'2px 8px',borderRadius:10,fontSize:10,fontWeight:600,background:`${color}22`,color,border:`1px solid ${color}33`,marginRight:4}}>{text}</span>}

function Section({title, icon, metaphor, children, action}: any) {
  const m = metaphor||{}
  return <Card>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:14,borderBottom:'1px solid rgba(80,150,255,0.08)',paddingBottom:10}}>
      <div>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <span style={{fontSize:18}}>{m.icon||icon}</span>
          <span style={{fontSize:14,fontWeight:700,color:'rgba(200,220,250,0.9)',letterSpacing:1}}>{title}</span>
        </div>
        {m.desc?<div style={{fontSize:10,color:'rgba(140,180,220,0.4)',marginTop:2}}>{m.desc}</div>:null}
      </div>
      {action}
    </div>
    {children}
  </Card>
}

// ── 动画数字 ─────────────────────────────────────────────────────────────
function AnimatedValue({value,duration=600}:{value:number,duration?:number}) {
  const [v,setV]=useState(0)
  useEffect(()=>{const t=setTimeout(()=>setV(value),50);return ()=>clearTimeout(t)},[value])
  return <span>{v.toFixed(0)}</span>
}

// ── 力导向知识图谱 ───────────────────────────────────────────────────────
function ForceGraph({data,w=580,h=340}:any){
  const ref=useRef<SVGSVGElement>(null)
  useEffect(()=>{
    if(!data?.nodes?.length||!ref.current)return
    const svg=d3.select(ref.current);svg.selectAll('*').remove()
    const nodes=(data.nodes||[]).slice(0,50)
    const edges=(data.edges||[]).filter((e:any)=>nodes.find((n:any)=>n.id===e.source)&&nodes.find((n:any)=>n.id===e.target)).slice(0,80)
    const sim=d3.forceSimulation(nodes).force('link',d3.forceLink(edges).id((d:any)=>d.id).distance(65)).force('charge',d3.forceManyBody().strength(-160)).force('center',d3.forceCenter(w/2,h/2))
    const color=d3.scaleOrdinal<string>().domain(['tool','skill','concept','phase','error_type','action']).range(['#60a5fa','#34d399','#a78bfa','#fbbf24','#f87171','#94a3b8'])
    svg.append('g').selectAll('line').data(edges).join('line').attr('stroke','rgba(80,150,255,0.2)').attr('stroke-width',(d:any)=>d.weight*2.5)
    const node=svg.append('g').selectAll('circle').data(nodes).join('circle').attr('r',(d:any)=>d.central?8:4.5).attr('fill',(d:any)=>color(d.type)).attr('stroke','rgba(255,255,255,0.15)').attr('stroke-width',1.5).call(d3.drag<any,any>().on('start',(e:any,d:any)=>{if(!e.active)sim.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y}).on('drag',(e:any,d:any)=>{d.fx=e.x;d.fy=e.y}).on('end',(e:any,d:any)=>{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null}))
    svg.append('g').selectAll('text').data(nodes.slice(0,25)).join('text').text((d:any)=>d.name&&d.name.length>14?d.name.slice(0,13)+'…':d.name||'').attr('font-size',8.5).attr('dx',7).attr('dy',3).attr('fill','rgba(160,200,240,0.5)')
    sim.on('tick',()=>{svg.selectAll('line').attr('x1',(d:any)=>d.source.x).attr('y1',(d:any)=>d.source.y).attr('x2',(d:any)=>d.target.x).attr('y2',(d:any)=>d.target.y);node.attr('cx',(d:any)=>d.x).attr('cy',(d:any)=>d.y);svg.selectAll('text').attr('x',(d:any)=>d.x).attr('y',(d:any)=>d.y)})
  },[data])
  return <svg ref={ref} width={w} height={h} style={{borderRadius:12}}/>
}

// ═══════════════════════════════════════════════════════════════════════════
export default function Dashboard() {
  const [mem,setMem]=useState<any>({})
  const [lrn,setLrn]=useState<any>({})
  const [graph,setGraph]=useState<any>(null)
  const [rules,setRules]=useState<any[]>([])
  const [episodes,setEpisodes]=useState<any[]>([])
  const [agents,setAgents]=useState<any[]>([])
  const [heatmap,setHeatmap]=useState<any>(null)
  const [calibration,setCalibration]=useState<any>(null)
  const [dream,setDream]=useState<any>(null)
  const [skills,setSkills]=useState<any[]>([])
  const [achievements,setAchievements]=useState<any[]>([])
  const [searchQ,setSearchQ]=useState(''); const [searchR,setSearchR]=useState<any>(null)
  const [loading,setLoading]=useState(true); const [error,setError]=useState('')
  const [pulse,setPulse]=useState(0)

  useEffect(()=>{
    Promise.all([F('/memory/overview'),F('/learning/overview'),F('/kg/graph'),F('/pm/rules'),F('/em/timeline?limit=60'),F('/agents'),F('/ql/heatmap'),F('/meta/calibration'),F('/dream/status'),F('/skills/list'),F('/achievements')])
      .then(([memR,lrnR,gR,rR,epR,agR,hmR,calR,drR,skR,achR])=>{
        if(!memR&&!lrnR){setError('无法连接后端 API (localhost:8741)');setLoading(false);return}
        setMem(memR||{});setLrn(lrnR||{});setGraph(gR);setRules(rR||[]);setEpisodes(epR||[]);setAgents(agR||[]);setHeatmap(hmR);setCalibration(calR);setDream(drR);setSkills(Object.values(skR||{}));setAchievements(achR?.achievements||[]);setLoading(false)
      }).catch((e:any)=>{setError(`加载失败: ${e.message}`);setLoading(false)})
    let ws:WebSocket;try{ws=new WebSocket('ws://localhost:8741/ws');ws.onmessage=e=>{const d=JSON.parse(e.data);setLrn((p:any)=>p?.q_learning?{...p,q_learning:{...p.q_learning,nonzero:d.ql_nonzero,buffer:d.ql_buffer},metacognition:{...p.metacognition,health:d.health,accuracy:d.accuracy,score:d.score}}:p);setPulse(p=>p+1)}}catch{};return()=>{try{ws?.close()}catch{}}
  },[])

  const doSearch=async()=>{if(!searchQ)return;setSearchR(await F(`/search?q=${encodeURIComponent(searchQ)}&limit=8`))}

  if(loading)return<div style={{padding:100,textAlign:'center'}}><div style={{fontSize:60}}>🧠</div><div style={{fontSize:24,fontWeight:800,background:'linear-gradient(90deg,#60a5fa,#818cf8)',WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent',marginTop:16}}>藏慧晶核正在唤醒…</div><div style={{marginTop:10,color:'rgba(160,200,240,0.4)',fontSize:13}}>正在连接记忆与学习系统</div></div>
  if(error)return<div style={{padding:100,textAlign:'center'}}><div style={{fontSize:22,fontWeight:700,color:'#f87171'}}>连接失败</div><div style={{marginTop:8,color:'rgba(160,200,240,0.5)',fontSize:13}}>{error}</div><div style={{marginTop:16,color:'rgba(160,200,240,0.35)',fontSize:12}}>请确认：<code style={{background:'rgba(255,255,255,0.05)',padding:'4px 8px',borderRadius:4}}>python start_server.py</code></div></div>

  const m:any=mem||{}; const l:any=lrn||{}
  const kpiList=[
    {icon:'📒',metaphor:metaphors.p3,value:m?.p3_episodic_memory?.total??'—',sub:`今日+0 · 重要性 ${m?.p3_episodic_memory?.avg_importance??0}`,accent:colors.episodic,detail:`含教训 ${m?.p3_episodic_memory?.with_lessons??0} 条 · success ${m?.p3_episodic_memory?.by_outcome?.success??0} · failure ${m?.p3_episodic_memory?.by_outcome?.failure??0}`},
    {icon:'📋',metaphor:metaphors.pm,value:m?.procedural_memory?.total_rules??'—',sub:'5级自动化规则',accent:colors.procedural},
    {icon:'🕸️',metaphor:metaphors.kg,value:m?.knowledge_graph?.entities??'—',sub:`${m?.knowledge_graph?.relationships??0} 条关系`,accent:colors.kg},
    {icon:'🎯',metaphor:metaphors.ql,value:`${l?.q_learning?.nonzero??'?'}/${l?.q_learning?.total??'?'}`,sub:`${l?.q_learning?.nonzero_pct??0}% 已学习`,accent:colors.qlearning,detail:`状态 ${l?.q_learning?.states??0} · α=${l?.q_learning?.alpha?.toFixed(3)??'?'} · ε=${l?.q_learning?.epsilon??'?'}`},
    {icon:'🩺',metaphor:metaphors.meta,value:`${l?.metacognition?.score?.toFixed(0)??'?'}%`,sub:`${l?.metacognition?.health??'?'} · ECE ${l?.metacognition?.ece?.toFixed(3)??'?'}`,accent:colors.health},
    {icon:'🔍',metaphor:metaphors.p2,value:m?.p2_vector_memory?.total_vectors??0,sub:m?.p2_vector_memory?.collection||'ChromaDB',accent:colors.vector},
  ]

  return <div style={{padding:'20px 28px',maxWidth:1440,margin:'0 auto'}}>
    {/* KPI 卡片 */}
    <div style={{display:'flex',gap:12,flexWrap:'wrap',marginBottom:18}}>
      {kpiList.map((k,i)=><KPI key={i} {...k} />)}
    </div>

    {/* 成就徽章 */}
    {achievements.length>0 && <div style={{display:'flex',gap:8,flexWrap:'wrap',marginBottom:18}}>
      {achievements.map((a:any)=><Tooltip key={a.id} text={a.desc}><div style={{padding:'6px 14px',borderRadius:20,background:'rgba(251,191,36,0.08)',border:'1px solid rgba(251,191,36,0.2)',fontSize:12,display:'flex',alignItems:'center',gap:6}}>
        <span>{a.icon}</span><span style={{color:'#fbbf24'}}>{a.title}</span>
        {a.level>=2?<span style={{fontSize:10,background:'#fbbf24',color:'#000',borderRadius:8,padding:'1px 6px'}}>Lv{a.level}</span>:null}
      </div></Tooltip>)}
    </div>}

    <div style={{display:'flex',gap:16,flexWrap:'wrap'}}>
      {/* ─── 左列 ─── */}
      <div style={{flex:2,minWidth:560}}>
        {/* 思维导图 (KG) */}
        <Section title="思维导图" metaphor={metaphors.kg}>
          {graph?.nodes?.length?<ForceGraph data={graph}/>:<div style={{color:'rgba(160,200,240,0.25)',padding:40,textAlign:'center'}}>🕸️ 知识网络正在生长中…</div>}
          <div style={{marginTop:8,display:'flex',gap:14,flexWrap:'wrap',fontSize:10,color:'rgba(160,200,240,0.4)'}}>
            {Object.entries(m.knowledge_graph?.types||{}).map(([t,n])=><Tooltip key={t} text={`${t}: ${n} 个实体`}><span>● {t}: {n as number}</span></Tooltip>)}
          </div>
        </Section>

        {/* 技能树 (QL) */}
        <Section title="技能树" metaphor={metaphors.ql} action={<span style={{fontSize:10,color:'rgba(160,200,240,0.4)'}}>Lv.{((l?.q_learning?.nonzero_pct??0)/10).toFixed(0)}</span>}>
          <div style={{marginBottom:8,fontSize:11,color:'rgba(160,200,240,0.5)'}}>
            <Tooltip text={`${l?.q_learning?.nonzero_pct??0}% 状态空间已学习`}>📊 总体进度</Tooltip>
          </div>
          <div style={{height:8,background:'rgba(255,255,255,0.05)',borderRadius:4,overflow:'hidden',marginBottom:16}}>
            <div style={{width:`${l?.q_learning?.nonzero_pct??0}%`,height:'100%',background:'linear-gradient(90deg,#fbbf24,#f59e0b)',borderRadius:4,transition:'width 1s'}}/>
          </div>
          {heatmap?.rows?.length?<div style={{overflowX:'auto'}}>
            <div style={{display:'flex',marginBottom:4,gap:4}}><div style={{width:36}}/>{(heatmap.actions||[]).map((a:string,i:number)=><div key={i} style={{flex:1,fontSize:9,color:'rgba(160,200,240,0.5)',textAlign:'center',minWidth:55}}>{a}</div>)}</div>
            {(heatmap.rows||[]).slice(0,12).map((row:any,i:number)=><div key={i} style={{display:'flex',gap:4,alignItems:'center',marginBottom:2}}>
              <div style={{width:36,fontSize:9,color:'rgba(160,200,240,0.4)'}}>S{row.state}</div>
              {(row.values||[]).map((v:number,j:number)=>{const int=Math.min(1,Math.abs(v)/0.5);const hue=v>0?'34,211,144':'248,113,113'
                return <Tooltip key={j} text={`${heatmap.actions[j]}: Q=${v.toFixed(4)}`}><div style={{flex:1,height:12,minWidth:55,borderRadius:3,background:`rgba(${hue},${int*0.8})`,border:j===row.best?'1px solid rgba(255,255,255,0.35)':'none',fontSize:7.5,color:'rgba(255,255,255,0.6)',textAlign:'center',lineHeight:'12px'}}>{v.toFixed(2)}</div></Tooltip>
              })}
            </div>)}
          </div>:<div style={{color:'rgba(160,200,240,0.25)',padding:16,textAlign:'center'}}>🎯 技能树等待训练数据…</div>}
        </Section>

        {/* 记忆相册 (EM) */}
        <Section title="记忆相册" metaphor={metaphors.p3}>
          <div style={{maxHeight:280,overflowY:'auto'}}>
            {episodes.length>0?episodes.slice(0,20).map((e:any,i:number)=><div key={i} style={{padding:'6px 0',borderBottom:'1px solid rgba(80,150,255,0.04)',display:'flex',alignItems:'center',gap:8}}>
              <Tooltip text={`情感: ${e.emotion||'?'} · 重要性: ${e.importance??0}/5`}><Badge text={e.outcome||'?'} color={e.outcome==='success'?'#34d399':e.outcome==='failure'?'#f87171':'#94a3b8'}/></Tooltip>
              <span style={{fontSize:12,flex:1}}>{e.what||''}</span>
              <span style={{fontSize:9,color:'rgba(160,200,240,0.3)'}}>{(e.when||'').slice(0,10)}</span>
            </div>):<div style={{color:'rgba(160,200,240,0.25)',padding:20,textAlign:'center'}}>📒 记忆相册还是空的…</div>}
          </div>
        </Section>
      </div>

      {/* ─── 右列 ─── */}
      <div style={{flex:1,minWidth:340}}>
        {/* 便签板 (P1) + 语义搜索 (P2) */}
        <Section title="便签板" metaphor={metaphors.p1}>
          <div style={{fontSize:12,lineHeight:2}}>
            <div><b style={{color:'#60a5fa'}}>当前任务：</b>{m?.p1_working_memory?.task||'空闲'}</div>
            <div><b style={{color:'#38bdf8'}}>目标：</b>{m?.p1_working_memory?.goal||'无'}</div>
            <div><b style={{color:'#a78bfa'}}>任务栈：</b>深度 {m?.p1_working_memory?.stack_depth??0}</div>
            <div><b style={{color:'#94a3b8'}}>活跃上下文：</b>{(m?.p1_working_memory?.context_keys||[]).slice(0,6).join(', ')||'无'}</div>
          </div>
        </Section>

        {/* 经验笔记 (PM) */}
        <Section title="经验笔记" metaphor={metaphors.pm}>
          <div style={{maxHeight:260,overflowY:'auto'}}>
            {rules.length>0?rules.slice(0,10).map((r:any,i:number)=><div key={i} style={{padding:'7px 0',borderBottom:'1px solid rgba(80,150,255,0.04)'}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                <span style={{fontSize:12.5,fontWeight:600,color:'#e0e8f0'}}>{r.name}</span>
                <Tooltip text={`自动化等级 ${r.level}/5`}><Badge text={`Lv${r.level}`} color={r.level>=4?'#34d399':r.level>=2?'#60a5fa':'#94a3b8'}/></Tooltip>
              </div>
              <div style={{display:'flex',gap:12,fontSize:10,color:'rgba(160,200,240,0.4)',marginTop:4}}>
                <Tooltip text={`${r.attempts||0} 次尝试`}><span>✓ {(r.success_rate*100).toFixed(0)}% 成功率</span></Tooltip>
                {r.patterns?.length>0?<Tooltip text={r.patterns.join(', ')}><span>📌 {r.patterns.slice(0,3).join(', ')}</span></Tooltip>:null}
              </div>
            </div>):<div style={{color:'rgba(160,200,240,0.25)',padding:16,textAlign:'center'}}>📋 经验笔记还是空的…</div>}
          </div>
        </Section>

        {/* 自我诊断 (Meta) */}
        <Section title="自我诊断" metaphor={metaphors.meta}>
          {calibration?<div>
            <div style={{fontSize:22,fontWeight:800,color:calibration.ece<0.1?'#34d399':calibration.ece<0.2?'#fbbf24':'#f87171',marginBottom:10}}>
              ECE = {calibration.ece?.toFixed(4)}
            </div>
            {(calibration.bins||[]).map((b:any,i:number)=><div key={i} style={{display:'flex',alignItems:'center',gap:8,marginTop:5,fontSize:10}}>
              <span style={{width:54,color:'rgba(160,200,240,0.4)'}}>{b.conf_low?.toFixed(1)}-{b.conf_high?.toFixed(1)}</span>
              <div style={{flex:1,height:8,background:'rgba(255,255,255,0.04)',borderRadius:4,overflow:'hidden'}}><div style={{width:`${(b.accuracy||0)*100}%`,height:'100%',background:'linear-gradient(90deg,#60a5fa,#a78bfa)',borderRadius:4}}/></div>
              <span style={{width:28,textAlign:'right',color:'rgba(160,200,240,0.5)'}}>{b.count||0}</span>
            </div>)}
            <div style={{marginTop:10,fontSize:10,color:'rgba(160,200,240,0.4)'}}>过度自信={calibration.overconfidence?.toFixed(3)} · 信心不足={calibration.underconfidence?.toFixed(3)}</div>
          </div>:<div style={{color:'rgba(160,200,240,0.25)',padding:12,textAlign:'center'}}>🩺 尚无校准数据</div>}
        </Section>

        {/* 睡眠整理 (Dream Cycle) */}
        <Section title="睡眠整理" metaphor={metaphors.dream} action={
          <button onClick={async()=>{const r=await F('/dream/run');if(r)setDream(r)}} style={{padding:'5px 14px',borderRadius:8,background:'linear-gradient(90deg,rgba(129,140,248,0.2),rgba(96,165,250,0.2))',border:'1px solid rgba(129,140,248,0.3)',color:'#a78bfa',cursor:'pointer',fontSize:11}}>立即运行</button>
        }>
          {dream?.phases?<div>
            {Object.entries(dream.phases as Record<string,number>).map(([k,v])=><div key={k} style={{display:'flex',alignItems:'center',gap:8,marginBottom:4,fontSize:10}}>
              <span style={{width:72,color:'rgba(160,200,240,0.45)'}}>{k}</span><div style={{flex:1,height:5,background:'rgba(255,255,255,0.04)',borderRadius:3}}><div style={{width:`${Math.min(100,v*5)}%`,height:'100%',background:'linear-gradient(90deg,#818cf8,#a78bfa)',borderRadius:3}}/></div><span style={{width:22,textAlign:'right',color:v?'#818cf8':'rgba(160,200,240,0.2)'}}>{v}</span>
            </div>)}
            <div style={{marginTop:6,fontSize:10,color:'rgba(160,200,240,0.35)'}}>上次: {(dream.last||'').slice(0,19)} · 共 {dream.total||0} 次</div>
          </div>:<div style={{color:'rgba(160,200,240,0.25)',padding:12,textAlign:'center'}}>🌙 睡眠整理等待首次运行…</div>}
        </Section>

        {/* 自动技能 + Agent 中心 */}
        <div style={{display:'flex',gap:16,flexWrap:'wrap'}}>
          <div style={{flex:1,minWidth:120}}>
            <Section title="自动技能" metaphor={metaphors.skill}>
              {skills.length>0?skills.slice(0,6).map((s:any,i:number)=><div key={i} style={{fontSize:10,padding:'3px 0'}}><Badge text={s.action||'?'} color="#f472b6"/> <span style={{color:'rgba(160,200,240,0.4)'}}>({s.success_count})</span></div>):<div style={{fontSize:10,color:'rgba(160,200,240,0.25)'}}>暂无自动技能</div>}
            </Section>
          </div>
          <div style={{flex:1,minWidth:120}}>
            <Section title="Agent 中心" metaphor={metaphors.agent}>
              {agents.map((a:any)=><div key={a.id} style={{fontSize:11,padding:'4px 0',display:'flex',justifyContent:'space-between'}}><span style={{fontWeight:600}}>{a.id}</span><span style={{color:'rgba(160,200,240,0.4)',fontSize:9}}>{a.actions}动作</span></div>)}
            </Section>
          </div>
        </div>
      </div>
    </div>

    {/* 底部搜索 */}
    <Card style={{marginTop:18}}>
      <div style={{display:'flex',gap:12,alignItems:'center'}}>
        <span style={{fontSize:22}}>🔍</span>
        <input value={searchQ} onChange={e=>setSearchQ(e.target.value)} onKeyDown={e=>e.key==='Enter'&&doSearch()} placeholder="搜索你的记忆…" style={{flex:1,padding:'10px 16px',borderRadius:10,border:'1px solid rgba(80,150,255,0.15)',background:'rgba(10,20,40,0.5)',color:'#e0e8f0',fontSize:14}}/>
        <button onClick={doSearch} style={{padding:'10px 24px',borderRadius:10,background:'linear-gradient(90deg,#3b82f6,#6366f1)',color:'#fff',border:'none',cursor:'pointer',fontSize:13,fontWeight:600}}>搜索</button>
        <button style={{padding:'10px 18px',borderRadius:10,background:'rgba(96,165,250,0.12)',border:'1px solid rgba(96,165,250,0.2)',color:'#60a5fa',cursor:'pointer',fontSize:11}}>📊 分享</button>
      </div>
      {searchR&&<div style={{marginTop:12,fontSize:12}}>
        {(searchR.kg||[]).map((e:any,i:number)=><span key={`k${i}`} style={{marginRight:8}}><Badge text={e.type||'?'} color="#60a5fa"/> {e.name}</span>)}
        {(searchR.em||[]).map((e:any,i:number)=><div key={`e${i}`} style={{marginTop:4,color:'rgba(160,200,240,0.55)'}}>[{e.outcome}] {e.what}</div>)}
      </div>}
    </Card>
  </div>
}
