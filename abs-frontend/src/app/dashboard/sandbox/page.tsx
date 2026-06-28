'use client';

import * as React from 'react';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { useSubmitAgentTask, useAgentStatus, useCancelAgentTask } from '@/hooks/use-api';
import { useAppStore } from '@/store/app-store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Loader2, Terminal, StopCircle, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { SessionStatus } from '@/types';
import { SESSION_STATUS_COLORS } from '@/lib/constants';

const formSchema = z.object({
  task_prompt: z.string().min(5, { message: 'Task prompt must be at least 5 characters.' }),
  target_url: z.string().url({ message: 'Must be a valid URL (e.g. https://example.com)' }).optional().or(z.literal('')),
});

export default function SandboxPage() {
  const { activeJobId, setActiveJobId } = useAppStore();
  const submitTask = useSubmitAgentTask();
  const cancelTask = useCancelAgentTask();
  
  const { data: jobStatus, isLoading: isStatusLoading } = useAgentStatus(activeJobId);
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      task_prompt: '',
      target_url: '',
    },
  });

  const isActive = jobStatus && [SessionStatus.QUEUED, SessionStatus.RUNNING].includes(jobStatus.status);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      const data = {
        task_prompt: values.task_prompt,
        target_url: values.target_url || undefined,
      };
      
      const session = await submitTask.mutateAsync(data);
      setActiveJobId(session.id);
      
      toast.success('Agent session started', {
        description: `Job ID: ${session.id}`,
      });
    } catch (error: any) {
      toast.error('Failed to start session', {
        description: error.message || 'An error occurred',
      });
    }
  }
  
  async function handleCancel() {
    if (!activeJobId) return;
    
    try {
      await cancelTask.mutateAsync(activeJobId);
      toast.success('Cancel request sent');
    } catch (error: any) {
      toast.error('Failed to cancel session', {
        description: error.message || 'An error occurred',
      });
    }
  }
  
  async function handleClear() {
    setActiveJobId(null);
    form.reset();
  }

  return (
    <div className="flex flex-col h-full gap-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agent Sandbox</h1>
        <p className="text-muted-foreground">
          Deploy an autonomous AI agent through the ABSs proxy for testing and validation.
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Terminal className="size-5" /> Mission Parameters
            </CardTitle>
            <CardDescription>
              Configure the goal and target for the autonomous agent.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <FormField
                  control={form.control}
                  name="task_prompt"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Agent Objective</FormLabel>
                      <FormControl>
                        <Textarea 
                          placeholder="e.g. Find the pricing page and summarize the enterprise tier features." 
                          className="min-h-[120px] bg-zinc-900/50 resize-none" 
                          {...field} 
                          disabled={isActive}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="target_url"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Starting URL (Optional)</FormLabel>
                      <FormControl>
                        <Input 
                          placeholder="https://example.com" 
                          className="bg-zinc-900/50" 
                          {...field} 
                          disabled={isActive}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="flex justify-end gap-2 pt-4">
                  {activeJobId ? (
                    <>
                      <Button type="button" variant="outline" onClick={handleClear} disabled={isActive}>
                        Clear Session
                      </Button>
                      <Button type="button" variant="destructive" onClick={handleCancel} disabled={!isActive || cancelTask.isPending}>
                        {cancelTask.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <StopCircle className="mr-2 h-4 w-4" />}
                        Abort Mission
                      </Button>
                    </>
                  ) : (
                    <Button type="submit" className="w-full sm:w-auto" disabled={submitTask.isPending}>
                      {submitTask.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Terminal className="mr-2 h-4 w-4" />}
                      Deploy Agent
                    </Button>
                  )}
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>

        <Card className="glass flex flex-col h-full min-h-[400px]">
          <CardHeader className="border-b border-border bg-zinc-900/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Live Telemetry</CardTitle>
              {jobStatus ? (
                <Badge variant="outline" className={SESSION_STATUS_COLORS[jobStatus.status]}>
                  {jobStatus.status}
                </Badge>
              ) : (
                <Badge variant="outline" className="text-zinc-500">IDLE</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="flex-1 p-0 bg-black/40 overflow-hidden relative font-mono text-sm">
            {activeJobId ? (
              <div className="p-4 space-y-4 overflow-y-auto h-full max-h-[500px]">
                <div className="text-zinc-500">[{jobStatus?.created_at ? new Date(jobStatus.created_at).toLocaleTimeString() : '...'}] System: Session initialized. Job ID: {activeJobId}</div>
                
                {jobStatus?.started_at && (
                  <div className="text-blue-400">[{new Date(jobStatus.started_at).toLocaleTimeString()}] System: Agent worker assigned. Navigating to target...</div>
                )}
                
                {isActive && (
                  <div className="flex items-center gap-2 text-emerald-500">
                    <RefreshCw className="size-3 animate-spin" /> 
                    <span>Agent is reasoning and executing actions via ABSs Proxy...</span>
                  </div>
                )}
                
                {jobStatus?.status === SessionStatus.COMPLETED && (
                  <>
                    <div className="text-emerald-500 flex items-center gap-2">
                      <CheckCircle2 className="size-4" /> 
                      <span>Mission accomplished.</span>
                    </div>
                    {jobStatus.result_summary && (
                      <div className="mt-4 p-3 bg-zinc-900 rounded border border-zinc-800 text-zinc-300">
                        <div className="text-xs text-zinc-500 mb-2 uppercase">Result Summary</div>
                        {jobStatus.result_summary}
                      </div>
                    )}
                  </>
                )}
                
                {jobStatus?.status === SessionStatus.FAILED && (
                  <>
                    <div className="text-red-500 flex items-center gap-2">
                      <AlertCircle className="size-4" /> 
                      <span>Mission failed.</span>
                    </div>
                    {jobStatus.error_message && (
                      <div className="mt-4 p-3 bg-red-950/30 rounded border border-red-900/50 text-red-400">
                        <div className="text-xs text-red-500/70 mb-2 uppercase">Error Trace</div>
                        {jobStatus.error_message}
                      </div>
                    )}
                  </>
                )}
                
                {jobStatus?.status === SessionStatus.CANCELLED && (
                  <div className="text-amber-500 flex items-center gap-2">
                    <StopCircle className="size-4" /> 
                    <span>Mission manually aborted by operator.</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-zinc-600 p-8 text-center gap-4">
                <Terminal className="size-12 opacity-20" />
                <p>Deploy an agent to monitor live execution telemetry, intercepted network requests, and DOM mutations here.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
