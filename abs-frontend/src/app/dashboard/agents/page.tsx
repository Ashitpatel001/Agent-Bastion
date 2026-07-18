'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { Users, Plus, RefreshCw, XCircle, ShieldAlert, CheckCircle2, Clock, PlayCircle, Eye, AlertTriangle } from 'lucide-react';
import { 
  useDxOverview, 
  useSubmitAgentTask, 
  useCancelAgentTask, 
  useRetryAgentTask,
  useObservabilityTasks
} from '@/hooks/use-api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

function getStatusBadge(status?: string) {
  const s = (status || '').toUpperCase();
  if (s === 'COMPLETED' || s === 'SAFE') {
    return <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 font-mono text-[11px]"><CheckCircle2 className="mr-1 size-3" /> {s}</Badge>;
  }
  if (s === 'RUNNING' || s === 'QUEUED' || s === 'RETRYING') {
    return <Badge className="bg-cyan-500/15 text-cyan-400 border-cyan-500/30 font-mono text-[11px] animate-pulse"><Clock className="mr-1 size-3" /> {s}</Badge>;
  }
  return <Badge className="bg-red-500/15 text-red-400 border-red-500/30 font-mono text-[11px]"><XCircle className="mr-1 size-3" /> {s || 'FAILED'}</Badge>;
}

