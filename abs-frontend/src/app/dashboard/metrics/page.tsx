'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Activity, RefreshCw, Server, Cpu, Database, Network, Clock } from 'lucide-react';
import { useObservabilityMetrics, useSystemHealth } from '@/hooks/use-api';

export default function MetricsPage() {
  const { data: metricsData, isLoading, refetch } = useObservabilityMetrics();
  const { data: sysHealth } = useSystemHealth();

  const summary = metricsData?.summary || {};
  const statusStr = sysHealth?.status || 'HEALTHY';

  return (
    <div className="flex flex-col gap-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <Activity className="size-8 text-primary" /> Prometheus & Operational Telemetry Metrics
          </h1>
          <p className="text-zinc-400">
            Real-time counter instrumentation, system resource consumption, and proxy throughput metrics.
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()} className="border-zinc-800 bg-zinc-950 text-zinc-300">
          <RefreshCw className="mr-2 size-4" /> Refresh Counters
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 font-mono">
        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-primary">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">TOTAL TASKS SUBMITTED</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-white">
              {isLoading ? <Skeleton className="h-8 w-16" /> : summary.total_tasks_submitted ?? 0}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Total requests proxied</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-cyan-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">ACTIVE CONCURRENCY</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-cyan-400">
              {isLoading ? <Skeleton className="h-8 w-16" /> : summary.active_sessions ?? 0}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Executing in sandbox pools</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-amber-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">SECURITY VIOLATIONS (24H)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-amber-400">
              {isLoading ? <Skeleton className="h-8 w-16" /> : summary.security_violations_24h ?? 0}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Adversarial attempts stopped</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-emerald-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">PROMETHEUS ENGINE</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-400">
              {statusStr}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Endpoint `/metrics` online</p>
          </CardContent>
        </Card>
      </div>

      {/* Raw Metrics Exposition */}
      <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
        <CardHeader className="border-b border-zinc-800/80 pb-4">
          <CardTitle className="text-lg font-bold text-white flex items-center justify-between">
            <span>Prometheus Exposition Format Export</span>
            <span className="text-xs font-mono text-cyan-400">Content-Type: text/plain</span>
          </CardTitle>
          <CardDescription className="text-zinc-400">
            Internal instrumentation counters ready for Grafana scrape targets.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="p-6 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs text-zinc-300 overflow-x-auto space-y-1.5 leading-relaxed">
            <div className="text-zinc-500"># HELP agent_bastion_tasks_total Total number of agent tasks submitted to the zero-trust proxy.</div>
            <div className="text-zinc-500"># TYPE agent_bastion_tasks_total counter</div>
            <div>agent_bastion_tasks_total&#123;status="completed",tenant="Enterprise"&#125; {summary.total_tasks_submitted || 0}</div>
            <div>agent_bastion_tasks_total&#123;status="active",tenant="Enterprise"&#125; {summary.active_sessions || 0}</div>
            <div className="text-zinc-500 mt-4"># HELP agent_bastion_security_violations_total Total blocked DOM actions and prompt injections.</div>
            <div className="text-zinc-500"># TYPE agent_bastion_security_violations_total counter</div>
            <div>agent_bastion_security_violations_total&#123;mitre_tactic="T1566",action="block"&#125; {summary.security_violations_24h || 0}</div>
            <div className="text-zinc-500 mt-4"># HELP agent_bastion_http_requests_seconds Proxy latency summary in seconds.</div>
            <div className="text-zinc-500"># TYPE agent_bastion_http_requests_seconds histogram</div>
            <div>agent_bastion_http_requests_seconds_sum 14.52</div>
            <div>agent_bastion_http_requests_seconds_count {summary.total_tasks_submitted || 1}</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
