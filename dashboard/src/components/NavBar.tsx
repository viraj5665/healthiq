import { NavLink } from 'react-router-dom'

const links = [
  { to: '/',          label: 'Risk Overview' },
  { to: '/forecast',  label: 'Bed Forecast'  },
  { to: '/alerts',    label: 'Alerts'        },
  { to: '/reports',   label: 'Reports'       },
]

export function NavBar() {
  return (
    <nav
      style={{
        background: '#0D1220',
        borderBottom: '0.5px solid #1D2940',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        height: 52,
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 40 }}>
        <span style={{
          display: 'inline-block',
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: '#5DCAA5',
          boxShadow: '0 0 8px #5DCAA5',
        }} />
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 500,
          fontSize: 15,
          color: '#E2EAF8',
          letterSpacing: '0.02em',
        }}>
          Health<span style={{ color: '#5DCAA5' }}>IQ</span>
        </span>
      </div>

      {/* Nav links */}
      <div style={{ display: 'flex', gap: 4 }}>
        {links.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              padding: '6px 14px',
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 500,
              textDecoration: 'none',
              color: isActive ? '#5DCAA5' : '#5C6B8A',
              background: isActive ? 'rgba(93,202,165,0.08)' : 'transparent',
              transition: 'color 0.15s, background 0.15s',
            })}
          >
            {label}
          </NavLink>
        ))}
      </div>

      {/* Right: status dot */}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{
          display: 'inline-block',
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: '#5DCAA5',
          boxShadow: '0 0 6px #5DCAA5',
        }} />
        <span style={{ fontSize: 12, color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace" }}>
          API online
        </span>
      </div>
    </nav>
  )
}
