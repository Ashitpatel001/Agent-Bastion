export enum TenantTier {
  FREE = 'FREE',
  PRO = 'PRO',
  ENTERPRISE = 'ENTERPRISE',
}

export enum RiskLevel {
  SAFE = 'SAFE',
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

export enum ActionTaken {
  ALLOWED = 'ALLOWED',
  MONITOR = 'MONITOR',
  WARNED = 'WARNED',
  SANITIZED = 'SANITIZED',
  BLOCKED = 'BLOCKED',
  BLOCK_AND_ESCALATE = 'BLOCK_AND_ESCALATE',
  EXPLAINED = 'EXPLAINED',
}

export enum SessionStatus {
  QUEUED = 'QUEUED',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
}

export enum UserRole {
  OWNER = 'OWNER',
  ADMIN = 'ADMIN',
  SECURITY_ANALYST = 'SECURITY_ANALYST',
  DEVELOPER = 'DEVELOPER',
  VIEWER = 'VIEWER',
}

export interface Tenant {
  id: string;
  name: string;
  email: string;
  tier: TenantTier;
  is_active: boolean;
  api_key_prefix: string;
  max_concurrent_sessions: number;
  created_at: string;
}

export interface TenantCreateRequest {
  name: string;
  email: string;
}

export interface TenantCreateResponse {
  tenant: Tenant;
  raw_api_key: string;
  message?: string;
}

export interface Policy {
  id: string;
  tenant_id: string;
  is_active: boolean;
  blocked_domains: string[];
  blocked_input_patterns: string[];
  blocked_actions: string[];
  trusted_domains: string[];
  max_risk_tolerance: number;
  require_human_approval: boolean;
  created_at: string;
  updated_at: string;
}

export interface PolicyUpdateRequest {
  id?: string;
  blocked_domains?: string[];
  blocked_input_patterns?: string[];
  blocked_actions?: string[];
  trusted_domains?: string[];
  max_risk_tolerance?: number;
  require_human_approval?: boolean;
}

export interface AgentSession {
  id: string;
  tenant_id: string;
  status: SessionStatus;
  task_prompt: string;
  target_url: string | null;
  result_summary: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface AgentSessionCreateRequest {
  task_prompt: string;
  target_url?: string;
}

export interface AuditLog {
  id: string;
  tenant_id: string;
  session_id: string | null;
  event_type: string;
  url: string | null;
  details: string | null;
  risk_level: RiskLevel;
  risk_score: number;
  action_taken: ActionTaken;
  risk_breakdown: Record<string, unknown> | null;
  screenshot_path: string | null;
  xai_explanation: string | null;
  xai_pending: boolean;
  created_at: string;
}

export interface AuditLogListResponse {
  total: number;
  page: number;
  page_size: number;
  items: AuditLog[];
}

export type SecurityStats = Record<string, unknown>;

export interface HealthResponse {
  status: string;
  service: string;
}

export interface ApiError {
  detail: string;
}

export interface NavigationItem {
  title: string;
  href?: string;
  url?: string;
  icon: string;
  badge?: string;
  roles?: UserRole[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface Incident {
  id: string;
  tenant_id: string;
  title: string;
  description?: string;
  severity: string;
  status: string;
  risk_score: number;
  mitre_ids: string[];
  created_at: string;
}

export interface IncidentListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Incident[];
}

export interface TenantSettings {
  id?: string;
  tenant_id?: string;
  notification_email?: string;
  webhook_url?: string;
  timezone: string;
  data_retention_days: number;
  settings_json: Record<string, unknown>;
}

export interface TimeSeriesDataPoint {
  date: string;
  total: number;
  safe: number;
  blocked: number;
  avg_risk: number;
}

export interface TimeSeriesResponse {
  days: number;
  data: TimeSeriesDataPoint[];
}

export interface XaiAuditLog {
  id: number;
  event_type: string;
  url: string;
  risk_level: RiskLevel;
  risk_score: number;
  action_taken: ActionTaken;
  xai_explanation: string | null;
  xai_pending: boolean;
  details: Record<string, unknown>;
  created_at: string;
}

export interface XaiAuditLogListResponse {
  items: XaiAuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReputationCheckRequest {
  url: string;
}

export interface ReputationCheckResponse {
  url: string;
  domain: string;
  trust_level: string;
  is_safe: boolean;
  details: string;
}

export interface SystemHealthResponse {
  status: string;
  service: string;
  version: string;
  uptime_seconds: number;
  components: Record<string, { status: string; error?: string }>;
}

export interface SecurityEvent {
  id: number;
  tenant_id: number;
  event_type: string;
  source: string;
  severity: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SecurityEventListResponse {
  items: SecurityEvent[];
  total: number;
  page: number;
  page_size: number;
}

