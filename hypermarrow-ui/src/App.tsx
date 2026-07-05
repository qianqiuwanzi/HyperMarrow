import React, { useState, useEffect, createContext } from 'react'
import Dashboard from './pages/Dashboard'

export const ThemeContext = createContext({ dark: true, toggle: () => {} })

export default function App() {
  const [dark, setDark] = useState(true)
  useEffect(() => { document.body.className = dark ? 'dark' : 'light' }, [dark])

  return (
    <ThemeContext.Provider value={{ dark, toggle: () => setDark(!dark) }}>
      <div style={{ minHeight: '100vh', background: dark ? '#0d1117' : '#f6f8fa', color: dark ? '#e6edf3' : '#1f2328', transition: 'all .3s' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', borderBottom: `1px solid ${dark ? '#21262d' : '#d0d7de'}` }}>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>
            <span style={{ color: '#58a6ff' }}>◈</span> HyperMarrow · Crystal Core
          </h1>
          <button onClick={() => { setDark(!dark); document.body.className = dark ? 'light' : 'dark' }}
            style={{ background: dark ? '#21262d' : '#eaeef2', border: 'none', color: dark ? '#e6edf3' : '#1f2328', padding: '8px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 14 }}>
            {dark ? '☀ Light' : '🌙 Dark'}
          </button>
        </header>
        <Dashboard dark={dark} />
      </div>
    </ThemeContext.Provider>
  )
}
