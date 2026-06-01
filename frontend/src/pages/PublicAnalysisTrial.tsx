import { AlertCircle, ArrowRight, CheckCircle, FileSearch, Gauge, RotateCcw, Upload, Users } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { analyzePublicFile, loadPublicAnalysisCapacity, type PublicAnalysisCapacity, type PublicAnalysisProblem, type PublicAnalysisResult } from '../data/publicAnalysisApi'
import { isApiRequestError } from '../data/serverApi'

const SESSION_STORAGE_KEY = 'lawdit_public_analysis_session'
const DEFAULT_FILE_LIMIT_BYTES = 10 * 1024 * 1024
const CAPACITY_POLL_MS = 8000

type TrialState = 'idle' | 'selected' | 'analyzing' | 'completed' | 'error'

export function PublicAnalysisTrial() {
  const sessionId = useMemo(() => publicTrialSessionId(), [])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [capacity, setCapacity] = useState<PublicAnalysisCapacity | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<PublicAnalysisResult | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [trialState, setTrialState] = useState<TrialState>('idle')
  const fileLimit = capacity?.fileSizeLimitBytes ?? DEFAULT_FILE_LIMIT_BYTES
  const activeRatio = capacity && capacity.maxActive > 0 ? capacity.activeAnalyses / capacity.maxActive : 0
  const selectedFileTooLarge = Boolean(selectedFile && selectedFile.size > fileLimit)
  const canAnalyze = Boolean(selectedFile && !selectedFileTooLarge && trialState !== 'analyzing' && !capacity?.userHasActiveAnalysis)

  useEffect(() => {
    let cancelled = false

    async function refreshCapacity() {
      try {
        const nextCapacity = await loadPublicAnalysisCapacity(sessionId)
        if (!cancelled) {
          setCapacity(nextCapacity.data)
        }
      } catch {
        if (!cancelled) {
          setCapacity(null)
        }
      }
    }

    void refreshCapacity()
    const interval = window.setInterval(refreshCapacity, CAPACITY_POLL_MS)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [sessionId])

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setResult(null)
    setMessage(file && file.size > fileLimit ? `File is ${formatBytes(file.size)}. This website entry accepts one file up to ${formatBytes(fileLimit)}.` : null)
    setTrialState(file ? 'selected' : 'idle')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedFile || selectedFileTooLarge) {
      return
    }

    setTrialState('analyzing')
    setMessage(null)
    setResult(null)

    try {
      const analyzed = await analyzePublicFile(selectedFile, sessionId)
      setResult(analyzed.data)
      setCapacity(analyzed.data.capacity)
      setTrialState('completed')
    } catch (error) {
      if (isApiRequestError(error)) {
        const problem = error.problem as PublicAnalysisProblem
        setMessage(problem.detail ?? problem.title ?? error.message)
        if (problem.capacity) {
          setCapacity(problem.capacity)
        }
      } else {
        setMessage('File analysis is unavailable right now.')
      }
      setTrialState('error')
    }
  }

  function handleReset() {
    setSelectedFile(null)
    setResult(null)
    setMessage(null)
    setTrialState('idle')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <section className="landing-section landing-trial" id="try-analysis" tabIndex={-1}>
      <div className="landing-trial-copy landing-reveal">
        <h2>Analyze one file with lawdit.</h2>
        <p>
          Upload a file to see how lawdit extracts readable content, redacts sensitive signals, scores review priority, and explains the next accountable action. For source ownership, audit trails, and evaluation history, continue in the governed Workspace.
        </p>
        <div className="landing-trial-boundary">
          <strong>Website analysis boundary</strong>
          <span>This upload is processed for this response only. It does not create a Workspace source, finding, audit event, or deletion action.</span>
          <Link to="/dashboard">
            Continue to governed Workspace <ArrowRight aria-hidden="true" size={15} />
          </Link>
        </div>
        <div className="landing-trial-capacity" aria-label="Public analysis capacity">
          <div className="landing-trial-meter">
            <span style={{ inlineSize: `${Math.min(100, Math.max(0, activeRatio * 100))}%` }} />
          </div>
          <dl>
            <div>
              <dt><Gauge aria-hidden="true" size={16} /> In analysis</dt>
              <dd>{capacity ? `${capacity.activeAnalyses} / ${capacity.maxActive}` : 'Checking'}</dd>
            </div>
            <div>
              <dt><Users aria-hidden="true" size={16} /> Slots open</dt>
              <dd>{capacity ? capacity.availableSlots : '...'}</dd>
            </div>
            <div>
              <dt>Waiting</dt>
              <dd>{capacity ? capacity.waitingUsers : '...'}</dd>
            </div>
          </dl>
          {capacity?.userHasActiveAnalysis ? <p className="landing-trial-note">This browser session already has an active file analysis.</p> : null}
          {capacity?.userQueuePosition ? <p className="landing-trial-note">Your waiting position is {capacity.userQueuePosition}.</p> : null}
        </div>
      </div>

      <form className="landing-trial-tool landing-reveal" onSubmit={handleSubmit}>
        <div className="landing-trial-tool-head">
          <strong>One-file analysis entry</strong>
          <span>One file, 10 MB maximum. Results show redacted evidence and accountable next steps without creating a Workspace record.</span>
        </div>
        <input
          accept=".txt,.csv,.tsv,.json,.jsonl,.ndjson,.md,.log,.xml,.html,.htm,.rtf,.eml,.zip,.pdf,.docx,.xlsx,.pptx,.odt,.ods,.odp,.vtt,.srt,image/*"
          className="landing-trial-input"
          id="public-analysis-file"
          onChange={handleFileChange}
          ref={fileInputRef}
          type="file"
        />
        <label className={`landing-trial-drop ${selectedFileTooLarge ? 'landing-trial-drop-error' : ''}`} htmlFor="public-analysis-file">
          <Upload aria-hidden="true" size={22} />
          <span>
            <strong>{selectedFile ? selectedFile.name : 'Choose one file'}</strong>
            <small>{selectedFile ? formatBytes(selectedFile.size) : `Limit ${formatBytes(fileLimit)}`}</small>
          </span>
        </label>

        <div className="landing-trial-actions">
          <button className="landing-primary landing-trial-submit" disabled={!canAnalyze} type="submit">
            <span className="landing-primary-content">
              <FileSearch aria-hidden="true" size={17} />
              {trialState === 'analyzing' ? 'Analyzing' : 'Analyze file'}
            </span>
          </button>
          <button className="landing-secondary landing-trial-reset" onClick={handleReset} type="button">
            <RotateCcw aria-hidden="true" size={16} />
            Start over
          </button>
        </div>

        {message ? (
          <div className="landing-trial-alert" role="alert">
            <AlertCircle aria-hidden="true" size={18} />
            <span>{message}</span>
          </div>
        ) : null}

        {result ? <PublicAnalysisResultView result={result} /> : <PublicAnalysisEmptyState />}
      </form>
    </section>
  )
}

