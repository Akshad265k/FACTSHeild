import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

/* ── Safe fetch helper ──────────────────────────────────────────────────────── */
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const toApiUrl = (p) => (p.startsWith('http') ? p : `${API_BASE}${p}`)

const request = async (path, options = {}) => {
  let r
  try {
    r = await fetch(toApiUrl(path), {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch (networkErr) {
    throw new Error(
      'Could not reach the FACTSHIELD backend — is the Python API running?'
    )
  }

  // Read body text once; it may be empty on 204 or on error pages
  const text = await r.text()
  let body
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      throw new Error(
        'Unexpected response from the backend — received non-JSON data.'
      )
    }
  }

  if (!r.ok) {
    const detail = body?.detail || `Request failed (HTTP ${r.status})`
    throw new Error(detail)
  }

  return body
}

const save = (name, text, type = 'text/plain') => {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type }))
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}

const Empty = ({ title, text }) => (
  <section className="page empty">
    <h1>{title}</h1>
    <p>{text}</p>
  </section>
)

/* ── Inline error banner (dismissible) ──────────────────────────────────────── */
const InlineError = ({ message, onDismiss }) => {
  if (!message) return null
  return (
    <p className="alert bad inline-error">
      <span>{message}</span>
      <button className="dismiss" onClick={onDismiss} aria-label="Dismiss error">
        ×
      </button>
    </p>
  )
}

/* ── Trust badges ───────────────────────────────────────────────────────────── */
const TrustBadges = () => (
  <div className="trust-badges">
    <span className="badge">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
      Deterministic verification
    </span>
    <span className="badge">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
      No LLM matching
    </span>
  </div>
)

