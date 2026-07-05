import React, { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'

export default function App() {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  return (
    <div style={{ minHeight:'100vh', background:'linear-gradient(135deg,#0a1628 0%,#0d1f3c 40%,#0f2444 70%,#0a1628 100%)', color:'#e0e8f0', fontFamily:"'PingFang SC','Microsoft YaHei',sans-serif" }}>
      <header style={{ display:'flex',justifyContent:'space-between',alignItems:'center',padding:'14px 28px',
        background:'linear-gradient(90deg,rgba(30,80,180,0.15) 0%,rgba(30,120,220,0.08) 50%,rgba(30,80,180,0.15) 100%)',
        borderBottom:'1px solid rgba(80,150,255,0.15)',backdropFilter:'blur(12px)' }}>
        <h1 style={{ margin:0,fontSize:20,fontWeight:700,letterSpacing:2,
          background:'linear-gradient(90deg,#60a5fa,#818cf8,#60a5fa)',WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent' }}>
          ◈ HyperMarrow 藏慧 · 晶核控制台
        </h1>
        <span style={{ fontSize:12,color:'rgba(150,190,240,0.6)',letterSpacing:1 }}>
          记忆系统 · 学习系统 · 多Agent
        </span>
      </header>
      {mounted && <Dashboard />}
    </div>
  )
}
