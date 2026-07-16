import {
  TenantCreateRequest,
  TenantCreateResponse,
  AgentSessionCreateRequest,
  AgentSession,
  Policy,
  PolicyUpdateRequest,
  AuditLogListResponse,
  SecurityStats,
  HealthResponse,
  LoginRequest,
  RegisterRequest,
  IncidentListResponse,
  TenantSettings,
  TimeSeriesResponse,
  XaiAuditLogListResponse,
  ReputationCheckResponse,
  SystemHealthResponse,
  SecurityEventListResponse,
} from '@/types';
import { API_BASE_URL } from '@/lib/constants';

export class AbsApiClient {

  private constructor(
    private readonly baseUrl: string,
    private readonly apiKey?: string
  ) {}

  public static create(apiKey?: string): AbsApiClient {
    return new AbsApiClient(API_BASE_URL, apiKey);
  }

  private async fetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers);
    
    let key = this.apiKey;
    if (!key && typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('abs-app-storage');
        if (stored) {
          const parsed = JSON.parse(stored);
          if (parsed.state?.apiKey) {
            key = parsed.state.apiKey;
          }
        }
      } catch (e) {
        // ignore
      }
    }

    if (key) {
      if (key.startsWith('ey')) {
        headers.set('Authorization', `Bearer ${key}`);
      } else {
        headers.set('X-API-Key', key);
      }
    }
    
    if (!headers.has('Content-Type') && options.method !== 'GET' && options.method !== 'HEAD') {
      headers.set('Content-Type', 'application/json');
    }

    const config: RequestInit = {
      ...options,
      headers,
    };

    const url = `${this.baseUrl}${endpoint}`;
    let response: Response;

    try {
      response = await fetch(url, config);
    } catch (error: any) {
      console.error(`[ABSs API Error] Network error for ${endpoint}:`, error);
      throw new Error(`Backend service unreachable (${endpoint}): ${error.message || 'Connection refused'}`);
    }

    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      let errorMessage = 'An error occurred';
      if (data && typeof data === 'object' && 'detail' in data) {
        if (typeof data.detail === 'string') {
            errorMessage = data.detail;
        } else if (Array.isArray(data.detail) && data.detail.length > 0 && data.detail[0].msg) {
             errorMessage = data.detail[0].msg;
        } else {
            errorMessage = JSON.stringify(data.detail);
        }
      } else if (typeof data === 'string') {
        errorMessage = data;
      }

      // Handle 401 Unauthorized — clear stale credentials and redirect to login
      if (response.status === 401 && typeof window !== 'undefined') {
        try {
          localStorage.removeItem('abs-app-storage');
        } catch (_) { /* ignore */ }
        setTimeout(() => {
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
        }, 1500);
      }

      throw new Error(errorMessage);
    }

    // Ensure compatibility if backend sends 'total_events' instead of 'total_actions'
    if (endpoint.includes('/api/v1/security/stats') || endpoint.includes('/api/v1/analytics/overview')) {
      const stats = data as any;
      if (stats && typeof stats === 'object') {
        if (stats.total_events !== undefined && stats.total_actions === undefined) {
          stats.total_actions = stats.total_events;
          let blocked = 0;
          if (stats.risk_distribution) {
            blocked = (stats.risk_distribution['CRITICAL'] || 0) + (stats.risk_distribution['HIGH'] || 0);
          }
          stats.blocked_actions = blocked || stats.blocked_events || 0;
          stats.safe_actions = stats.total_events - stats.blocked_actions;
          stats.active_sessions = stats.active_sessions ?? 0;
        }
      }
    }

    return data as T;
  }

  public async registerTenant(data: TenantCreateRequest): Promise<TenantCreateResponse> {
    return this.fetch<TenantCreateResponse>('/api/v1/tenants', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  public async submitAgentTask(data: AgentSessionCreateRequest): Promise<AgentSession> {
    return this.fetch<AgentSession>('/api/v1/agent/run', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  public async getAgentStatus(jobId: string): Promise<AgentSession> {
    return this.fetch<AgentSession>(`/api/v1/agent/status/${jobId}`, {
      method: 'GET',
    });
  }

  public async cancelAgentTask(jobId: string): Promise<Record<string, unknown>> {
    return this.fetch<Record<string, unknown>>(`/api/v1/agent/cancel/${jobId}`, {
      method: 'POST',
    });
  }

  public async retryAgentTask(jobId: string): Promise<Record<string, unknown>> {
    return this.fetch<Record<string, unknown>>(`/api/v1/agents/${jobId}/retry`, {
      method: 'POST',
    });
  }

  public async getDxQuickstart(): Promise<Record<string, any>> {
    return this.fetch<Record<string, any>>('/api/v1/dx/quickstart', {
      method: 'GET',
    });
  }

  public async getDxOverview(): Promise<Record<string, any>> {
    return this.fetch<Record<string, any>>('/api/v1/dx/overview', {
      method: 'GET',
    });
  }

  public async getActivePolicy(): Promise<Policy> {
    return this.fetch<Policy>('/api/v1/security/policies', {
      method: 'GET',
    });
  }

  public async updatePolicy(data: PolicyUpdateRequest): Promise<Policy> {
    return this.fetch<Policy>('/api/v1/security/policies', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  public async getSecurityLogs(page: number = 1, pageSize: number = 50): Promise<AuditLogListResponse> {
    return this.fetch<AuditLogListResponse>(`/api/v1/security/logs?page=${page}&page_size=${pageSize}`, {
      method: 'GET',
    });
  }

  public async getSecurityStats(): Promise<SecurityStats> {
    return this.fetch<SecurityStats>('/api/v1/security/stats', {
      method: 'GET',
    });
  }

  public async healthCheck(): Promise<HealthResponse> {
    return this.fetch<HealthResponse>('/health', {
      method: 'GET',
    });
  }

  public async login(data: LoginRequest): Promise<Record<string, any>> {
    return this.fetch<Record<string, any>>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  public async registerV1(data: RegisterRequest): Promise<Record<string, any>> {
    return this.fetch<Record<string, any>>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  public async getIncidents(page: number = 1, pageSize: number = 50): Promise<IncidentListResponse> {
    return this.fetch<IncidentListResponse>(`/api/v1/incidents?skip=${(page - 1) * pageSize}&limit=${pageSize}`, {
      method: 'GET',
    });
  }

  public async getSettings(): Promise<TenantSettings> {
    return this.fetch<TenantSettings>('/api/v1/settings', {
      method: 'GET',
    });
  }

  public async updateSettings(data: Partial<TenantSettings>): Promise<TenantSettings> {
    return this.fetch<TenantSettings>('/api/v1/settings', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  public async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    return this.fetch<T>(endpoint, options);
  }

  async getAnalyticsOverview(): Promise<SecurityStats> {
    return this.request('/api/v1/analytics/overview');
  }

  async getAnalyticsTimeSeries(days: number = 30): Promise<TimeSeriesResponse> {
    return this.request(`/api/v1/analytics/time-series?days=${days}`);
  }

  async getXaiLogs(page: number = 1, pageSize: number = 20, pendingOnly: boolean = false): Promise<XaiAuditLogListResponse> {
    return this.request(`/api/v1/audit?page=${page}&page_size=${pageSize}&pending_only=${pendingOnly}`);
  }

  async checkReputation(url: string): Promise<ReputationCheckResponse> {
    return this.request('/api/v1/reputation/check', { method: 'POST', body: JSON.stringify({ url }) });
  }

  async getSystemHealth(): Promise<SystemHealthResponse> {
    return this.request('/api/v1/system/health');
  }

  async getSecurityEvents(page: number = 1, pageSize: number = 50): Promise<SecurityEventListResponse> {
    return this.request(`/api/v1/security-events?page=${page}&page_size=${pageSize}`);
  }
  async simulateTraffic(): Promise<any> {
    return this.request('/api/v1/sandbox/simulate-traffic', { method: 'POST' });
  }

  async getInfrastructureStatus(): Promise<any> {
    return this.request('/api/v1/system/infrastructure');
  }

  async getWorkerObservability(): Promise<any> {
    return this.request('/api/v1/observability/workers');
  }

  async getTaskObservability(): Promise<any> {
    return this.request('/api/v1/observability/tasks');
  }

  async getSecurityObservability(days: number = 7): Promise<any> {
    return this.request(`/api/v1/observability/security?days=${days}`);
  }

  async getTenantObservability(): Promise<any> {
    return this.request('/api/v1/observability/tenants');
  }

  async getAuditTrail(page: number = 1, pageSize: number = 50): Promise<any> {
    return this.request(`/api/v1/observability/audit-trail?limit=${pageSize}&offset=${(page - 1) * pageSize}`);
  }

  async getObservabilityMetrics(): Promise<any> {
    return this.request('/api/v1/observability/metrics');
  }
}

export const apiClient = AbsApiClient.create();