/* ── Upload & Analyse ───────────────────────────────────────────────────────── */
function Analyse({ done }) {
  const [mode, setMode] = useState('sample')
  const [samples, setSamples] = useState([])
  const [release, setRelease] = useState('')
  const [source, setSource] = useState('')
  const [hindi, setHindi] = useState('')
  const [marathi, setMarathi] = useState('')
  const [auto, setAuto] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const translationsReady = Boolean(source && hindi && marathi)

  // Load sample list and auto-select the first release
  useEffect(() => {
    request('/api/samples')
      .then((list) => {
        setSamples(list || [])
        if (list && list.length > 0) {
          setRelease(list[0].id)
        }
      })
      .catch((e) =>
        setError("Couldn't load sample releases — check the backend connection.")
      )
  }, [])

  const read = (set) => (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    const form = new FormData()
    form.append('file', f)
    fetch(toApiUrl('/api/documents/extract'), { method: 'POST', body: form })
      .then(async (r) => {
        const text = await r.text()
        if (!text) throw new Error('Empty response from document extraction.')
        let body
        try {
          body = JSON.parse(text)
        } catch {
          throw new Error('Unexpected response while extracting document.')
        }
        if (!r.ok) throw new Error(body.detail || 'Document extraction failed')
        set(body.text)
      })
      .catch((x) => setError(x.message))
  }

  const generateTranslations = async () => {
    setBusy(true)
    setError('')
    try {
      if (mode === 'sample') {
        if (!release) throw new Error('Please select a sample release first.')
        const sample = await request(`/api/samples/${release}`)
        setSource(sample.English)
        setHindi(sample.Hindi)
        setMarathi(sample.Marathi)
      } else {
        const generated = await request('/api/translate', {
          method: 'POST',
          body: JSON.stringify({ source_text: source }),
        })
        setHindi(generated.Hindi)
        setMarathi(generated.Marathi)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const run = async () => {
    setBusy(true)
    setError('')
    try {
      if (!translationsReady) {
        throw new Error('Generate or upload both translations before running QC.')
      }
      const payload = {
        source_text: source,
        hindi_text: hindi,
        marathi_text: marathi,
        auto_translate: false,
      }
      done(
        await request('/api/analyse', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
      )
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const TAB_ITEMS = [
    ['sample', '📁', 'Sample release'],
    ['paste', '📋', 'Paste text'],
    ['upload', '📤', 'Upload documents'],
  ]

  return (
    <section className="page">
      <i>ANALYSIS WORKSPACE</i>
      <h1>Verify multilingual facts before release.</h1>
      <TrustBadges />
      <p className="lead">
        The React console calls FACTSHIELD's existing deterministic Python
        engine—no matching or scoring logic is duplicated.
      </p>

      {/* ── Mode tabs ─────────────────────────────────────────────────── */}
      <div className="tabs">
        {TAB_ITEMS.map(([k, icon, label]) => (
          <button
            className={`tab-btn${mode === k ? ' tab-active' : ''}`}
            onClick={() => {
              setMode(k)
              setSource('')
              setHindi('')
              setMarathi('')
              setError('')
            }}
            key={k}
          >
            <span className="tab-icon">{icon}</span>
            {label}
          </button>
        ))}
      </div>

      {/* ── Sample release mode ───────────────────────────────────────── */}
      {mode === 'sample' && (
        <div className="card sample-card">
          <label>
            Prepared release
            <select
              value={release}
              onChange={(e) => {
                setRelease(e.target.value)
                setSource('')
                setHindi('')
                setMarathi('')
              }}
            >
              {samples.length === 0 && (
                <option value="">Select a release…</option>
              )}
              {samples.map((x) => (
                <option value={x.id} key={x.id}>
                  {x.label}
                </option>
              ))}
            </select>
          </label>
          <p>
            Trusted English, Hindi, and Marathi texts are loaded directly from
            the selected sample.
          </p>
          <InlineError message={error} onDismiss={() => setError('')} />
        </div>
      )}

      {/* ── Paste text mode ───────────────────────────────────────────── */}
      {mode === 'paste' && (
        <div className="fields">
          <label>
            Authoritative English
            <textarea
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="Paste the English release…"
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={auto}
              onChange={(e) => setAuto(e.target.checked)}
            />{' '}
            Automatically translate to Hindi and Marathi
          </label>
          {!auto && (
            <>
              <label>
                Hindi
                <textarea
                  value={hindi}
                  onChange={(e) => setHindi(e.target.value)}
                />
              </label>
              <label>
                Marathi
                <textarea
                  value={marathi}
                  onChange={(e) => setMarathi(e.target.value)}
                />
              </label>
            </>
          )}
          <InlineError message={error} onDismiss={() => setError('')} />
        </div>
      )}

      {/* ── Upload mode ───────────────────────────────────────────────── */}
      {mode === 'upload' && (
        <div className="fields">
          <label>
            English source (.txt or .docx)
            <input
              type="file"
              accept=".txt,.docx"
              onChange={read(setSource)}
            />
          </label>
          <p className="upload-help">
            Upload one authoritative English release. FACTSHIELD generates the
            Hindi and Marathi texts, lets you review them, then runs QC across
            all three versions.
          </p>
          <InlineError message={error} onDismiss={() => setError('')} />
        </div>
      )}

      {translationsReady && (
        <div className="translation-review">
          <div className="translation-header">
            <div>
              <i>TRANSLATION REVIEW</i>
              <h2>Hindi and Marathi texts ready for QC</h2>
            </div>
            <div className="translation-downloads">
              <button onClick={() => save('Hindi_Report.txt', hindi)}>Download Hindi</button>
              <button onClick={() => save('Marathi_Report.txt', marathi)}>Download Marathi</button>
            </div>
          </div>
          <div className="translation-grid">
            <label>Hindi<textarea value={hindi} onChange={(e) => setHindi(e.target.value)} /></label>
            <label>Marathi<textarea value={marathi} onChange={(e) => setMarathi(e.target.value)} /></label>
          </div>
        </div>
      )}

      {/* Show error above CTA only if none of the mode panels is showing it
          (edge case: error set while switching mode) */}
      {error && mode !== 'sample' && mode !== 'paste' && mode !== 'upload' && (
        <InlineError message={error} onDismiss={() => setError('')} />
      )}

      {!translationsReady && (mode === 'sample' || mode === 'upload' || (mode === 'paste' && auto)) && (
        <button className="primary cta" disabled={busy} onClick={generateTranslations}>
          {busy ? 'Generating translations…' : '🌐 Generate Hindi & Marathi texts'}
        </button>
      )}
      {translationsReady && (
        <button className="primary cta" disabled={busy} onClick={run}>
          {busy ? 'Running QC check…' : '🛡️ Run QC check on these 3 texts'}
        </button>
      )}
    </section>
  )
}

/* ── Dashboard ──────────────────────────────────────────────────────────────── */
function Dashboard({ data }) {
  if (!data)
    return (
      <Empty
        title="No analysis yet"
        text="Establish a multilingual baseline from Upload & Analyse."
      />
    )
  const { result, facts } = data
  return (
    <section className="page">
      <i>QC DASHBOARD</i>
      <div className="title">
        <h1>Release decision</h1>
        <b className={`pill ${result.overall_status}`}>
          {result.overall_status}
        </b>
      </div>
      <div className="score">
        <strong>{result.qc_score}</strong>
        <span>/100 integrity score</span>
        <p>
          {result.overall_status === 'PASS'
            ? 'Every checked fact is consistent.'
            : 'Review the detected findings before publication.'}
        </p>
      </div>
      <Metrics
        items={[
          ['Facts checked', result.total_facts_checked],
          ['Matches', result.total_matches],
          ['Mismatches', result.total_mismatches],
          ['Missing', result.total_missing],
          ['Review', result.total_review],
        ]}
      />
      <h2>Language status</h2>
      <div className="tiles">
        {Object.entries(result.lang_status).map(([k, v]) => (
          <div className="card" key={k}>
            <span>{k}</span>
            <b className={`pill ${v}`}>{v}</b>
          </div>
        ))}
      </div>
      <h2>Protected facts</h2>
      <div className="facts">
        {facts.map((f) => (
          <div key={f.fact_id}>
            <small>
              {f.fact_id} · {f.type}
            </small>
            <b>{f.canonical_value}</b>
            <em>{f.criticality}</em>
          </div>
        ))}
      </div>
    </section>
  )
}

const Metrics = ({ items }) => (
  <div className="metrics">
    {items.map(([a, b]) => (
      <div className="metric" key={a}>
        <span>{a}</span>
        <strong>{b}</strong>
      </div>
    ))}
  </div>
)

/* ── Findings ───────────────────────────────────────────────────────────────── */
function Findings({ data }) {
  if (!data)
    return (
      <Empty
        title="No findings yet"
        text="Run an analysis to view fact-level evidence."
      />
    )
  const r = data.result
  return (
    <section className="page">
      <i>FACT-LEVEL EVIDENCE</i>
      <h1>Findings &amp; matrix</h1>
      {r.findings.length ? (
        <div className="findings">
          {r.findings.map((f) => (
            <article className={f.severity} key={f.id}>
              <b>{f.severity}</b>
              <span>
                {f.fact_type.toUpperCase()} · {f.language}
              </span>
              <p>
                <strong>Expected:</strong> {f.expected}{' '}
                <strong>Detected:</strong> {f.detected}
              </p>
              <small>
                {f.rule_name} — {f.recommendation}
              </small>
            </article>
          ))}
        </div>
      ) : (
        <p className="alert good">
          No findings — all checked facts are consistent.
        </p>
      )}
      <h2>Full consistency matrix</h2>
      <div className="table">
        <table>
          <thead>
            <tr>
              {[
                'Language',
                'Fact ID',
                'Type',
                'Expected',
                'Detected',
                'Status',
              ].map((x) => (
                <th key={x}>{x}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {r.matrix.map((row, i) => (
              <tr key={i}>
                {[
                  'Language',
                  'Fact ID',
                  'Type',
                  'Expected',
                  'Detected',
                  'Status',
                ].map((x) => (
                  <td key={x}>{row[x]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

/* ── Provenance ─────────────────────────────────────────────────────────────── */
function Provenance({ data }) {
  const [copy, setCopy] = useState('')
  const [result, setResult] = useState()
  const [error, setError] = useState('')

  if (!data)
    return (
      <Empty
        title="Fingerprint unavailable"
        text="Run an analysis first to establish the authoritative facts."
      />
    )

  const verify = async () => {
    try {
      setError('')
      setResult(
        await request('/api/provenance', {
          method: 'POST',
          body: JSON.stringify({
            facts: data.facts,
            circulating_text: copy,
          }),
        })
      )
    } catch (e) {
      setError(e.message)
    }
  }

  const v = result?.verification
  return (
    <section className="page provenance-page">
      <div className="provenance-hero">
        <div className="shield-mark">⌬</div>
        <div>
          <i>PROVENANCE VERIFICATION</i>
          <h1>Prove the release has not drifted.</h1>
          <p>
            FACTSHIELD fingerprints protected facts—not wording—so normal
            editorial changes do not trigger a false integrity alert.
          </p>
        </div>
      </div>
      <div className="provenance-grid">
        <div className="fingerprint-card">
          <div className="card-kicker">AUTHORITATIVE FACT SET</div>
          <strong>{data.facts.length}</strong><span> protected facts</span>
          <div className="fingerprint">
            <span>SHA-256 FACT FINGERPRINT</span>
            <code>{result?.fingerprint || 'Generated when you verify a copy'}</code>
          </div>
          <small>Names, dates, numbers, and locations are protected.</small>
        </div>
        <div className="provenance-process">
          <span>01&nbsp; Establish facts</span><b>→</b><span>02&nbsp; Check circulating copy</span><b>→</b><span>03&nbsp; Release verdict</span>
        </div>
      </div>
      <div className="copy-check-card">
        <div className="copy-check-heading"><div><i>CHECK A CIRCULATING VERSION</i><h2>Paste the English copy to verify</h2></div><span className="live-dot">Ready</span></div>
        <label>
          Circulating English copy
          <textarea
            value={copy}
            onChange={(e) => setCopy(e.target.value)}
            placeholder="Paste the later or circulating version…"
          />
        </label>
        {error && <p className="alert bad">{error}</p>}
        <button className="primary verify-button" disabled={!copy.trim()} onClick={verify}>
          ⌁ Verify fact fingerprint
        </button>
      </div>
      {v && (
        <div className={`verification-verdict ${v.status === 'VERIFIED' ? 'verified' : 'tampered'}`}>
          <div className="verdict-icon">{v.status === 'VERIFIED' ? '✓' : '!'}</div>
          <div className="verdict-copy"><i>{v.status === 'VERIFIED' ? 'VERIFICATION COMPLETE' : 'INTEGRITY ALERT'}</i><h2>{v.status === 'VERIFIED' ? 'Verified — every protected fact is retained.' : 'Factual drift detected — analyst review required.'}</h2><p>{v.status === 'VERIFIED' ? 'The circulating copy matches the authoritative fact set.' : 'The copy differs from the established authoritative facts.'}</p></div>
        </div>
      )}
      {v && v.status !== 'VERIFIED' && (
        <div className="drift-results">
          <div className="drift-heading"><i>DRIFT DETAIL</i><h2>What changed?</h2></div>
          <div className="drift-grid">
            <div className="drift-card removed">
              <div><span>−</span><h3>Missing from copy</h3></div>
              {v.missing_facts.length ? (
                v.missing_facts.map((x, i) => (
                  <p key={i}><small>{x.type}</small>{x.value}</p>
                ))
              ) : (
                <p>None</p>
              )}
            </div>
            <div className="drift-card added">
              <div><span>+</span><h3>Added to copy</h3></div>
              {v.added_facts.length ? (
                v.added_facts.map((x, i) => (
                  <p key={i}><small>{x.type}</small>{x.value}</p>
                ))
              ) : (
                <p>None</p>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

/* ── Benchmark ──────────────────────────────────────────────────────────────── */
function Benchmark() {
  const [release, setRelease] = useState('release_001')
  const [data, setData] = useState()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const run = async () => {
    setBusy(true)
    try {
      setData(
        await request(`/api/benchmark/${release}`, { method: 'POST' })
      )
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const m = data?.metrics
  return (
    <section className="page">
      <i>ENGINE EVALUATION</i>
      <h1>Seeded-error benchmark</h1>
      <p className="lead">
        Inject 40 known errors and measure how many the unchanged QC engine
        catches.
      </p>
      <div className="inline">
        <select value={release} onChange={(e) => setRelease(e.target.value)}>
          {[1, 2, 3, 4, 5].map((n) => (
            <option key={n}>release_00{n}</option>
          ))}
        </select>
        <button className="primary" onClick={run}>
          {busy ? 'Benchmarking…' : 'Run benchmark'}
        </button>
      </div>
      {error && <p className="alert bad">{error}</p>}
      {m && (
        <>
          <Metrics
            items={[
              ['Catch rate', `${m.catch_rate}%`],
              ['Caught', m.caught],
              ['Missed', m.missed],
              ['Precision', `${m.precision}%`],
              ['F1 score', `${m.f1}%`],
            ]}
          />
          <h2>By category</h2>
          <div className="tiles">
            {Object.entries(m.by_category).map(([k, v]) => (
              <div className="card" key={k}>
                <span>{k}</span>
                <b>{v.catch_rate}%</b>
                <small>
                  {v.caught}/{v.total} caught
                </small>
              </div>
            ))}
          </div>
          <button
            onClick={() =>
              save(
                `benchmark_${release}.json`,
                JSON.stringify(data, null, 2),
                'application/json'
              )
            }
          >
            Download JSON
          </button>
        </>
      )}
    </section>
  )
}

/* ── Verified Social Post Studio ──────────────────────────────────────────── */
function SocialStudio({ data }) {
  const [theme, setTheme] = useState('professional')
  const [posts, setPosts] = useState()
  const [active, setActive] = useState('linkedin')
  const [draft, setDraft] = useState('')
  const [check, setCheck] = useState()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (!data) return <Empty title="No verified release yet" text="Run QC first; social copy is generated only from a verified fact set." />
  const qcScore = data.result?.qc_score ?? 0
  const eligible = qcScore > 80
  const generate = async () => {
    setBusy(true); setError(''); setCheck(undefined)
    try {
      const made = await request('/api/social-posts', { method: 'POST', body: JSON.stringify({ facts: data.facts, qc_status: data.result.overall_status, qc_score: qcScore, theme, source_text: data.versions?.English || '' }) })
      setPosts(made); setActive('linkedin'); setDraft(made.linkedin)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const switchPost = (platform) => { setActive(platform); setDraft(posts[platform]); setCheck(undefined) }
  const verify = async () => {
    setBusy(true); setError('')
    try { setCheck(await request('/api/social-posts/verify', { method: 'POST', body: JSON.stringify({ facts: data.facts, post_text: draft }) })) }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  return <section className="page social-page">
    <div className="social-hero"><div><i>VERIFIED SOCIAL POST STUDIO</i><h1>Turn a verified release into a trusted post.</h1><p>Captions are built from your QC-approved facts. Tone, format and hashtags can be optimized—but facts remain protected.</p></div><div className={`social-gate ${eligible ? 'open' : 'closed'}`}><span>{eligible ? '✓' : '!'}</span><div><small>QC GATE</small><b>{eligible ? `Score ${qcScore}/100 — content unlocked` : `Score ${qcScore}/100 — need above 80`}</b></div></div></div>
    {!eligible ? <div className="social-lock"><h2>QC score too low for social posts</h2><p>A QC score above 80 is required to generate social content. Current score: <b>{qcScore}/100</b>. Resolve flagged issues to improve the score.</p></div> : <>
      <div className="social-config"><div><i>CONTENT SETTINGS</i><h2>Choose a publishing tone</h2></div><select value={theme} onChange={(e) => setTheme(e.target.value)}><option value="professional">Professional / leadership</option><option value="community">Community engagement</option></select><button className="primary" disabled={busy} onClick={generate}>{busy ? 'Creating drafts…' : 'Create verified drafts'}</button></div>
      {error && <p className="alert bad">{error}</p>}
      {posts && <div className="social-workspace"><div className="platform-tabs"><button className={active === 'linkedin' ? 'chosen' : ''} onClick={() => switchPost('linkedin')}>in&nbsp; LinkedIn</button><button className={active === 'instagram' ? 'chosen' : ''} onClick={() => switchPost('instagram')}>◎&nbsp; Instagram</button></div><div className="post-editor"><div className="post-editor-header"><div><i>{active.toUpperCase()} DRAFT</i><h2>Review before publishing</h2></div><button onClick={() => save(`${active}_verified_draft.txt`, draft)}>Download draft</button></div><textarea value={draft} onChange={(e) => { setDraft(e.target.value); setCheck(undefined) }} /><div className="post-actions"><span>{draft.length} characters</span><button className="primary" disabled={busy} onClick={verify}>{busy ? 'Checking…' : 'Verify caption facts'}</button></div></div>
      {check && <div className={`caption-check ${check.status === 'SAFE' ? 'safe' : 'review'}`}><div className="caption-check-icon">{check.status === 'SAFE' ? '✓' : '!'}</div><div><i>{check.status === 'SAFE' ? 'SAFE TO EXPORT' : 'REVIEW REQUIRED'}</i><h2>{check.status === 'SAFE' ? 'No unverified facts were introduced.' : 'This edit introduced facts outside the QC baseline.'}</h2>{check.unexpected_facts.length > 0 && <p><b>Unexpected:</b> {check.unexpected_facts.join(', ')}</p>}<small>{check.verified_facts_used.length} verified facts detected in this caption.</small></div></div>}
      <div className="hashtag-bank"><i>APPROVED HASHTAGS</i><div>{posts.hashtags.map((tag) => <span key={tag}>{tag}</span>)}</div></div></div>}
    </>}
  </section>
}

/* ── Exports ────────────────────────────────────────────────────────────────── */
function Exports({ data }) {
  if (!data)
    return (
      <Empty
        title="Nothing to export"
        text="Run an analysis to create reports."
      />
    )
  const { versions, result } = data
  const report = {
    overall_status: result.overall_status,
    qc_score: result.qc_score,
    findings: result.findings,
    matrix: result.matrix,
  }
  return (
    <section className="page">
      <i>EXPORTS</i>
      <h1>Download review artifacts</h1>
      <div className="exports">
        <button onClick={() => save('English_Report.txt', versions.English)}>
          English source
        </button>
        <button onClick={() => save('Hindi_Report.txt', versions.Hindi)}>
          Hindi translation
        </button>
        <button onClick={() => save('Marathi_Report.txt', versions.Marathi)}>
          Marathi translation
        </button>
        <button
          className="primary"
          onClick={() =>
            save(
              'QC_Report.json',
              JSON.stringify(report, null, 2),
              'application/json'
            )
          }
        >
          QC report (JSON)
        </button>
      </div>
    </section>
  )
}

/* ── App shell ──────────────────────────────────────────────────────────────── */
function App() {
  const [page, setPage] = useState('analyse')
  const [data, setData] = useState()

  const views = {
    analyse: [
      '📤 Upload & Analyse',
      <Analyse
        done={(x) => {
          setData(x)
          setPage('dashboard')
        }}
      />,
    ],
    dashboard: ['📊 QC Dashboard', <Dashboard data={data} />],
    findings: ['🔍 Findings', <Findings data={data} />],
    provenance: ['🔐 Provenance', <Provenance data={data} />],
    social: ['✦ Social Studio', <SocialStudio data={data} />],
    benchmark: ['🧪 Benchmark', <Benchmark />],
    exports: ['📥 Exports', <Exports data={data} />],
  }

  return (
    <div className="shell">
      <aside>
        <header>
          ◈ <b>FACTSHIELD</b>
          <small>FACT INTEGRITY SYSTEM</small>
        </header>
        <nav>
          {Object.entries(views).map(([k, [label]]) => (
            <button
              className={page === k ? 'selected' : ''}
              onClick={() => setPage(k)}
              key={k}
            >
              {label}
            </button>
          ))}
        </nav>
        <footer>
          <small>v2.0 — Rule-based engine</small>
        </footer>
      </aside>
      <main>{views[page][1]}</main>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
