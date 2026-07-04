import {
  SecurityStats,
  TimeSeriesResponse,
  IncidentListResponse,
  SecurityEventListResponse,
  AuditLogListResponse,
  XaiAuditLogListResponse,
  Policy,
  TenantSettings,
  RiskLevel,
  ActionTaken,
} from '@/types';

// Seed for consistent but evolving randomness
let callCount = 0;

export function getMockSecurityStats(): SecurityStats {
  callCount++;
  const baseActions = 14520 + Math.floor(callCount / 2);
  const blockedActions = 432 + Math.floor(callCount / 10);
  
  return {
    total_actions: baseActions,
    safe_actions: baseActions - blockedActions,
    blocked_actions: blockedActions,
    active_sessions: 12 + (callCount % 4),
    policy_violations: 89,
    avg_risk_score: 14.5 + (Math.random() * 2),
    threat_categories: {
      'Prompt Injection': 120,
      'Data Exfiltration': 85,
      'Malicious Navigation': 140,
      'Unauthorized Form Submission': 87
    }
  };
}

export function getMockTimeSeries(days: number): TimeSeriesResponse {
  const data = [];
  const now = new Date();
  
  for (let i = days; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    data.push({
      date: d.toISOString().split('T')[0],
      safe: 300 + Math.floor(Math.random() * 200),
      blocked: 10 + Math.floor(Math.random() * 40)
    });
  }
  
  return { data };
}

export function getMockIncidents(): IncidentListResponse {
  const now = new Date();
  return {
    items: [
      {
        id: 'inc-1',
        tenant_id: 'tenant-1',
        title: 'Critical Prompt Injection Attempt',
        description: 'Agent attempted to execute hidden payload found in DOM.',
        severity: RiskLevel.CRITICAL,
        status: 'OPEN',
        source: 'Agent Action Sentinel',
        risk_score: 95,
        blocked_url: 'https://malicious-demo.com/inject',
        attack_vector: 'Prompt Injection',
        created_at: new Date(now.getTime() - 1000 * 60 * 5).toISOString(),
      },
      {
        id: 'inc-2',
        tenant_id: 'tenant-1',
        title: 'Data Exfiltration Blocked',
        description: 'Prevented agent from submitting sensitive environment data.',
        severity: RiskLevel.HIGH,
        status: 'RESOLVED',
        source: 'Network Proxy',
        risk_score: 82,
        blocked_url: 'https://evil-server.net/collect',
        attack_vector: 'Data Exfiltration',
        created_at: new Date(now.getTime() - 1000 * 60 * 60 * 2).toISOString(),
        resolved_at: new Date(now.getTime() - 1000 * 60 * 30).toISOString(),
      },
      {
        id: 'inc-3',
        tenant_id: 'tenant-1',
        title: 'Crypto Drainer Navigation',
        description: 'Blocked agent navigation to known web3 phishing domain.',
        severity: RiskLevel.CRITICAL,
        status: 'OPEN',
        source: 'URL Reputation Filter',
        risk_score: 98,
        blocked_url: 'https://wallet-drainer.eth.link',
        attack_vector: 'Phishing',
        created_at: new Date(now.getTime() - 1000 * 60 * 60 * 24).toISOString(),
      }
    ],
    total: 3,
    page: 1,
    page_size: 50,
    pages: 1
  };
}

export function getMockSecurityEvents(): SecurityEventListResponse {
  const now = new Date();
  return {
    items: [
      {
        id: 101,
        tenant_id: 'tenant-1',
        event_type: 'NETWORK_INTERCEPT',
        severity: RiskLevel.HIGH,
        source: '192.168.1.100',
        details: { description: 'Intercepted background pixel tracking request.', destination_url: 'https://tracker.malicious.com', is_blocked: true },
        raw_data: { headers: { "user-agent": "playwright" } },
        created_at: new Date(now.getTime() - 1000 * 15).toISOString()
      },
      {
        id: 102,
        tenant_id: 'tenant-1',
        event_type: 'DOM_SANITIZATION',
        severity: RiskLevel.MEDIUM,
        source: '192.168.1.100',
        details: { description: 'Stripped hidden CSS injection (opacity: 0).', destination_url: 'https://example.com', is_blocked: true },
        raw_data: null,
        created_at: new Date(now.getTime() - 1000 * 45).toISOString()
      }
    ],
    total: 2,
    page: 1,
    page_size: 50,
    pages: 1
  };
}

