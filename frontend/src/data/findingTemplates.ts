import type { Owner, Signal } from '../types'

export type FindingTemplate = {
  category: string
  extension: string
  fileStem: string
  owner: Owner
  pathSegment: string
  signals: Signal[]
  title: string
}

export const findingTemplates: Record<string, FindingTemplate> = {
  expense_report: {
    category: 'expense_report',
    extension: 'xlsx',
    fileStem: 'expense_report',
    owner: {
      userId: 'user_lena',
      displayName: 'Lena Hoffmann',
      email: 'lena.hoffmann@example.com',
      assignmentType: 'direct_owner',
      assignmentReason: 'Expense workflow metadata matched the finance operations owner.',
      assignmentSource: 'file_owner_metadata',
    },
    pathSegment: '/finance/shared/expenses',
    signals: [
      { type: 'employee_id', detector: 'employee_identifier_pattern', confidence: 0.92, snippet: 'Employee ID: [REDACTED_ID]', page: 1 },
      { type: 'reimbursement_data', detector: 'expense_table_detector', confidence: 0.86, snippet: 'Reimbursement row: [REDACTED_AMOUNT]', page: 1 },
    ],
    title: 'expense record',
  },
  it_access: {
    category: 'it_access',
    extension: 'pdf',
    fileStem: 'it_access_request',
    owner: {
      userId: 'user_markus',
      displayName: 'Markus Keller',
      email: 'markus.keller@example.com',
      assignmentType: 'direct_owner',
      assignmentReason: 'Access request metadata matched the IT Operations owner.',
      assignmentSource: 'file_owner_metadata',
    },
    pathSegment: '/it/access',
    signals: [
      { type: 'employee_id', detector: 'employee_identifier_pattern', confidence: 0.94, snippet: 'Requester ID: [REDACTED_ID]', page: 1 },
      { type: 'access_role', detector: 'access_role_dictionary', confidence: 0.88, snippet: 'Requested role: [REDACTED_ROLE]', page: 1 },
    ],
    title: 'access request',
  },
  incident_report: {
    category: 'incident_report',
    extension: 'docx',
    fileStem: 'incident_report',
    owner: {
      userId: 'user_sofia',
      displayName: 'Sofia Braun',
      email: 'sofia.braun@example.com',
      assignmentType: 'direct_owner',
      assignmentReason: 'Incident workflow metadata matched the support operations owner.',
      assignmentSource: 'file_owner_metadata',
    },
    pathSegment: '/operations/incidents',
    signals: [
      { type: 'email', detector: 'email_regex', confidence: 0.99, snippet: 'Reporter: [REDACTED_EMAIL]', page: 1 },
      { type: 'free_text_personal_data', detector: 'personal_context_phrase', confidence: 0.78, snippet: 'Incident notes: [REDACTED_PERSONAL_CONTEXT]', page: 2 },
    ],
    title: 'incident record',
  },
  supplier_onboarding: {
    category: 'supplier_onboarding',
    extension: 'pdf',
    fileStem: 'supplier_onboarding',
    owner: {
      userId: 'user_julia',
      displayName: 'Julia Weber',
      email: 'julia.weber@example.com',
      assignmentType: 'direct_owner',
      assignmentReason: 'Supplier workflow metadata matched the procurement owner.',
      assignmentSource: 'file_owner_metadata',
    },
    pathSegment: '/finance/shared/suppliers',
    signals: [
      { type: 'iban_like', detector: 'financial_identifier_pattern', confidence: 0.91, snippet: 'IBAN-like value: [REDACTED_FINANCIAL_ID]', page: 1 },
      { type: 'billing_address', detector: 'address_block_detector', confidence: 0.84, snippet: 'Billing address: [REDACTED_ADDRESS]', page: 1 },
      { type: 'signature', detector: 'signature_marker_detector', confidence: 0.8, snippet: 'Signature block: [REDACTED_SIGNATURE]', page: 2 },
    ],
    title: 'supplier onboarding record',
  },
  training_evaluation: {
    category: 'training_evaluation',
    extension: 'docx',
    fileStem: 'training_evaluation',
    owner: {
      userId: 'user_erik',
      displayName: 'Erik Vogel',
      email: 'erik.vogel@example.com',
      assignmentType: 'direct_owner',
      assignmentReason: 'Training workflow metadata matched the learning operations owner.',
      assignmentSource: 'file_owner_metadata',
    },
    pathSegment: '/hr/training',
    signals: [
      { type: 'email', detector: 'email_regex', confidence: 0.99, snippet: 'Participant: [REDACTED_EMAIL]', page: 1 },
      { type: 'feedback_comment', detector: 'feedback_context_detector', confidence: 0.74, snippet: 'Feedback: [REDACTED_COMMENT]', page: 1 },
    ],
    title: 'training evaluation',
  },
}

export const fallbackOwner: Owner = {
  userId: 'user_anna',
  displayName: 'Anna Schneider',
  email: 'anna.schneider@example.com',
  assignmentType: 'master_of_data',
  assignmentReason: 'Direct owner signal was unavailable; routed to source Master of Data.',
  assignmentSource: 'source_master_of_data',
}

export const escalationOwner: Owner = {
  userId: 'queue_dpo',
  displayName: 'DPO review queue',
  email: null,
  assignmentType: 'escalation_queue',
  assignmentReason: 'Policy guidance routed this finding to escalation before human review.',
  assignmentSource: 'policy_escalation_path',
}
