import { useEffect, useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { fetchReports, fetchReport, generateReport } from '../lib/api'
import type { ReportMeta, ReportFull } from '../types'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function EmptyState({ onGenerate, generating }: { onGenerate: () => void; generating: boolean }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      height: 320, gap: 16, padding: 32,
    }}>
      <div style={{
        width: 56, height: 56, borderRadius: 12,
        background: 'rgba(143,163,200,0.06)',
        border: '1px solid #1D2940',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 22,
      }}>
        📋
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: '#E2EAF8', marginBottom: 6 }}>
          No reports yet
        </div>
        <div style={{ fontSize: 12, color: '#5C6B8A', lineHeight: 1.6 }}>
          Generate your first AI-powered clinical summary.<br />
          The Reporting Agent gathers risk data, alerts,<br />
          and bed forecasts, then calls Claude to write it up.
        </div>
      </div>
      <GenerateButton onClick={onGenerate} generating={generating} />
    </div>
  )
}

function GenerateButton({ onClick, generating }: { onClick: () => void; generating: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={generating}
      style={{
        background: generating ? '#1D2940' : 'rgba(93,202,165,0.08)',
        border: '1px solid #5DCAA5',
        borderRadius: 6,
        padding: '9px 20px',
        color: generating ? '#5C6B8A' : '#5DCAA5',
        fontSize: 12,
        fontFamily: "'JetBrains Mono', monospace",
        cursor: generating ? 'not-allowed' : 'pointer',
        display: 'flex', alignItems: 'center', gap: 8,
        transition: 'all 0.15s',
        whiteSpace: 'nowrap',
      }}
    >
      {generating ? (
        <>
          <span style={{
            display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
            border: '1.5px solid #3A4B6A', borderTopColor: '#5DCAA5',
            animation: 'spin 0.8s linear infinite',
          }} />
          Claude is writing…
        </>
      ) : '✦  Generate new report'}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </button>
  )
}

