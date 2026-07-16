'use client';

import React, { useEffect, useState } from 'react';
import { apiClient } from '@/services/api';
import { Cpu, Server, CheckCircle2, AlertTriangle, RefreshCw, Layers, Activity } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default function WorkersDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkerHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getWorkerObservability();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch worker observability data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkerHealth();
    const interval = setInterval(fetchWorkerHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const workersInfo = data?.workers || {};
  const nodes: any[] = workersInfo?.nodes || [];
  const queueSizes: Record<string, number> = workersInfo?.queue_sizes || {};
  const activeWorkerCount = workersInfo?.active_worker_count || 0;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Cpu className="size-6 text-primary" />
            Distributed Worker & Queue Health
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time status of Celery worker clusters (`abs-worker-agent` and `abs-worker-xai`), active task concurrency, and queue depths.
          </p>
        </div>
        <Button onClick={fetchWorkerHealth} variant="outline" size="sm" className="gap-2" disabled={loading}>
          <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Status
        </Button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm flex items-center gap-3">
          <AlertTriangle className="size-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Worker Nodes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center gap-2">
              {loading ? '...' : activeWorkerCount}
              {!loading && (activeWorkerCount > 0 ? (
                <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 gap-1 text-xs">
                  <CheckCircle2 className="size-3" /> Online
                </Badge>
              ) : (
                <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10 gap-1 text-xs">
                  <AlertTriangle className="size-3" /> Offline
                </Badge>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Celery worker pool cluster nodes</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Task Concurrency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : nodes.reduce((acc: number, n: any) => acc + (n.active_tasks || 0), 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Tasks currently executing in worker pools</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Queued Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : Number(Object.values(queueSizes).reduce((a: number, b: number) => Number(a) + Number(b), 0))}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Across all priority and isolation queues</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Dead-Letter Queue Policy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold text-foreground truncate">
              {workersInfo?.dead_letter_policy || '3 retries -> dead letter'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Automated quarantine for failed tasks</p>
          </CardContent>
        </Card>
      </div>

      {/* Worker Nodes Grid */}
      <h2 className="text-lg font-semibold tracking-tight mt-4">Active Worker Pool Cluster Nodes</h2>
      {loading ? (
        <div className="p-12 text-center text-muted-foreground text-sm">Inspecting distributed worker heartbeats...</div>
      ) : nodes.length === 0 ? (
        <Card className="border-dashed border-amber-500/30 bg-amber-500/5">
          <CardContent className="p-8 text-center">
            <AlertTriangle className="size-10 text-amber-500 mx-auto mb-3" />
            <h3 className="font-semibold text-foreground">No Celery Worker Nodes Detected</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
              Ensure `abs-worker-agent` and `abs-worker-xai` are running in your Docker Compose stack (`docker compose -f docker-compose.dev.yml up`).
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {nodes.map((node: any, i: number) => (
            <Card key={i} className="border-border/60">
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-lg bg-primary/10 text-primary">
                    <Server className="size-5" />
                  </div>
                  <div>
                    <CardTitle className="text-base font-semibold">{node.node_id}</CardTitle>
                    <CardDescription className="text-xs font-mono">{node.broker}</CardDescription>
                  </div>
                </div>
                <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 gap-1.5">
                  <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
                  {node.status || 'ONLINE'}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-3 pt-2">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="p-3 rounded-lg bg-muted/40 border border-border/40">
                    <span className="text-xs text-muted-foreground block">Pool Concurrency</span>
                    <span className="text-lg font-bold">{node.concurrency} worker slots</span>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/40 border border-border/40">
                    <span className="text-xs text-muted-foreground block">Active Tasks Executing</span>
                    <span className="text-lg font-bold text-blue-500">{node.active_tasks} tasks</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Queues Breakdown */}
      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="size-4 text-primary" />
            Distributed Queue Backlog & Isolation Status
          </CardTitle>
          <CardDescription>
            Live task breakdown per queue across high-priority and standard agent queues.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {Object.keys(queueSizes).length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">No queued tasks currently pending.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(queueSizes).map(([queueName, count]: [string, any], idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-lg border bg-card text-sm">
                  <div className="flex items-center gap-3">
                    <Activity className="size-4 text-blue-500" />
                    <span className="font-mono font-medium">{queueName}</span>
                  </div>
                  <Badge variant="secondary" className="font-mono">{count} pending tasks</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
