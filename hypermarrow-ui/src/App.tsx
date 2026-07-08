import React, { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import LicenseStatus from './pages/LicenseStatus'

export default function App() {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  return (
    <div style={{
      minHeight:'100vh',
      background:'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding:20,
      fontFamily:'-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      <div style={{maxWidth:1200, margin:'0 auto'}}>
        <div style={{
          background:'rgba(255,255,255,0.95)', padding:'20px 30px', borderRadius:12,
          marginBottom:20, display:'flex', justifyContent:'space-between', alignItems:'center',
          boxShadow:'0 4px 6px rgba(0,0,0,0.1)'
        }}>
          <h1 style={{fontSize:24, color:'#667eea', margin:0}}>🧠 HyperMarrow 藏慧 · 记忆中心</h1>
        </div>
        {mounted && <LicenseStatus />}
        {mounted && <Dashboard />}
      </div>
    </div>
  )
}

const btnStyle: React.CSSProperties = {padding:'8px 16px',border:'none',borderRadius:6,cursor:'pointer',fontSize:14,transition:'all .3s'}
const btnPrimaryStyle: React.CSSProperties = {...btnStyle, background:'#667eea', color:'white'}
