import { FEATURE_LABELS } from '../lib/api'
import type { ShapFeature } from '../types'

interface Props {
  features: ShapFeature[]
}

export function ShapBar({ features }: Props) {
  const maxAbs = Math.max(...features.map(f => Math.abs(f.shap_value)), 0.001)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {features.map((f) => {
        const pct = (Math.abs(f.shap_value) / maxAbs) * 100
        const positive = f.shap_value >= 0
        const color = positive ? '#F0997B' : '#5DCAA5'
        const label = FEATURE_LABELS[f.feature] ?? f.feature

        return (
          <div key={f.feature} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              width: 130,
              fontSize: 11,
              color: '#8FA3C8',
              textAlign: 'right',
              flexShrink: 0,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {label}
            </span>
            <div style={{ flex: 1, height: 3, background: '#1D2940', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${pct}%`,
                background: color,
                borderRadius: 2,
              }} />
            </div>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              color,
              width: 52,
              textAlign: 'left',
            }}>
              {positive ? '+' : ''}{f.shap_value.toFixed(3)}
            </span>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              color: '#5C6B8A',
              minWidth: 40,
            }}>
              ({typeof f.feature_value === 'number' ? f.feature_value.toFixed(1) : f.feature_value})
            </span>
          </div>
        )
      })}
    </div>
  )
}
