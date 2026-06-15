import { Routes, Route } from 'react-router-dom'
import { NavBar } from './components/NavBar'
import RiskOverview from './pages/RiskOverview'
import BedForecast from './pages/BedForecast'
import Alerts from './pages/Alerts'
import Reports from './pages/Reports'

export default function App() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#0A0E17' }}>
      <NavBar />
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
