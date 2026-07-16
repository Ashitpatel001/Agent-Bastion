'use client';

import React, { useEffect, useState } from 'react';
import { apiClient } from '@/services/api';
import { Server, Database, Cpu, ShieldCheck, CheckCircle2, AlertTriangle, RefreshCw, Activity, Layers } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default function InfrastructureDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchInfrastructure = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getInfrastructureStatus();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to inspect infrastructure services');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInfrastructure();
    const interval = setInterval(fetchInfrastructure, 15000);
    return () => clearInterval(interval);
  }, []);

  const services = data?.services || {};
  const pg = services?.postgres || {};
  const redis = services?.redis || {};
  const api = services?.api || {};
  const workers = services?.workers || {};
  const caddy = services?.caddy || {};

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Server className="size-6 text-primary" />
            System Infrastructure & Service Health
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time status of core services (`PostgreSQL`, `Redis`, `FastAPI Gateway`, `Distributed Workers`, `Caddy WAF`).
          </p>
        </div>
        <Button onClick={fetchInfrastructure} variant="outline" size="sm" className="gap-2" disabled={loading}>
          <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
          Inspect Infrastructure
        </Button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm flex items-center gap-3">
          <AlertTriangle className="size-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Overall Health Status Banner */}
      <Card className="bg-muted/30 border-border/60">
        <CardContent className="p-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-full ${data?.status === 'healthy' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'}`}>
              {data?.status === 'healthy' ? <CheckCircle2 className="size-6" /> : <AlertTriangle className="size-6" />}
            </div>
            <div>
              <h2 className="font-semibold text-base">
                Overall Infrastructure Status: <span className="uppercase">{data?.status || 'UNKNOWN'}</span>
              </h2>
              <p className="text-xs text-muted-foreground">
                Environment: `{data?.environment || 'development'}` | Last Probed: {data?.timestamp ? new Date(data.timestamp).toLocaleTimeString() : 'N/A'}
              </p>
            </div>
          </div>
          <Badge variant="outline" className="font-mono text-xs">
            Host: {caddy?.domain || 'localhost'}
          </Badge>
        </CardContent>
      </Card>

      {/* Core Infrastructure Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* PostgreSQL Service Card */}
        <Card className="border-border/60">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-500">
                <Database className="size-5" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold">PostgreSQL 16</CardTitle>
                <CardDescription className="text-xs">Relational Storage & Audit Logs</CardDescription>
              </div>
            </div>
            <Badge variant="outline" className={pg.status === 'healthy' ? 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10' : 'text-red-500 border-red-500/30 bg-red-500/10'}>
              {pg.status === 'healthy' ? 'UP' : 'DOWN'}
            </Badge>
          </CardHeader>
          <CardContent className="text-xs space-y-2 pt-1">
            <div className="flex justify-between text-muted-foreground">
              <span>Query Latency:</span>
              <span className="font-mono font-medium text-foreground">{pg.latency_ms || 0} ms</span>
            </div>
            <div className="p-2.5 rounded bg-muted/40 font-mono text-[11px] text-muted-foreground truncate">
              {pg.details || 'Checking connectivity...'}
            </div>
          </CardContent>
        </Card>

        {/* Redis Service Card */}
        <Card className="border-border/60">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-red-500/10 text-red-500">
                <Layers className="size-5" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold">Redis 7 Broker</CardTitle>
                <CardDescription className="text-xs">Task Queues & Rate Limiting</CardDescription>
              </div>
            </div>
            <Badge variant="outline" className={redis.status === 'healthy' ? 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10' : 'text-red-500 border-red-500/30 bg-red-500/10'}>
              {redis.status === 'healthy' ? 'UP' : 'DOWN'}
            </Badge>
          </CardHeader>
          <CardContent className="text-xs space-y-2 pt-1">
            <div className="flex justify-between text-muted-foreground">
              <span>Ping Latency:</span>
              <span className="font-mono font-medium text-foreground">{redis.latency_ms || 0} ms</span>
            </div>
            <div className="p-2.5 rounded bg-muted/40 font-mono text-[11px] text-muted-foreground truncate">
              {redis.details || 'Checking broker status...'}
            </div>
          </CardContent>
        </Card>

        {/* Celery Workers Card */}
        <Card className="border-border/60">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-500">
                <Cpu className="size-5" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold">Celery Workers</CardTitle>
                <CardDescription className="text-xs">Distributed Execution Engine</CardDescription>
              </div>
            </div>
            <Badge variant="outline" className={workers.status === 'healthy' ? 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10' : 'text-amber-500 border-amber-500/30 bg-amber-500/10'}>
              {workers.status === 'healthy' ? 'ONLINE' : (workers.status || 'OFFLINE')}
            </Badge>
          </CardHeader>
          <CardContent className="text-xs space-y-2 pt-1">
            <div className="flex justify-between text-muted-foreground">
              <span>Active Worker Pools:</span>
              <span className="font-mono font-medium text-foreground">{workers.active_nodes || 0} nodes</span>
            </div>
            <div className="p-2.5 rounded bg-muted/40 font-mono text-[11px] text-muted-foreground truncate">
              {workers.active_nodes > 0 ? `Active pools: ${workers.nodes?.map((n: any) => n.node_id.split('@')[1] || n.node_id).join(', ')}` : 'No workers responded to ping'}
            </div>
          </CardContent>
        </Card>

        {/* FastAPI Gateway Card */}
        <Card className="border-border/60">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-500">
                <Activity className="size-5" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold">FastAPI Gateway</CardTitle>
                <CardDescription className="text-xs">Multi-Tenant Security Proxy</CardDescription>
              </div>
            </div>
            <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10">
              UP
            </Badge>
          </CardHeader>
          <CardContent className="text-xs space-y-2 pt-1">
            <div className="flex justify-between text-muted-foreground">
              <span>Gateway Uptime:</span>
              <span className="font-mono font-medium text-foreground">{api.uptime_seconds || 0}s</span>
            </div>
            <div className="p-2.5 rounded bg-muted/40 font-mono text-[11px] text-muted-foreground truncate">
              {api.details || 'Uvicorn Async Gateway Online'}
            </div>
          </CardContent>
        </Card>

        {/* Caddy Reverse Proxy Card */}
        <Card className="border-border/60">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-amber-500/10 text-amber-500">
                <ShieldCheck className="size-5" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold">Caddy Reverse Proxy</CardTitle>
                <CardDescription className="text-xs">WAF & TLS Inspection Layer</CardDescription>
              </div>
            </div>
            <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10">
              ACTIVE
            </Badge>
          </CardHeader>
          <CardContent className="text-xs space-y-2 pt-1">
            <div className="flex justify-between text-muted-foreground">
              <span>Configured Host:</span>
              <span className="font-mono font-medium text-foreground">{caddy.domain || 'localhost'}</span>
            </div>
            <div className="p-2.5 rounded bg-muted/40 font-mono text-[11px] text-muted-foreground truncate">
              {caddy.details || 'Caddy Reverse Proxy Online'}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
