import React, { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'

const API = 'http://localhost:8741/api/v1'

export default function App() {
  const [mounted, setMounted] = useState(false)
  const [license, setLicense] = useState<any>(null)
  useEffect(() => setMounted(true), [])
  useEffect(() => {
    fetch(`${API}/license/status`)
      .then(r => r.json())
      .then(d => setLicense(d))
      .catch(() => {})
  }, [])

  const isCommercial = license?.mode === 'commercial'
  const isActive = license?.license_status === 'valid' || license?.license_status === 'offline'

  return (
    <div style={{
      minHeight:'100vh',
      background:'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding:20,
      fontFamily:'-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      <div style={{maxWidth:1200, margin:'0 auto'}}>
        <div style={{
          background:'rgba(255,255,255,0.95)', padding:'16px 30px', borderRadius:12,
          marginBottom:20, display:'flex', justifyContent:'space-between', alignItems:'center',
          boxShadow:'0 4px 6px rgba(0,0,0,0.1)', flexWrap:'wrap', gap:10
        }}>
          <h1 style={{fontSize:24, color:'#667eea', margin:0}}>🧠 智商藏不住 · 记忆中心</h1>
          {license && (
            <div style={{ display:'flex', alignItems:'center', gap:12, fontSize:13 }}>
              <span style={{ fontWeight:600, color:'#333' }}>
                {isCommercial ? '🔐 商业版' : '🎁 社区版'}
              </span>
              {isCommercial && (
                <span style={{
                  fontSize:12, padding:'2px 10px', borderRadius:10,
                  background: isActive ? '#d4edda' : '#f8d7da',
                  color: isActive ? '#155724' : '#721c24',
                }}>
                  {license.license_status === 'valid' ? '● 授权有效' :
                   license.license_status === 'offline' ? '◐ 离线模式' :
                   license.license_status === 'expired' ? '✕ 已过期' :
                   license.license_status === 'not_found' ? '○ 未激活' :
                   license.license_status}
                </span>
              )}
              <span style={{ color:'#666' }}>
                功能: {license.features_enabled}/{license.features_total}
                {license.expiry && ` | 到期: ${license.expiry}`}
              </span>
            </div>
          )}
        </div>
        {mounted && <Dashboard />}
      </div>
    </div>
  )
}

const btnStyle: React.CSSProperties = {padding:'8px 16px',border:'none',borderRadius:6,cursor:'pointer',fontSize:14,transition:'all .3s'}
const btnPrimaryStyle: React.CSSProperties = {...btnStyle, background:'#667eea', color:'white'}