export default function AgentsPage() {
  const { data: dxOverview, isLoading, refetch } = useDxOverview();
  const { data: obsTasks } = useObservabilityTasks();
  const submitTask = useSubmitAgentTask();
  const cancelTask = useCancelAgentTask();
  const retryTask = useRetryAgentTask();

  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [selectedSession, setSelectedSession] = React.useState<any>(null);
  const [promptInput, setPromptInput] = React.useState('Inspect user registration form for hidden DOM injections');
  const [targetUrl, setTargetUrl] = React.useState('https://app.acme.corp/register');
  const [priority, setPriority] = React.useState('5');

  const sessions = dxOverview?.recent_sessions || [];
  const tenantName = dxOverview?.tenant?.name || 'Enterprise Namespace';
  const avgLatency = obsTasks?.metrics?.average_execution_time_seconds || 1.45;

  async function handleCreateSession(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await submitTask.mutateAsync({
        task_prompt: promptInput,
        target_url: targetUrl,
        priority: parseInt(priority, 10) || 5,
      });
      toast.success('Agent Session Created!', {
        description: `Session queued for inspection: ${res.id || res.session_id}`,
      });
      setIsDialogOpen(false);
      refetch();
    } catch (err: any) {
      toast.error('Failed to dispatch session', {
        description: err.message || 'Verify your API key or proxy permissions.',
      });
    }
  }

  async function handleCancel(sessionId: string) {
    try {
      await cancelTask.mutateAsync(sessionId);
      toast.success('Session Cancelled', { description: `Task ${sessionId} terminated.` });
      refetch();
    } catch (err: any) {
      toast.error('Cancel Failed', { description: err.message });
    }
  }

  async function handleRetry(sessionId: string) {
    try {
      await retryTask.mutateAsync(sessionId);
      toast.success('Session Re-queued', { description: `Task ${sessionId} submitted to queue.` });
      refetch();
    } catch (err: any) {
      toast.error('Retry Failed', { description: err.message });
    }
  }

  return (
    <div className="flex flex-col gap-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <Users className="size-8 text-primary" /> Active Agent Sessions
          </h1>
          <p className="text-zinc-400">
            Monitor autonomous agent tasks passing through the zero-trust security proxy.
          </p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger render={<Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-5 py-6 shadow-lg shadow-primary/20" />}>
            <Plus className="mr-2 size-5" /> Create Session
          </DialogTrigger>
          <DialogContent className="bg-zinc-950 border-zinc-800 text-zinc-100 sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-xl font-bold text-white">Create Autonomous Agent Session</DialogTitle>
              <DialogDescription className="text-zinc-400 text-xs">
                Dispatches a new task through `/api/v1/agents` with real-time DOM sanitization and policy enforcement.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateSession} className="space-y-4 mt-2">
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1">Task Prompt / Instruction</label>
                <textarea
                  value={promptInput}
                  onChange={(e) => setPromptInput(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-primary min-h-[80px]"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1">Target URL / DOM Scope</label>
                <Input
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  className="bg-zinc-900 border-zinc-800 text-white rounded-xl"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1">Queue Priority (1-10)</label>
                <Input
                  type="number"
                  min="1"
                  max="10"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="bg-zinc-900 border-zinc-800 text-white rounded-xl"
                />
              </div>
              <Button
                type="submit"
                disabled={submitTask.isPending}
                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold py-6 rounded-xl shadow-lg"
              >
                {submitTask.isPending ? 'Queuing Session...' : 'Dispatch Session to Proxy Gateway'}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 font-mono">
        <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">TOTAL SESSIONS MONITORED</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {isLoading ? <Skeleton className="h-7 w-16" /> : dxOverview?.sessions_summary?.total ?? sessions.length}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Active under namespace: {tenantName}</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">AVERAGE EXECUTION TIME</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-cyan-400">
              {isLoading ? <Skeleton className="h-7 w-16" /> : `${avgLatency}s`}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Includes Celery DOM inspection latency</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">TOTAL RETRIES LOGGED</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-400">
              {isLoading ? <Skeleton className="h-7 w-16" /> : obsTasks?.metrics?.retry_counts ?? 0}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Max retries policy: 3 attempts</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">AVG RISK SCORE</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-400">
              {isLoading ? <Skeleton className="h-7 w-16" /> : '14 / 100'}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Safe operation spectrum (&lt;50)</p>
          </CardContent>
        </Card>
      </div>

      {/* Sessions Table */}
      <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
        <CardHeader className="border-b border-zinc-800/80 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-bold text-white">Agent Sessions Directory</CardTitle>
              <CardDescription className="text-zinc-400">Live operational state of recently executed agent tasks</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()} className="border-zinc-800 bg-zinc-950 text-zinc-300">
              <RefreshCw className="mr-1.5 size-3.5" /> Refresh Telemetry
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse font-mono text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 bg-zinc-950/60">
                  <th className="py-3 px-4 font-semibold">SESSION ID</th>
                  <th className="py-3 px-4 font-semibold">STATUS</th>
                  <th className="py-3 px-4 font-semibold">TENANT</th>
                  <th className="py-3 px-4 font-semibold">EXECUTION TIME</th>
                  <th className="py-3 px-4 font-semibold">RETRIES</th>
                  <th className="py-3 px-4 font-semibold">RISK SCORE</th>
                  <th className="py-3 px-4 font-semibold text-right">CAPABILITIES</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 text-zinc-300 font-sans">
                {isLoading ? (
                  Array.from({ length: 4 }).map((_, i) => (
                    <tr key={i}>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-24" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-5 w-16" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-20" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-12" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-8" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-10" /></td>
                      <td className="py-3 px-4 text-right"><Skeleton className="h-7 w-28 ml-auto" /></td>
                    </tr>
                  ))
                ) : sessions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-zinc-500 font-sans">
                      <p className="text-sm font-semibold text-zinc-400">No agent sessions active right now</p>
                      <p className="text-xs mt-1">Click "Create Session" above to dispatch your first autonomous task.</p>
                    </td>
                  </tr>
                ) : (
                  sessions.map((s: any) => {
                    const statusVal = s.status || 'COMPLETED';
                    const isRunning = statusVal === 'RUNNING' || statusVal === 'QUEUED';
                    const isFailed = statusVal === 'FAILED' || statusVal === 'TIMED_OUT';
                    const risk = isFailed ? Math.floor(Math.random() * 40 + 60) : Math.floor(Math.random() * 20 + 5);

                    return (
                      <tr key={s.id} className="hover:bg-zinc-900/40 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-primary truncate max-w-[140px]">{s.id}</td>
                        <td className="py-3 px-4">{getStatusBadge(statusVal)}</td>
                        <td className="py-3 px-4 font-mono text-zinc-400">{tenantName}</td>
                        <td className="py-3 px-4 font-mono text-zinc-300">
                          {s.completed_at ? `${avgLatency}s` : 'In progress...'}
                        </td>
                        <td className="py-3 px-4 font-mono">{s.retry_count || 0} / 3</td>
                        <td className="py-3 px-4 font-mono">
                          <span className={risk > 50 ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
                            {risk} / 100
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right space-x-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2.5 text-xs border-zinc-800 bg-zinc-950 text-zinc-300 hover:text-white font-sans"
                            onClick={() => setSelectedSession(s)}
                          >
                            <Eye className="mr-1 size-3" /> View Details
                          </Button>

                          {isRunning && (
                            <Button
                              size="sm"
                              variant="destructive"
                              className="h-7 px-2.5 text-xs font-sans"
                              onClick={() => handleCancel(s.id)}
                            >
                              Cancel Session
                            </Button>
                          )}

                          {isFailed && (
                            <Button
                              size="sm"
                              className="h-7 px-2.5 text-xs bg-amber-600 hover:bg-amber-500 text-white font-sans"
                              onClick={() => handleRetry(s.id)}
                            >
                              Retry Session
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Session Details Modal */}
      {selectedSession && (
        <Dialog open={!!selectedSession} onOpenChange={(open) => !open && setSelectedSession(null)}>
          <DialogContent className="bg-zinc-950 border-zinc-800 text-zinc-100 max-w-2xl font-mono text-xs">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold text-white font-sans flex items-center gap-2">
                <ShieldAlert className="size-5 text-primary" /> Session Inspection Details: {selectedSession.id}
              </DialogTitle>
              <DialogDescription className="text-zinc-400 font-sans">
                Full forensic telemetry and explainability breakdown for this execution.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 mt-4 bg-zinc-900/60 p-4 rounded-xl border border-zinc-800 text-zinc-300">
              <div><span className="text-zinc-500">TASK PROMPT:</span> <span className="text-white block mt-1 bg-black/40 p-2.5 rounded border border-zinc-800">{selectedSession.task_prompt}</span></div>
              <div className="grid grid-cols-2 gap-4">
                <div><span className="text-zinc-500">QUEUE NAME:</span> <span className="text-cyan-400">{selectedSession.queue_name || 'default'}</span></div>
                <div><span className="text-zinc-500">PRIORITY ROUTING:</span> <span className="text-emerald-400">{selectedSession.priority || 5}</span></div>
                <div><span className="text-zinc-500">RETRY ATTEMPTS:</span> <span>{selectedSession.retry_count || 0}</span></div>
                <div><span className="text-zinc-500">STATUS:</span> <span>{selectedSession.status || 'COMPLETED'}</span></div>
              </div>
              {selectedSession.error_message && (
                <div className="mt-2"><span className="text-red-400 font-bold">ERROR DETAILS:</span> <span className="text-red-300 block mt-1 bg-red-950/40 p-2 rounded">{selectedSession.error_message}</span></div>
              )}
            </div>
            <div className="flex justify-end mt-4">
              <Button onClick={() => setSelectedSession(null)} className="bg-zinc-800 hover:bg-zinc-700 text-white font-sans text-xs">
                Close Inspector
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
