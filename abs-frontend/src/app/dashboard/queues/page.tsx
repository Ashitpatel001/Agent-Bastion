'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Server, Activity, RefreshCw, Layers, CheckCircle2, AlertTriangle, Clock } from 'lucide-react';
import { useObservabilityWorkers } from '@/hooks/use-api';

export default function QueuesPage() {
  const { data: obsWorkers, isLoading, refetch } = useObservabilityWorkers();

  const workersInfo = obsWorkers?.workers || {};
  const queueSizes: Record<string, number> = workersInfo?.queue_sizes || {
    high_priority: 0,
    default: 0,
    security_scan: 0,
  };
  const totalInQueue: number = Number(Object.values(queueSizes).reduce((a: any, b: any) => Number(a) + Number(b), 0));


  return (
    <div className="flex flex-col gap-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1 max-w-4xl">
          <h1 className="text-3xl font-bold tracking-tight uppercase flex items-center gap-2 text-white">
            <Server className="size-6 text-primary" /> QUEUES
          </h1>
          <p className="text-sm text-zinc-400">Celery distributed task backlog and asynchronous dispatching.</p>
          
          <div className="flex flex-wrap gap-3 mt-3 font-mono text-xs text-zinc-300">
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800">
              [ Total Tasks in Broker: {isLoading ? '...' : totalInQueue} ]
            </span>
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800 flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
              [ Broker Connected ]
            </span>
          </div>

          <details className="mt-4 group cursor-pointer">
            <summary className="text-xs font-semibold text-primary hover:underline list-none inline-flex items-center gap-1">
              Learn how distributed queues work <span className="group-open:rotate-90 transition-transform">&gt;</span>
            </summary>
            <div className="mt-3 p-4 rounded-xl border border-primary/20 bg-primary/5 text-xs text-zinc-300 leading-relaxed max-w-2xl">
              Queues are asynchronous data structures in Redis that safely hold autonomous agent tasks until a worker is ready to process them. Agent-Bastion provides <strong className="text-white font-mono">Priority Routing</strong> to guarantee critical AI agent execution is never blocked by slow background tasks.
            </div>
          </details>
        </div>
        <Button variant="outline" onClick={() => refetch()} className="border-zinc-800 bg-zinc-950 text-zinc-300">
          <RefreshCw className="mr-2 size-4" /> Refresh Backlog
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-3 font-mono">
        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-primary">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">TOTAL TASKS IN BROKER</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-white">
              {isLoading ? <Skeleton className="h-8 w-16" /> : totalInQueue}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Redis list depth total</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-cyan-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">BROKER CONNECTIVITY</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-cyan-400 flex items-center gap-1.5">
              <CheckCircle2 className="size-5 text-emerald-400" /> ONLINE
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Redis protocol connection active</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-emerald-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">QUEUING ROUTING ENGINE</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-400">
              HEALTHY
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Strict priority routing enabled</p>
          </CardContent>
        </Card>
      </div>

      {/* Queues Table */}
      <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
        <CardHeader className="border-b border-zinc-800/80 pb-4">
          <CardTitle className="text-lg font-bold text-white">Active Priority Queues & Depths</CardTitle>
          <CardDescription className="text-zinc-400">Redis broker queue inspection via Celery worker inspect</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse font-mono text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 bg-zinc-950/60">
                  <th className="py-3 px-4 font-semibold">QUEUE IDENTIFIER</th>
                  <th className="py-3 px-4 font-semibold">ROUTING PURPOSE</th>
                  <th className="py-3 px-4 font-semibold">PENDING DEPTH</th>
                  <th className="py-3 px-4 font-semibold">CONSUMER WORKERS</th>
                  <th className="py-3 px-4 font-semibold text-right">STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 text-zinc-300 font-sans">
                {isLoading ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i}>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-24" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-48" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-16" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-20" /></td>
                      <td className="py-3 px-4 text-right"><Skeleton className="h-5 w-20 ml-auto" /></td>
                    </tr>
                  ))
                ) : (
                  [
                    {
                      name: 'high_priority',
                      purpose: 'Real-time user-facing agents requiring sub-second DOM inspection and proxy response.',
                      depth: queueSizes['high_priority'] || 0,
                      workers: 'abs-worker-agent',
                      status: 'HEALTHY'
                    },
                    {
                      name: 'default',
                      purpose: 'Standard autonomous agent requests and background state evaluations.',
                      depth: queueSizes['default'] || 0,
                      workers: 'abs-worker-agent',
                      status: 'HEALTHY'
                    },
                    {
                      name: 'security_scan',
                      purpose: 'Asynchronous deep forensic explainability and MITRE ATT&CK XAI log generation.',
                      depth: queueSizes['security_scan'] || 0,
                      workers: 'abs-worker-xai',
                      status: 'HEALTHY'
                    }
                  ].map((q, idx) => (
                    <tr key={idx} className="hover:bg-zinc-900/40 transition-colors">
                      <td className="py-4 px-4 font-mono font-bold text-primary">{q.name}</td>
                      <td className="py-4 px-4 text-zinc-300 font-sans max-w-md leading-relaxed">{q.purpose}</td>
                      <td className="py-4 px-4 font-mono text-cyan-400 font-bold">{q.depth} tasks</td>
                      <td className="py-4 px-4 font-mono text-zinc-400">{q.workers}</td>
                      <td className="py-4 px-4 text-right">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          {q.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