function PublicAnalysisResultView({ result }: { result: PublicAnalysisResult }) {
  const nextSteps = result.summary.nextSteps?.length ? result.summary.nextSteps : [result.summary.reviewRecommendation]
  const readiness = result.summary.workflowReadiness ?? []
  const boundaryNotes = mergeNotes(result.summary.boundaryNotes, result.governanceBoundaries)
  const plainSummary = result.summary.plainLanguageSummary

  return (
    <div className="landing-trial-result" aria-live="polite">
      <div className="landing-trial-result-head">
        <span>{result.summary.riskLevel} priority</span>
        <strong>{result.summary.detectedSignalCount} redacted signals</strong>
      </div>
      {plainSummary ? (
        <section className="landing-trial-human-summary" aria-label="Plain-language result summary">
          <strong>{plainSummary.headline}</strong>
          <p>{plainSummary.explanation}</p>
          <p>{plainSummary.gdprRelevance}</p>
          <p>{plainSummary.reviewFocus}</p>
        </section>
      ) : (
        <p>{result.summary.reviewRecommendation}</p>
      )}
      <dl className="landing-trial-file-summary" aria-label="Analyzed file handling">
        <div>
          <dt>Format</dt>
          <dd>{result.file.fileFormat}</dd>
        </div>
        <div>
          <dt>Extraction</dt>
          <dd>{labelize(result.file.extractionMethod)}</dd>
        </div>
        <div>
          <dt>Difficulty</dt>
          <dd>{labelize(result.file.recognitionDifficulty)}</dd>
        </div>
      </dl>
      {result.analysisStages?.length ? (
        <div className="landing-trial-stage-list" aria-label="Analysis stages">
          {result.analysisStages.map((stage) => (
            <article className="landing-trial-stage-row" key={stage.name}>
              <CheckCircle aria-hidden="true" size={16} />
              <div>
                <strong>{stage.name}</strong>
                <span>{stage.status ? labelize(stage.status) : 'Available'}</span>
                {stage.description ? <p>{stage.description}</p> : null}
              </div>
            </article>
          ))}
        </div>
      ) : null}
      <div className="landing-trial-type-list" aria-label="Detected signal categories">
        {result.summary.detectedTypes.length ? result.summary.detectedTypes.map((item) => (
          <span key={item.type}>{labelize(item.type)} x{item.count}</span>
        )) : <span>No deterministic signal match</span>}
      </div>
      <div className="landing-trial-evidence" aria-label="Redacted evidence">
        {result.evidence.length ? result.evidence.map((item) => (
          <div className="landing-trial-evidence-row" key={`${item.type}-${item.detector}-${item.locationLabel}`}>
            <span>{labelize(item.type)}</span>
            <strong>{item.snippet}</strong>
            <small>{item.locationLabel} · {Math.round(item.confidence * 100)}%</small>
          </div>
        )) : <p>No evidence snippet was returned by the deterministic detectors.</p>}
      </div>
      <InfoList title="Next accountable steps" items={nextSteps} />
      {readiness.length ? <InfoList title="Workspace handoff readiness" items={readiness} /> : null}
      <ul className="landing-trial-safety">
        <li>Workspace case created: no</li>
        <li>Raw content exposed: {yesNo(result.summary.rawContentExposed)}</li>
        <li>Legal conclusion: {yesNo(result.summary.legalConclusionProvided)}</li>
        <li>Deletion available: {yesNo(result.summary.deletionAvailable)}</li>
      </ul>
      {boundaryNotes.length ? <InfoList title="Analysis boundaries" items={boundaryNotes} /> : null}
      {result.warnings.length ? (
        <div className="landing-trial-warnings">
          {result.warnings.map((warning) => <p key={warning}>{warning}</p>)}
        </div>
      ) : null}
    </div>
  )
}

