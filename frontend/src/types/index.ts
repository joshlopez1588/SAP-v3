export type UserRole = 'admin' | 'analyst' | 'reviewer' | 'auditor' | 'examiner';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Framework {
  id: string;
  name: string;
  description?: string | null;
  review_type: string;
  version_major: number;
  version_minor: number;
  version_patch: number;
  settings: Record<string, unknown>;
  checks: Array<Record<string, unknown>>;
  status: string;
  is_immutable: boolean;
  created_at: string;
}

export interface Application {
  id: string;
  name: string;
  description?: string | null;
  review_type: string;
  owner?: string | null;
  owner_email?: string | null;
  criticality: string;
  data_classification: string;
  review_frequency: string;
  next_review_date?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Review {
  id: string;
  name: string;
  application_id: string;
  framework_id: string;
  framework_version_label: string;
  period_start?: string | null;
  period_end?: string | null;
  due_date?: string | null;
  status: string;
  analysis_checksum?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Finding {
  id: string;
  review_id: string;
  check_id: string;
  check_name: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  explainability: string;
  ai_description?: string | null;
  ai_remediation?: string | null;
  ai_generated: boolean;
  ai_confidence?: number | null;
  disposition?: 'approved' | 'revoke' | 'abstain' | null;
  disposition_note?: string | null;
  status: string;
  record_count: number;
  affected_record_ids: string[];
  output_fields: string[];
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  review_id: string;
  filename: string;
  file_hash: string;
  file_size: number;
  file_format: string;
  template_id?: string | null;
  template_match_confidence?: number | null;
  document_role: string;
  uploaded_at: string;
}

export interface ReferenceDataset {
  id: string;
  name: string;
  data_type: string;
  source_system: string;
  record_count: number;
  uploaded_at: string;
  freshness_threshold_days: number;
  freshness_status: 'green' | 'amber' | 'red';
}

export interface AuditEntry {
  id: number;
  timestamp: string;
  actor_id?: string | null;
  actor_type: string;
  request_id?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  content_hash: string;
  previous_hash?: string | null;
  metadata: Record<string, unknown>;
}
