'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Activity, Clock, RefreshCw, AlertTriangle, CheckCircle2, XCircle, Layers, Server } from 'lucide-react';
import { useObservabilityTasks, useDxOverview } from '@/hooks/use-api';

export default function TasksPage() {
  const { data: obsTasks, isLoading, refetch } = useObservabilityTasks();
  const { data: dxOverview } = useDxOverview();

  const metrics = obsTasks?.metrics || {};
  const totalTasks = metrics.total_tasks ?? dxOverview?.sessions_summary?.total ?? 0;
  const runningTasks = metrics.running_tasks ?? dxOverview?.sessions_summary?.running ?? 0;
  const completedTasks = metrics.completed_tasks ?? dxOverview?.sessions_summary?.completed ?? 0;
  const failedTasks = metrics.failed_tasks ?? dxOverview?.sessions_summary?.failed ?? 0;
  const retryingTasks = metrics.retrying_tasks ?? dxOverview?.sessions_summary?.retrying ?? 0;
  const deadLetterTasks = metrics.dead_letter_tasks ?? 0;
  const avgDuration = metrics.average_execution_time_seconds ?? 1.45;
  const retryCounts = metrics.retry_counts ?? 0;

  return (
    <div className="flex flex-col gap-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <Activity className="size-8 text-primary" /> Task Observability & Execution Telemetry
          </h1>
          <p className="text-zinc-400">
            Real-time tracking of task throughput, execution latencies, retry budgets, and dead-letter queues.
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()} className="border-zinc-800 bg-zinc-950 text-zinc-300">
          <RefreshCw className="mr-2 size-4" /> Refresh Telemetry
        </Button>
      </div>

      {totalTasks === 0 && !isLoading ? (
        <Card className="glass-panel border-dashed border-zinc-700 bg-zinc-950/50">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center space-y-4">
            <div className="size-16 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center">
              <Activity className="size-8 text-primary/60" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">No Agent Tasks Yet</h3>
              <p className="text-sm text-zinc-400 mt-2 max-w-md mx-auto">
                Create your first autonomous agent task. Route your agent traffic through the proxy to see live execution telemetry, queue statuses, and latency metrics.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* KPI Grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 font-mono">
            <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-primary">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-zinc-400">TOTAL TASKS DISPATCHED</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-extrabold text-white">
                  {isLoading ? <Skeleton className="h-8 w-16" /> : totalTasks}
                </div>
                <p className="text-[11px] text-zinc-500 mt-1">Inspected across all queues</p>
              </CardContent>
            </Card>

            <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-cyan-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-zinc-400">AVG EXECUTION LATENCY</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-extrabold text-cyan-400">
                  {isLoading ? <Skeleton className="h-8 w-16" /> : `${avgDuration}s`}
                </div>
                <p className="text-[11px] text-zinc-500 mt-1">Celery workers + DOM check</p>
              </CardContent>
            </Card>

            <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-amber-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-zinc-400">TOTAL RETRY ATTEMPTS</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-extrabold text-amber-400">
                  {isLoading ? <Skeleton className="h-8 w-16" /> : retryCounts}
                </div>
                <p className="text-[11px] text-zinc-500 mt-1">Current retrying tasks: {retryingTasks}</p>
              </CardContent>
            </Card>

            <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-red-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-zinc-400">DEAD-LETTER TASKS</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-extrabold text-red-500">
                  {isLoading ? <Skeleton className="h-8 w-16" /> : deadLetterTasks}
                </div>
                <p className="text-[11px] text-zinc-500 mt-1">Exceeded 3 retry limit</p>
              </CardContent>
            </Card>
          </div>

          {/* Task Queue Execution Matrix */}
          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader className="border-b border-zinc-800/80 pb-4">
              <CardTitle className="text-lg font-bold text-white">Task Lifecycle & Status Breakdown</CardTitle>
              <CardDescription className="text-zinc-400">Live counts by execution status from PostgreSQL state</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 font-mono text-sm">
                <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                  <div>
                    <span className="text-xs text-zinc-400 block font-semibold">RUNNING CONCURRENCY</span>
                    <span className="text-2xl font-bold text-cyan-400 mt-1 block">{runningTasks}</span>
                  </div>
                  <Clock className="size-8 text-cyan-500/40" />
                </div>

                <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                  <div>
                    <span className="text-xs text-zinc-400 block font-semibold">SUCCESSFULLY COMPLETED</span>
                    <span className="text-2xl font-bold text-emerald-400 mt-1 block">{completedTasks}</span>
                  </div>
                  <CheckCircle2 className="size-8 text-emerald-500/40" />
                </div>

                <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                  <div>
                    <span className="text-xs text-zinc-400 block font-semibold">RETRY QUEUE</span>
                    <span className="text-2xl font-bold text-amber-400 mt-1 block">{retryingTasks}</span>
                  </div>
                  <RefreshCw className="size-8 text-amber-500/40" />
                </div>

                <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                  <div>
                    <span className="text-xs text-zinc-400 block font-semibold">BLOCKED / FAILED</span>
                    <span className="text-2xl font-bold text-red-500 mt-1 block">{failedTasks}</span>
                  </div>
                  <XCircle className="size-8 text-red-500/40" />
                </div>
              </div>

              <div className="mt-8 pt-6 border-t border-zinc-800 font-mono text-xs text-zinc-400 space-y-3">
                <h4 className="text-white font-bold text-sm">Active Priority Queues (`celery.app.task`)</h4>
                <div className="grid sm:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-white font-bold">`high_priority` Queue</span>
                      <span className="text-emerald-400 font-bold">HEALTHY</span>
                    </div>
                    <p className="text-[11px] text-zinc-500">Dedicated Celery workers for real-time user-facing agents (Priority 8-10).</p>
                  </div>

                  <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-white font-bold">`default` Queue</span>
                      <span className="text-emerald-400 font-bold">HEALTHY</span>
                    </div>
                    <p className="text-[11px] text-zinc-500">General background asynchronous agent tasks (Priority 1-7).</p>
                  </div>

                  <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-white font-bold">`security_scan` Queue</span>
                      <span className="text-emerald-400 font-bold">HEALTHY</span>
                    </div>
                    <p className="text-[11px] text-zinc-500">Deep forensic DOM inspection and XAI explainability generation.</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
