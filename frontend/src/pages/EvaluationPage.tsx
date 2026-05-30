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
import { useI18n } from '../i18n'

function percentage(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—'
}

export function EvaluationPage() {
  const { t } = useI18n()
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
        <MetricCard icon={TrendingDown} label="Risk progress" value={percentage(riskReduction?.riskReductionRate)} helper={t('{{count}} high-risk remaining', { count: riskReduction?.remainingHighRiskFindings ?? '—' })} tone="amber" />
        <MetricCard icon={Binary} label="False negatives" value={(matrix?.falseNegatives ?? '—').toString()} helper={t('{{count}} false positive', { count: matrix?.falsePositives ?? '—' })} tone="red" />
        <MetricCard icon={Timer} label="Throughput" value={t('{{rate}} files/s', { rate: evaluation.throughputFilesPerSecond ?? '—' })} />
        <MetricCard icon={WalletCards} label="Paid service cost" value={`$${intensity.estimatedCostUsd ?? '—'}`} tone="green" />
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <SectionHeader title="Resource intensity" />
          <div className="resource-grid">
            <div><MemoryStick aria-hidden="true" size={18} /><span>{t('Peak memory')}</span><strong>{intensity.peakMemoryMb ?? '—'} MB</strong></div>
            <div><Cpu aria-hidden="true" size={18} /><span>{t('CPU time')}</span><strong>{intensity.cpuSeconds ?? '—'} {t('seconds')}</strong></div>
            <div><ShieldCheck aria-hidden="true" size={18} /><span>{t('Paid services')}</span><strong>{intensity.paidServiceUsed ? t('Used') : t('Not used')}</strong></div>
            <div><WalletCards aria-hidden="true" size={18} /><span>{t('Cost per 1k files')}</span><strong>${intensity.estimatedCostPerThousandFilesUsd ?? '—'}</strong></div>
          </div>
        </section>

        <section className="panel">
          <SectionHeader title="Reproducibility record" />
          <dl className="definition-list hash-list">
            <div><dt>{t('Evaluation run')}</dt><dd>{evaluation.evaluationRunId ?? t('Not available')}</dd></div>
            <div><dt>{t('Scanner version')}</dt><dd>{evaluation.scannerVersion ?? t('Not available')}</dd></div>
            <div><dt>{t('Dataset hash')}</dt><dd>{evaluation.datasetHash ?? t('Not available')}</dd></div>
            <div><dt>{t('Rules hash')}</dt><dd>{evaluation.detectorRulesHash ?? t('Not available')}</dd></div>
            <div><dt>{t('Admin metrics hash')}</dt><dd>{evaluation.adminMetricsRulesHash ?? t('Not available')}</dd></div>
            <div><dt>{t('Evaluation hash')}</dt><dd>{evaluation.evaluationRulesHash ?? t('Not available')}</dd></div>
            <div><dt>{t('Config hash')}</dt><dd>{evaluation.configHash ?? t('Not available')}</dd></div>
          </dl>
        </section>
      </div>

      <div className="dashboard-grid lower-grid">
        <section className="panel">
          <SectionHeader title="Quality basis" />
          <div className="resource-grid evaluation-basis-grid">
            <div><span>{t('Evaluated files')}</span><strong>{matrix?.evaluatedFiles ?? '—'}</strong></div>
            <div><span>{t('Actual positives')}</span><strong>{matrix?.actualPositiveFiles ?? '—'}</strong></div>
            <div><span>{t('Predicted positives')}</span><strong>{matrix?.predictedPositiveFiles ?? '—'}</strong></div>
            <div><span>{t('True positives')}</span><strong>{matrix?.truePositives ?? '—'}</strong></div>
            <div><span>{t('True negatives')}</span><strong>{matrix?.trueNegatives ?? '—'}</strong></div>
            <div><span>{t('Review throughput')}</span><strong>{quality?.review.reviewThroughputPerDay ?? '—'} / {t('day')}</strong></div>
          </div>
        </section>

        <section className="panel">
          <SectionHeader title="Safety boundaries" />
          <dl className="definition-list">
            <div><dt>{t('Raw content exposed')}</dt><dd>{quality?.safetyBoundaries.rawContentExposed ? t('Yes') : t('No')}</dd></div>
            <div><dt>{t('Legal conclusion provided')}</dt><dd>{quality?.safetyBoundaries.legalConclusionProvided ? t('Yes') : t('No')}</dd></div>
            <div><dt>{t('Deletion executed')}</dt><dd>{quality?.safetyBoundaries.deletionExecuted ? t('Yes') : t('No')}</dd></div>
            <div><dt>{t('Model calls')}</dt><dd>{quality?.safetyBoundaries.modelCalls ?? 0}</dd></div>
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
                  <span>{scenario.contextCategory ? humanize(scenario.contextCategory) : t('Unknown context')}</span>
                </div>
                <dl>
                  <div><dt>{t('Precision')}</dt><dd>{percentage(scenario.precision)}</dd></div>
                  <div><dt>{t('Recall')}</dt><dd>{percentage(scenario.recall)}</dd></div>
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
