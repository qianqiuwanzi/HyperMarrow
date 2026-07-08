import React, { useState, useEffect } from 'react'

const API = 'http://localhost:8741/api/v1'

interface LicenseInfo {
  mode: string
  plan: string
  license_status?: string
  expiry?: string | null
  max_devices?: number
  features_enabled: number
  features_total: number
  features: Record<string, boolean>
  user?: { name: string; email: string }
}

export default function LicenseStatus() {
  const [license, setLicense] = useState<LicenseInfo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/license/status`)
      .then(r => r.json())
      .then(d => { setLicense(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ color: '#999', fontSize: 12 }}>加载中...</div>
  if (!license) return null

  const isCommercial = license.mode === 'commercial'
  const isActive = license.license_status === 'valid' || license.license_status === 'offline'

  return (
    <div style={{
      background: 'rgba(255,255,255,0.95)', borderRadius: 10,
      padding: '14px 18px', marginBottom: 20, boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontWeight: 600, fontSize: 14, color: '#333' }}>
            {isCommercial ? '🔐 商业版' : '🎁 社区版'}
          </span>
          {isCommercial && (
            <span style={{
              marginLeft: 10, fontSize: 12, padding: '2px 8px', borderRadius: 10,
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
        </div>
        <div style={{ fontSize: 12, color: '#666' }}>
          功能: {license.features_enabled}/{license.features_total} 启用
          {license.expiry && ` | 到期: ${license.expiry}`}
          {license.max_devices && license.max_devices > 0 && ` | 设备: ${license.max_devices}`}
        </div>
      </div>
    </div>
  )
}