function PublicAnalysisEmptyState() {
  return (
    <div className="landing-trial-empty">
      <strong>Analysis result</strong>
      <p>Redacted signals, file handling, review priority, and Workspace handoff guidance appear here after analysis.</p>
    </div>
  )
}

function InfoList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="landing-trial-info-list">
      <strong>{title}</strong>
      <ul>
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  )
}

function publicTrialSessionId() {
  if (typeof window === 'undefined') {
    return 'server-rendered-public-trial'
  }

  const existing = window.localStorage.getItem(SESSION_STORAGE_KEY)
  if (existing) {
    return existing
  }

  const generated = window.crypto?.randomUUID?.() ?? `trial-${Date.now()}-${Math.random().toString(16).slice(2)}`
  window.localStorage.setItem(SESSION_STORAGE_KEY, generated)
  return generated
}

function formatBytes(bytes: number) {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(bytes % (1024 * 1024) === 0 ? 0 : 1)} MB`
  }
  if (bytes >= 1024) {
    return `${Math.round(bytes / 1024)} KB`
  }
  return `${bytes} B`
}

function labelize(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function yesNo(value: boolean) {
  return value ? 'yes' : 'no'
}

function mergeNotes(primary?: string[], secondary?: string[]) {
  const notes: string[] = []
  for (const note of [...(primary ?? []), ...(secondary ?? [])]) {
    if (!notes.includes(note)) {
      notes.push(note)
    }
  }
  return notes
}
