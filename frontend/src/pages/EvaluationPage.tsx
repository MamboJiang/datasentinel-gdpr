import { Cpu, DatabaseZap, Gauge, MemoryStick, Repeat2, Scale, Timer, WalletCards } from 'lucide-react'
import { useData } from '../data/useData'
import { MetricCard, PageHeader, SectionHeader } from '../components/ui'

function percentage(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—'
}

export function EvaluationPage() {
  const { evaluation } = useData()
  const intensity = evaluation.resourceIntensity ?? {}

  return (
    <>
      <PageHeader
        eyebrow="Measurable discovery"
        title="Evaluation"
      />

      <section className="metrics-grid evaluation-grid" aria-label="Evaluation metrics">
        <MetricCard icon={Scale} label="Precision" value={percentage(evaluation.precision)} tone="green" />
        <MetricCard icon={Gauge} label="Recall" value={percentage(evaluation.recall)} />
        <MetricCard icon={DatabaseZap} label="F1 score" value={percentage(evaluation.f1)} tone="green" />
        <MetricCard icon={Repeat2} label="Reproducibility" value={percentage(evaluation.reproducibility)} tone="green" />
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <SectionHeader title="Resource intensity" />
          <div className="resource-grid">
            <div><MemoryStick aria-hidden="true" size={18} /><span>Peak memory</span><strong>{intensity.peakMemoryMb ?? '—'} MB</strong></div>
            <div><Cpu aria-hidden="true" size={18} /><span>CPU time</span><strong>{intensity.cpuSeconds ?? '—'} seconds</strong></div>
            <div><Timer aria-hidden="true" size={18} /><span>Throughput</span><strong>{evaluation.throughputFilesPerSecond ?? '—'} files/s</strong></div>
            <div><WalletCards aria-hidden="true" size={18} /><span>Estimated cost</span><strong>${intensity.estimatedCostUsd ?? '—'}</strong></div>
          </div>
        </section>

        <section className="panel">
          <SectionHeader title="Reproducibility record" />
          <dl className="definition-list hash-list">
            <div><dt>Evaluation run</dt><dd>{evaluation.evaluationRunId ?? 'Not available'}</dd></div>
            <div><dt>Scanner version</dt><dd>{evaluation.scannerVersion ?? 'Not available'}</dd></div>
            <div><dt>Dataset hash</dt><dd>{evaluation.datasetHash ?? 'Not available'}</dd></div>
            <div><dt>Rules hash</dt><dd>{evaluation.detectorRulesHash ?? 'Not available'}</dd></div>
            <div><dt>Config hash</dt><dd>{evaluation.configHash ?? 'Not available'}</dd></div>
          </dl>
        </section>
      </div>
    </>
  )
}
