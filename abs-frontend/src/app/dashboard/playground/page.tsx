'use client';

import * as React from 'react';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { useSubmitAgentTask, useAgentStatus, useCancelAgentTask, useLlmStatus } from '@/hooks/use-api';
import { useAppStore } from '@/store/app-store';
import { SystemConfigStatus } from '@/components/system-config-status';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Loader2, Terminal, StopCircle, RefreshCw, CheckCircle2, AlertCircle, ShieldCheck, Activity, Cpu, Code2, Globe, Clock, Workflow, Network, Fingerprint, ChevronRight, ChevronDown } from 'lucide-react';
import { SessionStatus } from '@/types';
import { SESSION_STATUS_COLORS } from '@/lib/constants';

const formSchema = z.object({
  task_prompt: z.string().min(5, { message: 'Task prompt must be at least 5 characters.' }),
  target_url: z.string().url({ message: 'Must be a valid URL (e.g. https://example.com)' }).optional().or(z.literal('')),
  queue_name: z.string(),
  priority: z.coerce.number().min(1).max(10),
});

function ExecutionFlowVisualization({ status }: { status?: string }) {
  const steps = [
    { id: 'agent', label: 'Your AI Agent' },
    { id: 'gateway', label: 'API Gateway' },
    { id: 'auth', label: 'Authentication' },
    { id: 'policies', label: 'Security Policies' },
    { id: 'ratelimit', label: 'Rate Limiter' },
    { id: 'queue', label: 'Worker Queue Selection' },
    { id: 'worker', label: 'Worker Assignment' },
    { id: 'browser', label: 'Browser Runtime' },
    { id: 'security', label: 'Security Engine' },
    { id: 'risk', label: 'Risk Analysis' },
    { id: 'audit', label: 'Audit Trail' },
    { id: 'metrics', label: 'Metrics Collection' },
    { id: 'xai', label: 'Explainability' },
    { id: 'completion', label: 'Task Completion' },
  ];

  let activeIndex = -1;
  if (status === 'PENDING' || status === 'QUEUED') activeIndex = 5;
  if (status === 'RUNNING') activeIndex = 8;
  if (status === 'COMPLETED' || status === 'FAILED') activeIndex = 13;
  if (status === 'CANCELLED') activeIndex = 5;

  return (
    <Card className="bg-zinc-900/40 border-zinc-800 p-6 overflow-x-auto hide-scrollbar shadow-lg shadow-black/20">
      <div className="flex items-center min-w-max gap-1 px-2">
        {steps.map((step, idx) => {
          const isCompleted = idx <= activeIndex;
          const isActive = idx === activeIndex;
          const isFailed = status === 'FAILED' && isActive;
          
          let ringColor = 'border-zinc-700 bg-zinc-800 text-zinc-500';
          if (isCompleted) {
            if (isActive && status !== 'COMPLETED' && status !== 'FAILED') {
              ringColor = 'border-cyan-500 bg-cyan-500/20 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.4)]';
            } else if (isFailed) {
              ringColor = 'border-red-500 bg-red-500/20 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.4)]';
            } else {
              ringColor = 'border-emerald-500 bg-emerald-500/20 text-emerald-400';
            }
          }

          return (
            <React.Fragment key={step.id}>
              <div className="flex flex-col items-center gap-3 relative w-28 group">
                <div className={`size-8 rounded-full flex items-center justify-center border-2 transition-all duration-500 z-10 ${ringColor}`}>
                  {isCompleted && !isActive ? <CheckCircle2 className="size-4" /> : isFailed ? <AlertCircle className="size-4" /> : <span className="text-xs font-bold">{idx + 1}</span>}
                </div>
                <span className={`text-[10px] font-medium text-center leading-tight ${
                  isCompleted ? (isActive && status !== 'COMPLETED' && status !== 'FAILED' ? 'text-cyan-400 font-semibold' : isFailed ? 'text-red-400 font-semibold' : 'text-emerald-400') : 'text-zinc-500'
                }`}>
                  {step.label}
                </span>
              </div>
              {idx < steps.length - 1 && (
                <div className="w-8 relative h-0.5 flex items-center -mt-6">
                  <div className={`absolute inset-0 transition-colors duration-500 ${
                    idx < activeIndex ? 'bg-emerald-500' : 'bg-zinc-800'
                  }`} />
                  {idx === activeIndex - 1 && isActive && status !== 'COMPLETED' && status !== 'FAILED' && (
                    <div className="absolute h-0.5 bg-cyan-400 w-1/2 animate-pulse" />
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </Card>
  );
}

export default function PlaygroundPage() {
  const { activeJobId, setActiveJobId, tenantName } = useAppStore();
  const submitTask = useSubmitAgentTask();
  const cancelTask = useCancelAgentTask();
  const { data: llmStatus } = useLlmStatus();
  
  const { data: jobStatus } = useAgentStatus(activeJobId);
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      task_prompt: 'Navigate to https://example.com, analyze the page content, and extract the primary headings.',
      target_url: 'https://example.com',
      queue_name: 'agents',
      priority: 5,
    },
  });

  const isActive = jobStatus && [SessionStatus.QUEUED, SessionStatus.RUNNING].includes(jobStatus.status);

  const scrollRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [jobStatus?.telemetry_events, isActive]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      const data = {
        task_prompt: values.task_prompt,
        target_url: values.target_url || undefined,
        queue_name: values.queue_name,
        priority: values.priority,
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

  const exportPython = `
from agent_bastion import Agent

agent = Agent(
    api_key="YOUR_API_KEY",
    endpoint="http://localhost:8000"
)

response = agent.run(
    task_prompt="${form.watch('task_prompt') || 'Analyze the page.'}",
    target_url="${form.watch('target_url') || ''}",
    queue_name="${form.watch('queue_name')}",
    priority=${form.watch('priority')}
)
print(response)
  `.trim();

  const exportNode = `
import { AgentBastion } from 'agent-bastion';

const agent = new AgentBastion({
    apiKey: 'YOUR_API_KEY',
    endpoint: 'http://localhost:8000'
});

async function run() {
    const response = await agent.run({
        taskPrompt: "${form.watch('task_prompt') || 'Analyze the page.'}",
        targetUrl: "${form.watch('target_url') || ''}",
        queueName: "${form.watch('queue_name')}",
        priority: ${form.watch('priority')}
    });
    console.log(response);
}
run();
  `.trim();

  const exportCurl = `
curl -X POST "http://localhost:8000/api/v1/agent/run" \\
     -H "Authorization: Bearer YOUR_API_KEY" \\
     -H "Content-Type: application/json" \\
     -d '{
           "task_prompt": "${form.watch('task_prompt') || 'Analyze the page.'}",
           "target_url": "${form.watch('target_url') || ''}",
           "queue_name": "${form.watch('queue_name')}",
           "priority": ${form.watch('priority')}
         }'
  `.trim();

  const exportCli = `
# Using the Agent-Bastion CLI (abs)
abs run \\
  --prompt "${form.watch('task_prompt') || 'Analyze the page.'}" \\
  --url "${form.watch('target_url') || ''}" \\
  --queue "${form.watch('queue_name')}" \\
  --priority ${form.watch('priority')}
  `.trim();

  const exportOpenApi = JSON.stringify({
    "openapi": "3.1.0",
    "info": { "title": "Agent-Bastion API", "version": "v1" },
    "paths": {
      "/api/v1/agent/run": {
        "post": {
          "summary": "Submit an Agent Task",
          "requestBody": {
            "content": {
              "application/json": {
                "example": {
                  "task_prompt": form.watch('task_prompt') || "Analyze the page.",
                  "target_url": form.watch('target_url') || "",
                  "queue_name": form.watch('queue_name'),
                  "priority": form.watch('priority')
                }
              }
            }
          }
        }
      }
    }
  }, null, 2);

  return (
    <div className="flex flex-col h-full gap-6 max-w-[1600px] mx-auto pb-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 pb-4 border-b border-zinc-800">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Agent Playground
          </h1>
          <p className="text-sm text-zinc-400">
            Build, run, and observe autonomous AI agents moving through production infrastructure.
          </p>
        </div>
      </div>

      <div className="grid lg:grid-cols-12 gap-8 items-start flex-1 min-h-0">
        {/* Left Column: Configuration */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <SystemConfigStatus />
          
          <Card className="glass border-primary/20 bg-zinc-950/60 shadow-xl">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg font-semibold text-white">
                Configure AI Agent
              </CardTitle>
              <CardDescription>
                Define the objective and parameters for your agent.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4 p-3 bg-zinc-900/40 rounded-lg border border-zinc-800/80 mb-2">
                    <div>
                      <span className="text-[10px] uppercase text-zinc-500 font-bold tracking-wider">Tenant</span>
                      <div className="text-sm font-medium text-zinc-300 mt-0.5 truncate">{tenantName || 'system-local'}</div>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-zinc-500 font-bold tracking-wider">Security Policy</span>
                      <div className="text-sm font-medium text-emerald-400 mt-0.5">Strict (Enforced)</div>
                    </div>
                  </div>

                  <FormField
                    control={form.control}
                    name="task_prompt"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-zinc-300 font-semibold">Agent Objective</FormLabel>
                        <FormControl>
                          <Textarea 
                            className="min-h-[100px] bg-zinc-900 border-zinc-700 resize-none focus-visible:ring-primary/50 text-sm" 
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
                        <FormLabel className="text-zinc-300 font-semibold">Starting URL / Entrypoint</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-zinc-500" />
                            <Input 
                              className="bg-zinc-900 border-zinc-700 pl-9 focus-visible:ring-primary/50" 
                              {...field} 
                              disabled={isActive}
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="queue_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-zinc-300 font-semibold">Worker Queue</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <select 
                                disabled={isActive} 
                                value={field.value} 
                                onChange={field.onChange} 
                                className="flex h-10 w-full appearance-none items-center justify-between rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50 text-white"
                              >
                                <option value="agents">agents (Standard)</option>
                                <option value="priority_agents">priority_agents (Fast)</option>
                                <option value="xai">xai (Analysis)</option>
                              </select>
                              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3">
                                <ChevronDown className="h-4 w-4 opacity-50 text-white" />
                              </div>
                            </div>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="priority"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-zinc-300 font-semibold">Priority Level</FormLabel>
                          <FormControl>
                            <Input 
                              type="number"
                              min={1} max={10}
                              className="bg-zinc-900 border-zinc-700" 
                              {...field} 
                              disabled={isActive}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="flex gap-3 pt-4 border-t border-zinc-800/80">
                    {activeJobId ? (
                      <>
                        <Button type="button" variant="outline" className="flex-1 border-zinc-700 hover:bg-zinc-800" onClick={handleClear} disabled={isActive}>
                          Clear Session
                        </Button>
                        <Button type="button" variant="destructive" className="flex-1 shadow-lg shadow-red-900/20 font-semibold" onClick={handleCancel} disabled={!isActive || cancelTask.isPending}>
                          {cancelTask.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <StopCircle className="mr-2 h-4 w-4" />}
                          Cancel Execution
                        </Button>
                      </>
                    ) : (
                      <Button type="submit" className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-bold shadow-lg shadow-primary/20 py-6 text-sm" disabled={submitTask.isPending || !llmStatus?.ready}>
                        {submitTask.isPending ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Terminal className="mr-2 h-5 w-5" />}
                        {llmStatus?.ready ? 'Run Autonomous Agent' : 'Configure LLM First'}
                      </Button>
                    )}
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>

          {/* Export Snippets */}
          <Card className="glass border-zinc-800 bg-zinc-950/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2 text-zinc-300">
                <Code2 className="size-4 text-zinc-400" /> Export Integration Snippets
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Tabs defaultValue="python" className="w-full">
                <TabsList className="w-full rounded-none bg-zinc-900 border-y border-zinc-800 p-0 h-auto flex flex-wrap">
                  <TabsTrigger value="python" className="flex-1 rounded-none data-[state=active]:bg-zinc-800 data-[state=active]:text-cyan-400 py-2 text-xs font-medium">Python</TabsTrigger>
                  <TabsTrigger value="node" className="flex-1 rounded-none data-[state=active]:bg-zinc-800 data-[state=active]:text-yellow-400 py-2 text-xs font-medium">Node.js</TabsTrigger>
                  <TabsTrigger value="curl" className="flex-1 rounded-none data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-400 py-2 text-xs font-medium">cURL</TabsTrigger>
                  <TabsTrigger value="cli" className="flex-1 rounded-none data-[state=active]:bg-zinc-800 data-[state=active]:text-purple-400 py-2 text-xs font-medium">CLI</TabsTrigger>
                  <TabsTrigger value="openapi" className="flex-1 rounded-none data-[state=active]:bg-zinc-800 data-[state=active]:text-orange-400 py-2 text-xs font-medium">OpenAPI</TabsTrigger>
                </TabsList>
                <TabsContent value="python" className="p-0 m-0">
                  <div className="bg-black/60 p-4 overflow-x-auto text-[11px] font-mono text-zinc-300 h-48 custom-scrollbar">
                    <pre>{exportPython}</pre>
                  </div>
                </TabsContent>
                <TabsContent value="node" className="p-0 m-0">
                  <div className="bg-black/60 p-4 overflow-x-auto text-[11px] font-mono text-zinc-300 h-48 custom-scrollbar">
                    <pre>{exportNode}</pre>
                  </div>
                </TabsContent>
                <TabsContent value="curl" className="p-0 m-0">
                  <div className="bg-black/60 p-4 overflow-x-auto text-[11px] font-mono text-zinc-300 h-48 custom-scrollbar">
                    <pre>{exportCurl}</pre>
                  </div>
                </TabsContent>
                <TabsContent value="cli" className="p-0 m-0">
                  <div className="bg-black/60 p-4 overflow-x-auto text-[11px] font-mono text-zinc-300 h-48 custom-scrollbar">
                    <pre>{exportCli}</pre>
                  </div>
                </TabsContent>
                <TabsContent value="openapi" className="p-0 m-0">
                  <div className="bg-black/60 p-4 overflow-x-auto text-[11px] font-mono text-zinc-300 h-48 custom-scrollbar">
                    <pre>{exportOpenApi}</pre>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Live Execution Environment */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          
          {!activeJobId ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center px-4 py-24 bg-zinc-900/20 rounded-2xl border border-zinc-800/50 relative overflow-hidden">
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />
              <Terminal className="size-16 text-primary/40 mb-6 relative z-10" />
              <h2 className="text-2xl font-bold text-white mb-2 relative z-10">Waiting for your first Autonomous AI Agent.</h2>
              <p className="text-zinc-400 max-w-lg mb-8 relative z-10 text-sm">
                Run an agent and watch it move through the entire infrastructure stack in real time.
              </p>
              
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 relative z-10 text-left">
                {[
                  'Authentication', 'Security Policies', 'Queue Selection', 
                  'Worker Assignment', 'Browser Execution', 'Risk Analysis', 
                  'Audit Trails', 'Metrics Collection', 'Explainability', 
                  'Production Deployment'
                ].map((item, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-xs font-medium text-zinc-400 bg-zinc-900/50 px-3 py-2 rounded-lg border border-zinc-800/50">
                    <CheckCircle2 className="size-3 text-emerald-500/70 shrink-0" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* Real-time metrics ribbon */}
              <div className="grid grid-cols-4 gap-4">
                <Card className="bg-zinc-900/40 border-zinc-800 shadow-md">
                  <CardContent className="p-4 flex flex-col items-center justify-center text-center gap-1 h-full">
                    <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Session Status</span>
                    {jobStatus ? (
                      <Badge variant="outline" className={`mt-1 font-medium text-xs ${SESSION_STATUS_COLORS[jobStatus.status]}`}>
                        {jobStatus.status}
                      </Badge>
                    ) : (
                      <span className="text-sm font-bold text-zinc-500 mt-1">AWAITING TASK</span>
                    )}
                  </CardContent>
                </Card>
                <Card className="bg-zinc-900/40 border-zinc-800 shadow-md">
                  <CardContent className="p-4 flex flex-col items-center justify-center text-center gap-1 h-full">
                    <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Worker Node</span>
                    <div className="flex items-center gap-1.5 mt-1 text-sm font-bold text-zinc-300">
                      <Cpu className="size-4 text-cyan-500" />
                      {isActive ? 'abs-worker-agent' : <span className="text-zinc-500 text-xs font-medium uppercase tracking-wider">Awaiting Assignment</span>}
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-zinc-900/40 border-zinc-800 shadow-md">
                  <CardContent className="p-4 flex flex-col items-center justify-center text-center gap-1 h-full">
                    <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Risk Score</span>
                    <div className="flex items-center gap-1.5 mt-1 text-2xl font-bold text-emerald-400">
                      {jobStatus?.status === SessionStatus.COMPLETED ? '0' : <span className="text-zinc-500 text-xs font-medium uppercase tracking-wider mt-1">Pending Analysis</span>}
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-zinc-900/40 border-zinc-800 shadow-md">
                  <CardContent className="p-4 flex flex-col items-center justify-center text-center gap-1 h-full">
                    <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Execution Time</span>
                    <div className="flex items-center gap-1.5 mt-1 text-sm font-medium text-cyan-400">
                      <Clock className="size-4 text-cyan-500" />
                      {jobStatus?.started_at && jobStatus?.completed_at 
                        ? `${((new Date(jobStatus.completed_at).getTime() - new Date(jobStatus.started_at).getTime()) / 1000).toFixed(2)}s`
                        : isActive ? 'Running...' : <span className="text-zinc-500 text-xs font-medium uppercase tracking-wider">Not Started</span>}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="mb-2">
                <ExecutionFlowVisualization status={jobStatus?.status} />
              </div>

              <Tabs defaultValue="timeline" className="flex flex-col flex-1 min-h-[500px]">
                <TabsList className="bg-transparent border-b border-zinc-800 p-0 w-full justify-start rounded-none mb-4 overflow-x-auto h-auto hide-scrollbar gap-6">
                  <TabsTrigger value="timeline" className="text-sm font-medium data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none py-3 px-1 bg-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none shadow-none">
                    Execution Timeline
                  </TabsTrigger>
                  <TabsTrigger value="browser" className="text-sm font-medium data-[state=active]:text-cyan-500 data-[state=active]:border-b-2 data-[state=active]:border-cyan-500 rounded-none py-3 px-1 bg-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none shadow-none">
                    Browser Events
                  </TabsTrigger>
                  <TabsTrigger value="security" className="text-sm font-medium data-[state=active]:text-amber-500 data-[state=active]:border-b-2 data-[state=active]:border-amber-500 rounded-none py-3 px-1 bg-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none shadow-none">
                    Security Analysis
                  </TabsTrigger>
                  <TabsTrigger value="xai" className="text-sm font-medium data-[state=active]:text-purple-500 data-[state=active]:border-b-2 data-[state=active]:border-purple-500 rounded-none py-3 px-1 bg-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none shadow-none">
                    Explainability
                  </TabsTrigger>
                  <TabsTrigger value="audit" className="text-sm font-medium data-[state=active]:text-emerald-500 data-[state=active]:border-b-2 data-[state=active]:border-emerald-500 rounded-none py-3 px-1 bg-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none shadow-none">
                    Audit Timeline
                  </TabsTrigger>
                </TabsList>
                
                <TabsContent value="timeline" className="m-0 flex-1 flex flex-col">
                  <Card className="glass flex flex-col flex-1 border-zinc-800 overflow-hidden shadow-2xl">
                    <CardHeader className="border-b border-zinc-800 bg-zinc-950 py-3 px-4">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-semibold flex items-center gap-2 text-zinc-200">
                          <Activity className="size-4 text-cyan-400" /> Live Execution
                        </CardTitle>
                        <div className="flex gap-1.5">
                          <div className="size-2.5 rounded-full bg-red-500/20 border border-red-500/50"></div>
                          <div className="size-2.5 rounded-full bg-amber-500/20 border border-amber-500/50"></div>
                          <div className="size-2.5 rounded-full bg-emerald-500/20 border border-emerald-500/50"></div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="flex-1 p-0 bg-[#0a0a0a] relative font-mono text-sm overflow-hidden min-h-[400px]">
                      <div ref={scrollRef} className="p-5 space-y-4 overflow-y-auto absolute inset-0 custom-scrollbar pb-12">
                        <div className="text-zinc-500 mb-6">
                          <div className="text-primary font-bold">Agent-Bastion Execution Engine</div>
                          <div>Session ID: {activeJobId}</div>
                          <div>Target URL: {form.getValues('target_url') || 'Not Specified'}</div>
                          <div className="mt-2 border-b border-zinc-800 pb-2"></div>
                        </div>
                        
                        <div className="flex items-start gap-3 text-zinc-400">
                          <span className="text-zinc-600 shrink-0">[{jobStatus?.created_at ? new Date(jobStatus.created_at).toLocaleTimeString() : new Date().toLocaleTimeString()}]</span> 
                          <span>Agent task submitted via API Gateway.</span>
                        </div>
                        <div className="flex items-start gap-3 text-zinc-400">
                          <span className="text-zinc-600 shrink-0">[{jobStatus?.created_at ? new Date(jobStatus.created_at).toLocaleTimeString() : new Date().toLocaleTimeString()}]</span> 
                          <span>Authentication verified. Security policies applied.</span>
                        </div>
                        <div className="flex items-start gap-3 text-zinc-400">
                          <span className="text-zinc-600 shrink-0">[{jobStatus?.created_at ? new Date(jobStatus.created_at).toLocaleTimeString() : new Date().toLocaleTimeString()}]</span> 
                          <span>Assigned to queue '{jobStatus?.queue_name || 'agents'}' (Priority: {jobStatus?.priority || 5}). Waiting for worker assignment.</span>
                        </div>

                        {jobStatus?.telemetry_events?.map((event: any, i: number) => {
                          const isError = event.type === 'error' || event.message.toLowerCase().includes('failed');
                          const isSecurity = event.message.toLowerCase().includes('security') || event.message.toLowerCase().includes('policy');
                          
                          let textColor = 'text-zinc-300';
                          if (isError) textColor = 'text-red-400';
                          if (isSecurity) textColor = 'text-emerald-400';

                          return (
                            <div key={i} className={`flex items-start gap-3 hover:bg-zinc-900/30 px-1 -mx-1 py-1 rounded transition-colors ${textColor}`}>
                              <span className="text-zinc-600 shrink-0">[{new Date(event.timestamp).toLocaleTimeString()}]</span>
                              <span className="break-all">{event.message}</span>
                            </div>
                          );
                        })}
                        
                        {isActive && (
                          <div className="flex items-center gap-2 text-cyan-500 mt-6 px-1">
                            <RefreshCw className="size-4 animate-spin" /> 
                            <span className="animate-pulse">Awaiting next event...</span>
                          </div>
                        )}
                        
                        {jobStatus?.status === SessionStatus.COMPLETED && (
                          <div className="mt-8 pt-6 border-t border-zinc-800/50">
                            <div className="text-emerald-500 flex items-center gap-2 mb-4">
                              <CheckCircle2 className="size-5" /> 
                              <span className="text-base font-bold">Task Completed Successfully</span>
                            </div>
                            {jobStatus.result_summary && (
                              <div className="p-4 bg-zinc-900/60 rounded-xl border border-zinc-800 text-zinc-300">
                                <div className="text-xs text-zinc-500 mb-3 font-semibold uppercase tracking-wider">Execution Result</div>
                                <pre className="overflow-x-auto text-zinc-300 font-mono text-sm whitespace-pre-wrap">
                                  {typeof jobStatus.result_summary === 'object' ? JSON.stringify(jobStatus.result_summary, null, 2) : String(jobStatus.result_summary)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {jobStatus?.status === SessionStatus.FAILED && (
                          <div className="mt-8 pt-6 border-t border-zinc-800/50">
                            <div className="text-red-500 flex items-center gap-2 mb-4">
                              <AlertCircle className="size-5" /> 
                              <span className="text-base font-bold">Task Failed or Blocked</span>
                            </div>
                            {jobStatus.error_message && (
                              <div className="p-4 bg-red-950/20 rounded-xl border border-red-900/30 text-red-400">
                                <div className="text-xs text-red-500/70 mb-3 font-semibold uppercase tracking-wider">Error Details</div>
                                <pre className="overflow-x-auto text-red-400 font-mono text-sm whitespace-pre-wrap">
                                  {typeof jobStatus.error_message === 'object' ? JSON.stringify(jobStatus.error_message, null, 2) : String(jobStatus.error_message)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {jobStatus?.status === SessionStatus.CANCELLED && (
                          <div className="mt-8 pt-6 border-t border-zinc-800/50">
                            <div className="text-amber-500 flex items-center gap-2">
                              <StopCircle className="size-5" /> 
                              <span className="text-base font-bold">Execution Cancelled</span>
                            </div>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
                
                <TabsContent value="browser" className="m-0 flex-1 flex flex-col">
                  <Card className="glass flex flex-col flex-1 border-zinc-800 overflow-hidden shadow-2xl">
                    <CardContent className="flex-1 flex flex-col items-center justify-center text-center p-12 bg-[#0a0a0a] min-h-[400px]">
                      <div className="text-zinc-500 text-sm flex flex-col items-center gap-4">
                        <Globe className="size-12 text-zinc-700 animate-pulse" />
                        <p className="font-medium text-zinc-400">Waiting for browser runtime events...</p>
                        <p className="text-zinc-600 mt-2 max-w-sm">DOM interactions, network requests, and console logs from the headless browser sandbox will stream here automatically.</p>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="security" className="m-0 flex-1 flex flex-col">
                  <Card className="glass flex flex-col flex-1 border-zinc-800 overflow-hidden shadow-2xl">
                    <CardContent className="flex-1 flex flex-col items-center justify-center text-center p-12 bg-[#0a0a0a] min-h-[400px]">
                      <div className="text-zinc-500 text-sm flex flex-col items-center gap-4">
                        <ShieldCheck className="size-12 text-amber-500/50" />
                        <p className="text-amber-500 font-medium">Security Engine is monitoring...</p>
                        <p className="text-zinc-600 mt-2 max-w-sm">Prompt injections, data exfiltration attempts, and unauthorized network access are evaluated in real-time.</p>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="xai" className="m-0 flex-1 flex flex-col">
                  <Card className="glass flex flex-col flex-1 border-zinc-800 overflow-hidden shadow-2xl">
                    <CardContent className="flex-1 flex flex-col items-center justify-center text-center p-12 bg-[#0a0a0a] min-h-[400px]">
                      <div className="text-zinc-500 text-sm flex flex-col items-center gap-4">
                        <Activity className="size-12 text-purple-500/50 animate-pulse" />
                        <p className="text-purple-400 font-medium">Generating Explainability trace...</p>
                        <p className="text-zinc-600 mt-2 max-w-sm">AI intent, decision reasoning, and action justification will be provided upon task completion.</p>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="audit" className="m-0 flex-1 flex flex-col">
                  <Card className="glass flex flex-col flex-1 border-zinc-800 overflow-hidden shadow-2xl">
                    <CardContent className="flex-1 flex flex-col items-center justify-center text-center p-12 bg-[#0a0a0a] min-h-[400px]">
                      <div className="text-zinc-500 text-sm flex flex-col items-center gap-4">
                        <Fingerprint className="size-12 text-emerald-500/50" />
                        <p className="text-emerald-400 font-medium">Building Audit Timeline...</p>
                        <p className="text-zinc-600 mt-2 max-w-sm">An immutable log of every action taken by the AI agent is being recorded for compliance and review.</p>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </>
          )}

        </div>
      </div>
    </div>
  );
}
