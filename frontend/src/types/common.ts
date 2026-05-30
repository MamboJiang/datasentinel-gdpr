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
  referenceUrl?: string | null
  sampleFamilies?: string[]
}
