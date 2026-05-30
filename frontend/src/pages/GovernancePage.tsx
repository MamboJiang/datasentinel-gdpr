import { BadgeCheck, Building2, CircleSlash2, FileSliders, LockKeyhole, Network, ShieldCheck } from 'lucide-react'
import { useData } from '../data/useData'
import { formatDate, humanize } from '../components/formatters'
import { PageHeader, SectionHeader, StatusBadge } from '../components/ui'

export function GovernancePage() {
  const { governanceConfig, permissionBoundary } = useData()
  const { activePolicyPack, organizationModel, changeControls, sourceAdapters } = governanceConfig

  return (
    <>
      <PageHeader
        eyebrow="Adaptive controls"
        title="Governance settings"
      />

      <section className="governance-hero">
        <div className="governance-hero-icon"><ShieldCheck aria-hidden="true" size={23} /></div>
        <div>
          <span>Active policy pack</span>
          <h2>{activePolicyPack.policyPackId}</h2>
          <p>Version {activePolicyPack.version} · effective {formatDate(activePolicyPack.effectiveFrom)}</p>
        </div>
        <StatusBadge value={activePolicyPack.status} />
      </section>

      <div className="dashboard-grid governance-grid">
        <section className="panel">
          <SectionHeader title="Policy guidance" />
          <dl className="definition-list">
            <div><dt>Jurisdictions</dt><dd>{(activePolicyPack.jurisdictionTags ?? []).join(', ') || 'Not available'}</dd></div>
            <div><dt>Evidence requirements</dt><dd>{activePolicyPack.evidenceRequirements?.length ?? 0}</dd></div>
            <div><dt>Review decisions</dt><dd>{activePolicyPack.reviewDecisions.length}</dd></div>
            <div><dt>Escalation paths</dt><dd>{activePolicyPack.escalationPaths?.length ?? 0}</dd></div>
          </dl>
          <div className="guidance-list">
            {(activePolicyPack.retentionRules ?? []).map((rule) => (
              <article key={rule.ruleId}>
                <FileSliders aria-hidden="true" size={17} />
                <div>
                  <strong>{rule.documentCategory ? humanize(rule.documentCategory) : 'Retention rule'}</strong>
                  <p>{rule.guidance}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <SectionHeader title="Organization routing" />
          <dl className="definition-list">
            <div><dt>Model</dt><dd>{organizationModel.organizationModelId}</dd></div>
            <div><dt>Version</dt><dd>{organizationModel.version}</dd></div>
            <div><dt>Owner resolution</dt><dd>{humanize(organizationModel.ownerResolutionStrategy)}</dd></div>
          </dl>
          <div className="guidance-list">
            {(organizationModel.orgUnits ?? []).map((unit) => (
              <article key={unit.orgUnitId}>
                <Building2 aria-hidden="true" size={17} />
                <div><strong>{unit.displayName}</strong><p>Master of Data: {unit.masterOfDataUserId}</p></div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <div className="dashboard-grid governance-grid">
        <section className="panel">
          <SectionHeader title="Your permission boundary" />
          <div className="permission-columns">
            <div>
              <h3><BadgeCheck aria-hidden="true" size={16} /> Allowed actions</h3>
              {(permissionBoundary.allowedActions ?? []).map((action) => <span className="permission-chip permission-allowed" key={action}>{humanize(action)}</span>)}
            </div>
            <div>
              <h3><CircleSlash2 aria-hidden="true" size={16} /> Denied actions</h3>
              {(permissionBoundary.deniedActions ?? []).map((action) => <article className="denied-action" key={action.action}><strong>{humanize(action.action)}</strong><p>{action.reason}</p></article>)}
            </div>
          </div>
          <div className="visible-scopes">
            <LockKeyhole aria-hidden="true" size={15} />
            <span>Visible scopes: {permissionBoundary.visibleScopes.map(humanize).join(', ')}</span>
          </div>
        </section>

        <section className="panel">
          <SectionHeader title="Source adapters" />
          <div className="adapter-list">
            {sourceAdapters.map((adapter) => (
              <article key={adapter.sourceType}>
                <Network aria-hidden="true" size={17} />
                <div><strong>{adapter.label ?? humanize(adapter.sourceType)}</strong><span>{adapter.sourceType}</span></div>
                <StatusBadge value={adapter.status} />
              </article>
            ))}
          </div>
          <div className="change-controls">
            <strong>Change controls</strong>
            <p>Policy preview required: {changeControls?.policyChangesRequirePreview ? 'Yes' : 'No'}</p>
            <p>Organization changes audited: {changeControls?.orgChangesRequireAuditEvent ? 'Yes' : 'No'}</p>
            <p>Real deletion allowed: {changeControls?.realDeletionAllowed ? 'Yes' : 'No'}</p>
          </div>
        </section>
      </div>
    </>
  )
}
