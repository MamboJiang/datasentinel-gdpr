export type Meta = {
  contractVersion: string
  generatedAt: string
  traceId: string
  partial: boolean
  warnings: string[]
}

export type Source = {
  sourceId: string
  name: string
  sourceType: string
  status: string
  rootLabel?: string | null
  masterOfDataUserId?: string | null
  assignedOwnerUserId?: string | null
  assignedOwner?: {
    userId: string
    displayName: string
    email?: string | null
    assignmentType?: string
    assignmentReason?: string
    assignmentSource?: string
  } | null
  fallbackOwner?: {
    userId: string
    displayName: string
    email?: string | null
    assignmentType?: string
    assignmentReason?: string
    assignmentSource?: string
  } | null
  referenceUrl?: string | null
  sampleFamilies?: string[]
  config?: Record<string, unknown>
}