export default function Reports() {
  const [reports, setReports]       = useState<ReportMeta[]>([])
  const [selected, setSelected]     = useState<ReportFull | null>(null)
  const [loading, setLoading]       = useState(true)
  const [loadingReport, setLoadingReport] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError]     = useState<string | null>(null)

  const loadList = useCallback(async () => {
    try {
      const rows = await fetchReports()
      setReports(rows)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadList() }, [loadList])

  async function selectReport(meta: ReportMeta) {
    if (selected?.id === meta.id) return
    setLoadingReport(true)
    try {
      const full = await fetchReport(meta.id)
      setSelected(full)
    } finally {
      setLoadingReport(false)
    }
  }

  async function handleGenerate() {
    setGenerating(true)
    setGenError(null)
    try {
      const full = await generateReport()
      await loadList()
      setSelected(full)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      // Extract the core error from the detail string
      const clean = msg.replace(/^Report generation failed: /, '')
      setGenError(clean)
    } finally {
      setGenerating(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, gap: 10 }}>
      <div style={{
        width: 18, height: 18, borderRadius: '50%',
        border: '2px solid #1D2940', borderTopColor: '#5DCAA5',
        animation: 'spin 0.8s linear infinite',
      }} />
      <span style={{ color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>
        Loading reports...
      </span>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1200, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#E2EAF8', marginBottom: 4 }}>
            Clinical Reports
          </div>
          <div style={{ fontSize: 12, color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace" }}>
            AI-generated summaries · Powered by Claude
          </div>
        </div>
        {reports.length > 0 && (
          <GenerateButton onClick={handleGenerate} generating={generating} />
        )}
      </div>

      {/* Error banner */}
      {genError && (
        <div style={{
          marginBottom: 20, padding: '12px 16px',
          background: 'rgba(240,153,123,0.08)', border: '1px solid rgba(240,153,123,0.4)',
          borderRadius: 8,
        }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: '#F0997B', marginBottom: 4 }}>
            Report generation failed
          </div>
          <div style={{ fontSize: 11, color: '#8FA3C8', fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.6 }}>
            {genError.includes('authentication_error') || genError.includes('invalid x-api-key')
              ? 'Anthropic API key is invalid or has no credits. Update ANTHROPIC_API_KEY in your .env file and restart the backend.'
              : genError}
          </div>
        </div>
      )}

      {reports.length === 0 ? (
        <div style={{
          background: '#121929', border: '1px solid #1D2940', borderRadius: 8, overflow: 'hidden',
        }}>
          <EmptyState onGenerate={handleGenerate} generating={generating} />
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16, alignItems: 'start' }}>

          {/* Left panel — report list */}
          <div style={{
            background: '#121929', border: '1px solid #1D2940', borderRadius: 8, overflow: 'hidden',
          }}>
            <div style={{
              padding: '10px 14px', borderBottom: '1px solid #1D2940',
              fontSize: 10, color: '#3A4B6A', fontFamily: "'JetBrains Mono', monospace",
              textTransform: 'uppercase', letterSpacing: '0.08em',
            }}>
              {reports.length} report{reports.length !== 1 ? 's' : ''}
            </div>
            {reports.map((r) => {
              const isActive = selected?.id === r.id
              return (
                <button
                  key={r.id}
                  onClick={() => selectReport(r)}
                  style={{
                    width: '100%', textAlign: 'left',
                    padding: '12px 14px',
                    background: isActive ? 'rgba(93,202,165,0.06)' : 'transparent',
                    cursor: 'pointer',
                    border: 'none',
                    borderBottom: '1px solid #151E30',
                    borderLeft: `3px solid ${isActive ? '#5DCAA5' : 'transparent'}`,
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'rgba(23,32,53,0.7)' }}
                  onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent' }}
                >
                  <div style={{
                    fontSize: 12, color: isActive ? '#5DCAA5' : '#E2EAF8',
                    marginBottom: 4, fontWeight: 500,
                  }}>
                    {fmtDate(r.generated_at)}
                  </div>
                  <div style={{ fontSize: 10, color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace" }}>
                    {r.model_version ?? 'claude'}
                    {r.duration_seconds ? ` · ${r.duration_seconds.toFixed(1)}s` : ''}
                  </div>
                </button>
              )
            })}
          </div>

          {/* Right panel — report content */}
          <div style={{
            background: '#121929', border: '1px solid #1D2940', borderRadius: 8,
            padding: '28px 32px', minHeight: 400,
          }}>
            {loadingReport ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#5C6B8A', fontSize: 13 }}>
                <div style={{
                  width: 14, height: 14, borderRadius: '50%',
                  border: '2px solid #1D2940', borderTopColor: '#5DCAA5',
                  animation: 'spin 0.8s linear infinite',
                }} />
                Loading report...
              </div>
            ) : selected ? (
              <>
                <div style={{
                  fontSize: 10, color: '#3A4B6A', fontFamily: "'JetBrains Mono', monospace",
                  marginBottom: 20, textTransform: 'uppercase', letterSpacing: '0.08em',
                }}>
                  Generated {fmtDate(selected.generated_at)}
                  {selected.duration_seconds ? ` · ${selected.duration_seconds.toFixed(1)}s` : ''}
                  {' · '}{selected.model_version}
                </div>
                <div style={{ '--md-body': '#C8D6F0' } as React.CSSProperties}>
                  <ReactMarkdown
                    components={{
                      h1: ({ children }) => (
                        <h1 style={{ fontSize: 20, fontWeight: 600, color: '#E2EAF8', margin: '0 0 16px', borderBottom: '1px solid #1D2940', paddingBottom: 12 }}>
                          {children}
                        </h1>
                      ),
                      h2: ({ children }) => (
                        <h2 style={{ fontSize: 15, fontWeight: 600, color: '#E2EAF8', margin: '24px 0 10px' }}>
                          {children}
                        </h2>
                      ),
                      h3: ({ children }) => (
                        <h3 style={{ fontSize: 13, fontWeight: 600, color: '#8FA3C8', margin: '18px 0 8px' }}>
                          {children}
                        </h3>
                      ),
                      p: ({ children }) => (
                        <p style={{ fontSize: 13, color: '#C8D6F0', lineHeight: 1.75, margin: '0 0 12px' }}>
                          {children}
                        </p>
                      ),
                      strong: ({ children }) => (
                        <strong style={{ color: '#E2EAF8', fontWeight: 600 }}>{children}</strong>
                      ),
                      ul: ({ children }) => (
                        <ul style={{ fontSize: 13, color: '#C8D6F0', lineHeight: 1.75, margin: '0 0 12px', paddingLeft: 20 }}>
                          {children}
                        </ul>
                      ),
                      li: ({ children }) => (
                        <li style={{ marginBottom: 4 }}>{children}</li>
                      ),
                      code: ({ children }) => (
                        <code style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 11, color: '#5DCAA5',
                          background: 'rgba(93,202,165,0.08)',
                          padding: '2px 5px', borderRadius: 3,
                        }}>
                          {children}
                        </code>
                      ),
                      hr: () => (
                        <hr style={{ border: 'none', borderTop: '1px solid #1D2940', margin: '20px 0' }} />
                      ),
                    }}
                  >
                    {selected.report_markdown}
                  </ReactMarkdown>
                </div>
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: '#3A4B6A', fontSize: 13 }}>
                Select a report from the list to view it.
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  )
}
