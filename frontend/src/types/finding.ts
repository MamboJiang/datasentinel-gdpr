export type Owner = {
  userId: string
  displayName: string
  email?: string | null
  assignmentType: string
  assignmentReason?: string
  assignmentSource?: string
}

export type Signal = {
  type: string
  detector: string
  confidence: number
  snippet: string
  page?: number | null
  evidenceAnchor?: SignalEvidenceAnchor
}

export type SignalEvidenceAnchor = {
  anchorId: string
  format: string
  label: string
  redactedText: string
  selector: {
    type: string
    start?: number
    end?: number
    sourceStart?: number
    sourceEnd?: number
    page?: number
    row?: number
    column?: number
    columnLabel?: string
    sheetName?: string
    path?: string
    partName?: string
    paragraphIndex?: number
    slideNumber?: number
    shapeIndex?: number
    tagName?: string
    nodeIndex?: number
    recordIndex?: number
    lineNumber?: number
    fieldIndex?: number
    elementIndex?: number
    attributeIndex?: number
    blockLabel?: string
    frameIndex?: number
    pageRegion?: {
      x?: number
      y?: number
      width?: number
      height?: number
      pageWidth?: number
      pageHeight?: number
      unit?: string
      origin?: string
      confidence?: string
      ocrConfidence?: number
      [key: string]: unknown
    }
    [key: string]: unknown
  }
  fallback?: {
    label?: string
    redactedText?: string
    [key: string]: unknown
  }
  rawContentExposed?: boolean
  [key: string]: unknown
}

export type SourceReviewPreview = {
  sourcePreviewId: string
  sourceName: string
  fileFormat: string
  extractionMethod?: string
  recognitionDifficulty?: string
  redactionMode: string
  rawContentExposed: boolean
  pageImagesExposed: boolean
  anchors?: {
    anchorId: string
    label: string
    format: string
    redactedText: string
    fallbackLabel?: string
    selector: SignalEvidenceAnchor['selector']
    contextWindow?: SourceReviewContextWindow
    confidence?: number
    rawContentExposed?: boolean
  }[]
  contextWindows?: SourceReviewContextWindow[]
  pages?: {
    page: number
    label: string
    unit?: string
    origin?: string
    coordinateSystem?: string
    width?: number
    height?: number
    pageImageExposed?: boolean
    regions?: {
      anchorId: string
      label: string
      redactedText: string
      region: NonNullable<SignalEvidenceAnchor['selector']['pageRegion']>
      rawContentExposed?: boolean
    }[]
  }[]
  textRanges?: unknown[]
  tableCells?: unknown[]
  structureBlocks?: unknown[]
  warnings?: string[]
}

export type SourceReviewContextWindow = {
  anchorId: string
  redactedContext: string
  contextStart?: number
  contextEnd?: number
  highlightStart?: number
  highlightEnd?: number
  redactionMode?: string
  rawContentExposed: boolean
}

export type AuditEvidenceReference = {
  type: string
  id: string
  label?: string
}

export type AuditEvent = {
  auditEventId: string
  scanId?: string | null
  findingId?: string | null
  eventType: string
  actorId: string
  actorType?: 'human' | 'system'
  occurredAt: string
  recordedAt?: string
  auditRecordVersion?: string
  objectType?: string
  objectId?: string
  action?: string
  outcome?: string
  stage?: string
  sourceId?: string
  previousState?: string | null
  resultingState?: string | null
  summary?: string
  evidenceReferences?: AuditEvidenceReference[]
  decision?: ReviewDecision
  reason?: string
  resultingStatus?: string
  targetId?: string
  targetLabel?: string
  retentionUntil?: string | null
  deletionExecuted?: boolean
  policyPackVersion?: string
  permissionBoundaryFingerprint?: string
  reviewSupportRulesFingerprint?: string
  idempotencyKey?: string
  rawContentExposed?: boolean
  legalConclusionProvided?: boolean
}

export type FindingSummary = {
  findingId: string
  scanId?: string
  fileName: string
  sourcePath?: string
  riskLevel: string
  riskScore: number
  contextCategory?: string
  personalDataTypes?: string[]
  retentionStatus?: string
  recommendedAction?: string
  evidenceSignalCount?: number
  policyPackVersion?: string
  status: string
  owner?: Owner | null
}

export type Finding = FindingSummary & {
  file?: {
    sourceName?: string
    sourceType?: string
    lastModifiedAt?: string
    sizeBytes?: number
  }
  signals?: Signal[]
  sourceReviewPreview?: SourceReviewPreview
  riskExplanation?: string
  policyContext?: {
    policyPackId?: string
    policyPackVersion?: string
    policyConclusion?: string
  }
  availableActions?: string[]
  deniedActions?: DeniedAction[]
  auditTimeline?: AuditEvent[]
}

export type ReviewDecision =
  | 'delete_candidate'
  | 'keep_with_reason'
  | 'correct_false_positive'
  | 'reassign_owner'
  | 'escalate'

export type ReviewInput = {
  findingId: string
  decision: ReviewDecision
  reason: string
  actorId: string
  reassignToUserId?: string
  nextAction?: string
  retentionUntil?: string | null
  checklistItemIds?: string[]
  idempotencyKey?: string
}

export type ReviewRecord = {
  reviewId: string
  findingId: string
  decision: ReviewDecision
  reason: string
  actorId: string
  createdAt: string
  resultingStatus: string
  auditEventId: string
  targetId?: string
  targetLabel?: string
  retentionUntil?: string | null
  deletionExecuted: boolean
  policyPackVersion?: string
  permissionBoundaryFingerprint?: string
  reviewSupportRulesFingerprint?: string
  idempotencyKey?: string
}

export type DeniedAction = {
  action: string
  reason: string
}

export type PermissionBoundary = {
  actorId: string
  roles: string[]
  allowedActions: string[]
  deniedActions: DeniedAction[]
  visibleScopes: string[]
  boundaryFingerprint?: string
  evaluatedAt?: string
}

export type ReviewSupport = {
  findingId: string
  actorId: string
  policyPackVersion: string
  plainLanguageSummary?: string
  availableDecisions: {
    decision: ReviewDecision
    requiresReason?: boolean
    label?: string
  }[]
  checklist: {
    decision?: ReviewDecision
    itemId: string
    label: string
    required?: boolean
  }[]
  transferOptions?: {
    userId: string
    displayName: string
    reason?: string
  }[]
  escalationOptions?: {
    queueId: string
    label: string
  }[]
  permissionBoundary?: PermissionBoundary
}
