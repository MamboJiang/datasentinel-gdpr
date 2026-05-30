import {
  Binary,
  Cpu,
  DatabaseZap,
  Gauge,
  MemoryStick,
  Repeat2,
  Scale,
  ShieldCheck,
  Timer,
  TrendingDown,
  WalletCards,
} from 'lucide-react'
import { useData } from '../data/useData'
import { MetricCard, PageHeader, SectionHeader } from '../components/ui'
import { humanize } from '../components/formatters'

function percentage(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—'
}

export function EvaluationPage() {
  const { evaluation } = useData()
  const intensity = evaluation.resourceIntensity ?? {}
  const quality = evaluation.qualityBasis
  const matrix = quality?.confusionMatrix
  const riskReduction = quality?.riskReduction

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
        <MetricCard icon={TrendingDown} label="Risk progress" value={percentage(riskReduction?.riskReductionRate)} helper={`${riskReduction?.remainingHighRiskFindings ?? '—'} high-risk remaining`} tone="amber" />
        <MetricCard icon={Binary} label="False negatives" value={(matrix?.falseNegatives ?? '—').toString()} helper={`${matrix?.falsePositives ?? '—'} false positive`} tone="red" />
        <MetricCard icon={Timer} label="Throughput" value={`${evaluation.throughputFilesPerSecond ?? '—'} files/s`} />
        <MetricCard icon={WalletCards} label="Paid service cost" value={`$${intensity.estimatedCostUsd ?? '—'}`} tone="green" />
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <SectionHeader title="Resource intensity" />
          <div className="resource-grid">
            <div><MemoryStick aria-hidden="true" size={18} /><span>Peak memory</span><strong>{intensity.peakMemoryMb ?? '—'} MB</strong></div>
            <div><Cpu aria-hidden="true" size={18} /><span>CPU time</span><strong>{intensity.cpuSeconds ?? '—'} seconds</strong></div>
            <div><ShieldCheck aria-hidden="true" size={18} /><span>Paid services</span><strong>{intensity.paidServiceUsed ? 'Used' : 'Not used'}</strong></div>
            <div><WalletCards aria-hidden="true" size={18} /><span>Cost per 1k files</span><strong>${intensity.estimatedCostPerThousandFilesUsd ?? '—'}</strong></div>
          </div>
        </section>

        <section className="panel">
          <SectionHeader title="Reproducibility record" />
          <dl className="definition-list hash-list">
            <div><dt>Evaluation run</dt><dd>{evaluation.evaluationRunId ?? 'Not available'}</dd></div>
            <div><dt>Scanner version</dt><dd>{evaluation.scannerVersion ?? 'Not available'}</dd></div>
            <div><dt>Dataset hash</dt><dd>{evaluation.datasetHash ?? 'Not available'}</dd></div>
            <div><dt>Rules hash</dt><dd>{evaluation.detectorRulesHash ?? 'Not available'}</dd></div>
            <div><dt>Admin metrics hash</dt><dd>{evaluation.adminMetricsRulesHash ?? 'Not available'}</dd></div>
            <div><dt>Evaluation hash</dt><dd>{evaluation.evaluationRulesHash ?? 'Not available'}</dd></div>
            <div><dt>Config hash</dt><dd>{evaluation.configHash ?? 'Not available'}</dd></div>
          </dl>
        </section>
      </div>

      <div className="dashboard-grid lower-grid">
        <section className="panel">
          <SectionHeader title="Quality basis" />
          <div className="resource-grid evaluation-basis-grid">
            <div><span>Evaluated files</span><strong>{matrix?.evaluatedFiles ?? '—'}</strong></div>
            <div><span>Actual positives</span><strong>{matrix?.actualPositiveFiles ?? '—'}</strong></div>
            <div><span>Predicted positives</span><strong>{matrix?.predictedPositiveFiles ?? '—'}</strong></div>
            <div><span>True positives</span><strong>{matrix?.truePositives ?? '—'}</strong></div>
            <div><span>True negatives</span><strong>{matrix?.trueNegatives ?? '—'}</strong></div>
            <div><span>Review throughput</span><strong>{quality?.review.reviewThroughputPerDay ?? '—'} / day</strong></div>
          </div>
        </section>

        <section className="panel">
          <SectionHeader title="Safety boundaries" />
          <dl className="definition-list">
            <div><dt>Raw content exposed</dt><dd>{quality?.safetyBoundaries.rawContentExposed ? 'Yes' : 'No'}</dd></div>
            <div><dt>Legal conclusion provided</dt><dd>{quality?.safetyBoundaries.legalConclusionProvided ? 'Yes' : 'No'}</dd></div>
            <div><dt>Deletion executed</dt><dd>{quality?.safetyBoundaries.deletionExecuted ? 'Yes' : 'No'}</dd></div>
            <div><dt>Model calls</dt><dd>{quality?.safetyBoundaries.modelCalls ?? 0}</dd></div>
          </dl>
        </section>
      </div>

      {quality?.scenarioMetrics?.length ? (
        <section className="panel evaluation-scenario-panel">
          <SectionHeader title="Scenario quality" />
          <div className="scenario-list">
            {quality.scenarioMetrics.map((scenario) => (
              <div className="scenario-row" key={scenario.sourceFamily}>
                <div>
                  <strong>{humanize(scenario.sourceFamily)}</strong>
                  <span>{scenario.contextCategory ? humanize(scenario.contextCategory) : 'Unknown context'}</span>
                </div>
                <dl>
                  <div><dt>Precision</dt><dd>{percentage(scenario.precision)}</dd></div>
                  <div><dt>Recall</dt><dd>{percentage(scenario.recall)}</dd></div>
                  <div><dt>F1</dt><dd>{percentage(scenario.f1)}</dd></div>
                  <div><dt>FP/FN</dt><dd>{scenario.falsePositives}/{scenario.falseNegatives}</dd></div>
                  <div><dt>OCR</dt><dd>{scenario.ocrDeferredFiles ?? 0}</dd></div>
                </dl>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </>
  )
}
