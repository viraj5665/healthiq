import { useEffect, useRef, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { NavBar } from './components/NavBar'
import RiskOverview from './pages/RiskOverview'
import BedForecast from './pages/BedForecast'
import Alerts from './pages/Alerts'
import Reports from './pages/Reports'
import { fetchHealth } from './lib/api'

function WarmupBanner() {
  const [show, setShow] = useState(false)
  const [done, setDone] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    timerRef.current = setTimeout(() => setShow(true), 3000)

    fetchHealth()
      .then(() => {
        if (timerRef.current) clearTimeout(timerRef.current)
        setShow(false)
        setDone(true)
      })
      .catch(() => {
        if (timerRef.current) clearTimeout(timerRef.current)
        setShow(false)
        setDone(true)
      })

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  if (!show || done) return null

  return (
    <div style={{
      background: 'rgba(245,201,122,0.07)',
      borderBottom: '1px solid rgba(245,201,122,0.2)',
      padding: '8px 32px',
      display: 'flex',
      alignItems: 'center',
      gap: 10,
    }}>
      <span style={{
        display: 'inline-block',
        width: 7, height: 7,
        borderRadius: '50%',
        background: '#F5C97A',
        animation: 'pulse 1.2s ease-in-out infinite',
      }} />
      <span style={{
        fontSize: 11,
        color: '#F5C97A',
        fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: '0.04em',
      }}>
        Backend warming up — Render free tier spins down after inactivity.
        First request may take 30–60 s.
      </span>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
    </div>
  )
}

export default function App() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#0A0E17' }}>
      <NavBar />
      <WarmupBanner />
      <main style={{ flex: 1, overflowY: 'auto' }}>
        <Routes>
          <Route path="/"         element={<RiskOverview />} />
          <Route path="/forecast" element={<BedForecast />} />
          <Route path="/alerts"   element={<Alerts />} />
          <Route path="/reports"  element={<Reports />} />
        </Routes>
      </main>
    </div>
  )
}
