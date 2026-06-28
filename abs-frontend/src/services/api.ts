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
    
    if (this.apiKey) {
      headers.set('X-API-Key', this.apiKey);
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
      throw new Error(`Network error: ${error.message}`);
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
      throw new Error(errorMessage);
    }

    return data as T;
  }

  public async registerTenant(data: TenantCreateRequest): Promise<TenantCreateResponse> {
    return this.fetch<TenantCreateResponse>('/v1/tenants', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  public async submitAgentTask(data: AgentSessionCreateRequest): Promise<AgentSession> {
    return this.fetch<AgentSession>('/v1/agent/run', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  public async getAgentStatus(jobId: string): Promise<AgentSession> {
    return this.fetch<AgentSession>(`/v1/agent/status/${jobId}`, {
      method: 'GET',
    });
  }

  public async cancelAgentTask(jobId: string): Promise<Record<string, unknown>> {
    return this.fetch<Record<string, unknown>>(`/v1/agent/cancel/${jobId}`, {
      method: 'POST',
    });
  }

  public async getActivePolicy(): Promise<Policy> {
    return this.fetch<Policy>('/v1/security/policies', {
      method: 'GET',
    });
  }

  public async updatePolicy(data: PolicyUpdateRequest): Promise<Policy> {
    return this.fetch<Policy>('/v1/security/policies', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  public async getSecurityLogs(page: number = 1, pageSize: number = 50): Promise<AuditLogListResponse> {
    return this.fetch<AuditLogListResponse>(`/v1/security/logs?page=${page}&page_size=${pageSize}`, {
      method: 'GET',
    });
  }

  public async getSecurityStats(): Promise<SecurityStats> {
    return this.fetch<SecurityStats>('/v1/security/stats', {
      method: 'GET',
    });
  }

  public async healthCheck(): Promise<HealthResponse> {
    return this.fetch<HealthResponse>('/health', {
      method: 'GET',
    });
  }
}