export function getMockSecurityLogs(): AuditLogListResponse {
  const now = new Date();
  return {
    items: [
      {
        id: 201,
        tenant_id: 'tenant-1',
        session_id: 'sess-alpha',
        event_type: 'AGENT_ACTION',
        severity: RiskLevel.SAFE,
        action: 'click',
        url: 'https://news.ycombinator.com',
        risk_score: 5,
        details: { element: 'a.titlelink', text: 'Show HN' },
        is_blocked: false,
        action_taken: ActionTaken.ALLOWED,
        timestamp: new Date(now.getTime() - 1000 * 10).toISOString(),
        created_at: new Date(now.getTime() - 1000 * 10).toISOString()
      },
      {
        id: 202,
        tenant_id: 'tenant-1',
        session_id: 'sess-beta',
        event_type: 'AGENT_ACTION',
        severity: RiskLevel.CRITICAL,
        action: 'fill',
        url: 'https://fake-login.com',
        risk_score: 95,
        details: { element: 'input[name="password"]', warning: 'Credential leak detected' },
        is_blocked: true,
        action_taken: ActionTaken.BLOCKED,
        timestamp: new Date(now.getTime() - 1000 * 120).toISOString(),
        created_at: new Date(now.getTime() - 1000 * 120).toISOString()
      }
    ],
    total: 2,
    page: 1,
    page_size: 50,
    pages: 1
  };
}

export function getMockXaiLogs(): XaiAuditLogListResponse {
  const now = new Date();
  return {
    items: [
      {
        id: 301,
        tenant_id: 'tenant-1',
        audit_log_id: 202,
        explanation: 'The agent attempted to input data matching the format of an internal API key into an unverified third-party form. This behavior strongly correlates with Data Exfiltration techniques (T1048). The action was blocked due to Policy Rule #4 (Prevent Credential Leakage).',
        risk_factors: [
          'Target domain "fake-login.com" was registered < 30 days ago.',
          'Input payload matches regex for AWS access keys.',
          'Domain is not present in tenant Allowlist.'
        ],
        recommendation: 'Verify the agent\'s prompt instructions. Ensure the agent is not mistakenly extracting internal keys from its context window and pasting them externally.',
        model_used: 'llama-3.1-70b-versatile',
        created_at: new Date(now.getTime() - 1000 * 115).toISOString(),
        audit_log: getMockSecurityLogs().items[1]
      }
    ],
    total: 1,
    page: 1,
    page_size: 20,
    pages: 1
  };
}

export function getMockActivePolicy(): Policy {
  return {
    id: 'pol-1',
    tenant_id: 'tenant-1',
    name: 'Strict Zero-Trust Profile',
    version: 3,
    blocked_domains: ['malicious.com', 'evil.net', '*.phish.io'],
    trusted_domains: ['github.com', 'openai.com', 'internal-corp.net'],
    blocked_actions: ['download', 'submit_form_untrusted'],
    max_risk_score: 75,
    enable_dom_sanitizer: true,
    enable_action_sentinel: true,
    enable_network_firewall: true,
    enable_xai: true,
    require_human_approval: false,
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
}

export function getMockSettings(): TenantSettings {
  return {
    id: 'set-1',
    tenant_id: 'tenant-1',
    notification_email: 'security@myorg.com',
    webhook_url: 'https://siem.myorg.com/webhook/abs',
    timezone: 'UTC',
    data_retention_days: 30,
    settings_json: {
      slack_webhook_url: '',
      auto_block_critical: true
    }
  };
}
