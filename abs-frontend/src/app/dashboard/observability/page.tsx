'use client';

import React, { useEffect, useState } from 'react';
import { apiClient } from '@/services/api';
import { Layers, Activity, ShieldAlert, CheckCircle2, AlertTriangle, RefreshCw, BarChart3, Clock, Cpu } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default function ObservabilityDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<any>(null);
  const [taskMetrics, setTaskMetrics] = useState<any>(null);
  const [securityMetrics, setSecurityMetrics] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [timeWindow, setTimeWindow] = useState<number>(7);

  const fetchAllObservability = async () => {
    setLoading(true);
    setError(null);
    try {
      const [mRes, tRes, sRes] = await Promise.all([
        apiClient.getObservabilityMetrics(),
        apiClient.getTaskObservability(),
        apiClient.getSecurityObservability(timeWindow)
      ]);
      setMetrics(mRes);
      setTaskMetrics(tRes?.metrics || tRes);
      setSecurityMetrics(sRes?.intelligence || sRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load observability telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllObservability();
    const interval = setInterval(fetchAllObservability, 20000);
    return () => clearInterval(interval);
  }, [timeWindow]);

  const summary = metrics?.summary || {};
  const tStats = taskMetrics || {};
  const sIntel = securityMetrics || {};

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Layers className="size-6 text-primary" />
            System Observability & Security Intelligence
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Production telemetry, task lifecycle analytics, security detection counters, and rate-limiting metrics.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select 
            value={timeWindow} 
            onChange={(e) => setTimeWindow(Number(e.target.value))}
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value={1}>Last 24 Hours</option>
            <option value={7}>Last 7 Days</option>
            <option value={30}>Last 30 Days</option>
          </select>
          <Button onClick={fetchAllObservability} variant="outline" size="sm" className="gap-2" disabled={loading}>
            <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Telemetry
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm flex items-center gap-3">
          <AlertTriangle className="size-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top Telemetry KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Tasks Processed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? '...' : (summary.total_tasks_submitted ?? tStats.total_tasks ?? 0)}</div>
            <p className="text-xs text-muted-foreground mt-1">Lifecycle sessions dispatched</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">{loading ? '...' : (summary.active_sessions ?? tStats.running_tasks ?? 0)}</div>
            <p className="text-xs text-muted-foreground mt-1">Currently running or queued tasks</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Average Execution Latency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center gap-1.5 font-mono">
              <Clock className="size-5 text-emerald-500" />
              {loading ? '...' : `${tStats.average_execution_time_seconds || 0}s`}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Task lifecycle completion time</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Security Violations Blocked</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">
              {loading ? '...' : (summary.security_violations_24h ?? sIntel.total_blocked_actions ?? 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">WAF / Prompt injections intercepted</p>
          </CardContent>
        </Card>
      </div>

      {/* Task Lifecycle Breakdown & Security Vectors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="size-4 text-primary" />
              Task Execution Status Breakdown
            </CardTitle>
            <CardDescription>Aggregate distribution of task lifecycle completion statuses.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 rounded-lg border bg-card flex justify-between items-center">
                <span className="text-muted-foreground">Completed</span>
                <Badge variant="outline" className="text-emerald-500 font-mono">{tStats.completed_tasks ?? 0}</Badge>
              </div>
              <div className="p-3 rounded-lg border bg-card flex justify-between items-center">
                <span className="text-muted-foreground">Running</span>
                <Badge variant="outline" className="text-blue-500 font-mono">{tStats.running_tasks ?? 0}</Badge>
              </div>
              <div className="p-3 rounded-lg border bg-card flex justify-between items-center">
                <span className="text-muted-foreground">Queued</span>
                <Badge variant="outline" className="text-zinc-400 font-mono">{tStats.queued_tasks ?? 0}</Badge>
              </div>
              <div className="p-3 rounded-lg border bg-card flex justify-between items-center">
                <span className="text-muted-foreground">Failed / DLQ</span>
                <Badge variant="outline" className="text-red-500 font-mono">{tStats.failed_tasks ?? 0}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldAlert className="size-4 text-red-500" />
              Top Attack Vectors Detected
            </CardTitle>
            <CardDescription>Security detections categorized across prompt injections and exfiltration.</CardDescription>
          </CardHeader>
          <CardContent>
            {sIntel.attack_breakdown_by_vector && Object.keys(sIntel.attack_breakdown_by_vector).length > 0 ? (
              <div className="space-y-2.5">
                {Object.entries(sIntel.attack_breakdown_by_vector).map(([vector, count]: [string, any], idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-lg border bg-card text-sm">
                    <span className="font-mono">{vector}</span>
                    <Badge variant="destructive" className="font-mono">{count} blocked</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-muted-foreground text-sm border border-dashed rounded-lg">
                No active attack detections recorded in this window.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent High Risk Security Events Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="size-4 text-primary" />
            Recent High-Risk Security Interceptions
          </CardTitle>
          <CardDescription>Real-time audit trail of intercepted requests with risk score &gt;= 50.</CardDescription>
        </CardHeader>
        <CardContent>
          {sIntel.recent_high_risk_events && sIntel.recent_high_risk_events.length > 0 ? (
            <div className="space-y-3">
              {sIntel.recent_high_risk_events.map((evt: any, idx: number) => (
                <div key={idx} className="p-3 rounded-lg border bg-muted/20 flex flex-col md:flex-row md:items-center justify-between gap-2 text-sm">
                  <div>
                    <div className="font-semibold text-foreground">{evt?.event_type || 'Attack Detection'}</div>
                    <div className="text-xs font-mono text-muted-foreground">{evt?.url}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="destructive" className="text-xs font-mono">Risk Score: {evt?.risk_score}</Badge>
                    <span className="text-xs text-muted-foreground">{new Date(evt?.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground text-sm">
              All agent traffic within safety limits. No critical security blocks required.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
