const CONFIG: Record<string, { label: string; bg: string; color: string; glow?: string }> = {
  critical: { label: 'CRITICAL', bg: 'rgba(240,153,123,0.12)', color: '#F0997B', glow: '0 0 8px rgba(240,153,123,0.3)' },
  high:     { label: 'HIGH',     bg: 'rgba(240,135,92,0.12)',  color: '#F0875C', glow: '0 0 6px rgba(240,135,92,0.25)' },
  moderate: { label: 'MODERATE', bg: 'rgba(245,201,122,0.12)', color: '#F5C97A' },
  low:      { label: 'LOW',      bg: 'rgba(93,202,165,0.12)',  color: '#5DCAA5' },
}

interface Props {
  level: string
}

export function RiskLevelBadge({ level }: Props) {
  const c = CONFIG[level] ?? CONFIG.low
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        borderRadius: 4,
        background: c.bg,
        color: c.color,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        fontWeight: 500,
        letterSpacing: '0.08em',
        boxShadow: c.glow,
        whiteSpace: 'nowrap',
      }}
    >
      {c.label}
    </span>
  )
}
