'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldCheck, Server, CheckCircle2, Circle, ArrowRight, PlayCircle, Terminal, Activity, Cpu, Fingerprint, Database, Network } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

import { 
  useDxOverview, 
  useDxQuickstart,
  useObservabilityHealth,
  useObservabilityWorkers,
} from '@/hooks/use-api';

export default function OverviewPage() {
  const { data: dxOverview } = useDxOverview();
  const { data: dxQuickstart } = useDxQuickstart();
  const { data: obsHealth } = useObservabilityHealth();
  const { data: obsWorkers } = useObservabilityWorkers();

  // Derive Onboarding Progress steps
  const qsSteps = dxQuickstart?.steps || [];
  const totalSteps = qsSteps.length || 8;
  const completedSteps = qsSteps.filter((s: any) => s.completed).length;
  const progressPercentage = dxQuickstart?.progress_percentage || Math.round((completedSteps / Math.max(1, totalSteps)) * 100);

  // Derive Health Statuses
  const workerStatusStr = dxOverview?.worker_health?.status || 'degraded';
  const workerCount = dxOverview?.worker_health?.active_workers ?? obsWorkers?.workers?.active_worker_count ?? 1;
  const pgStatus = obsHealth?.components?.postgresql === 'UP' ? 'healthy' : 'unhealthy';
  const redisStatus = obsHealth?.components?.redis_broker === 'UP' ? 'healthy' : (workerStatusStr === 'healthy' ? 'healthy' : 'warning');
  const overallObsHealth = obsHealth?.status === 'HEALTHY' ? 'healthy' : 'warning';

  return (
    <div className="flex flex-col gap-10 max-w-6xl mx-auto pb-12 pt-4">
      {/* Welcome Banner */}
      <div className="flex flex-col items-start gap-4 p-8 rounded-2xl bg-gradient-to-r from-zinc-900 to-zinc-900/50 border border-zinc-800/80 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-20 -mt-20 size-80 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="space-y-4 max-w-3xl relative z-10">
          <div className="inline-flex items-center gap-2 text-primary text-sm font-bold tracking-wider uppercase">
            <ShieldCheck className="size-4" /> Welcome to Agent-Bastion
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
            Deploy Production Grade <br/> Autonomous AI Agents
          </h1>
          <p className="text-lg text-zinc-400 font-medium max-w-2xl">
            Without rebuilding your infrastructure stack.
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-4 relative z-10 mt-4">
          <Link href="/dashboard/playground">
            <Button className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/25 font-semibold px-6 py-6 text-base">
              <Terminal className="mr-2 h-5 w-5" /> Open Agent Playground
            </Button>
          </Link>
          <Link href="/dashboard/docs">
            <Button variant="outline" className="border-zinc-700 hover:bg-zinc-800 text-zinc-200 px-6 py-6 font-semibold text-base">
              Read Documentation
            </Button>
          </Link>
        </div>
      </div>

      {/* Onboarding Progress Card */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-2 border-b border-zinc-800">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              Build Your First Production AI Agent
            </h2>
            <p className="text-zinc-400 mt-1">
              Follow these steps to securely configure, deploy, and observe your first autonomous session.
            </p>
          </div>
          <div className="flex items-center gap-3 bg-zinc-900 px-4 py-2 rounded-xl border border-zinc-800">
            <span className="text-sm font-medium text-zinc-400">Readiness</span>
            <div className="w-24 h-2.5 bg-zinc-800 rounded-full overflow-hidden">
              <div className="h-full bg-primary transition-all duration-500" style={{ width: `${progressPercentage}%` }} />
            </div>
            <span className="text-sm font-bold text-primary">{progressPercentage}%</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-2">
          
          <div className="flex flex-col p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 hover:border-primary/50 transition-all hover:-translate-y-1">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 className="size-5 text-emerald-500 shrink-0" />
              <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Step 1</span>
            </div>
            <h4 className="text-base font-bold text-white mb-2">Create Namespace</h4>
            <p className="text-sm text-zinc-400 flex-1">
              Establish a secure, isolated tenant for your agent infrastructure.
            </p>
            <Link href="/dashboard/namespaces" className="text-primary text-sm font-medium hover:underline mt-4 flex items-center gap-1">
              View Namespaces <ArrowRight className="size-3.5" />
            </Link>
          </div>

          <div className="flex flex-col p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 hover:border-primary/50 transition-all hover:-translate-y-1">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 className="size-5 text-emerald-500 shrink-0" />
              <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Step 2</span>
            </div>
            <h4 className="text-base font-bold text-white mb-2">Generate API Key</h4>
            <p className="text-sm text-zinc-400 flex-1">
              Provision scoped proxy keys to authenticate your agent's requests.
            </p>
            <Link href="/dashboard/keys" className="text-primary text-sm font-medium hover:underline mt-4 flex items-center gap-1">
              Manage Keys <ArrowRight className="size-3.5" />
            </Link>
          </div>

          <div className="flex flex-col p-5 rounded-xl bg-primary/10 border border-primary/30 hover:border-primary/50 transition-all shadow-lg shadow-primary/5 hover:-translate-y-1">
            <div className="flex items-center gap-2 mb-3">
              <Circle className="size-5 text-primary shrink-0 fill-primary/20" />
              <span className="text-xs font-bold text-primary uppercase tracking-wider">Step 3</span>
            </div>
            <h4 className="text-base font-bold text-white mb-2">Open Playground</h4>
            <p className="text-sm text-zinc-300 flex-1">
              Enter the control plane to visualize and configure your autonomous agent.
            </p>
            <Link href="/dashboard/playground" className="text-primary text-sm font-bold hover:underline mt-4 flex items-center gap-1">
              Launch Playground <ArrowRight className="size-3.5" />
            </Link>
          </div>

          <div className="flex flex-col p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-all">
            <div className="flex items-center gap-2 mb-3">
              <Circle className="size-5 text-zinc-700 shrink-0" />
              <span className="text-xs font-bold text-zinc-600 uppercase tracking-wider">Step 4</span>
            </div>
            <h4 className="text-base font-bold text-zinc-200 mb-2">Run Your First Agent</h4>
            <p className="text-sm text-zinc-400 flex-1">
              Deploy an autonomous task through the API gateway and security firewall.
            </p>
          </div>

          <div className="flex flex-col p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-all">
            <div className="flex items-center gap-2 mb-3">
              <Circle className="size-5 text-zinc-700 shrink-0" />
              <span className="text-xs font-bold text-zinc-600 uppercase tracking-wider">Step 5</span>
            </div>
            <h4 className="text-base font-bold text-zinc-200 mb-2">Observe Infrastructure</h4>
            <p className="text-sm text-zinc-400 flex-1">
              Watch the infrastructure route, execute, and monitor the agent live.
            </p>
          </div>

          <div className="flex flex-col p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-all">
            <div className="flex items-center gap-2 mb-3">
              <Circle className="size-5 text-zinc-700 shrink-0" />
              <span className="text-xs font-bold text-zinc-600 uppercase tracking-wider">Step 6</span>
            </div>
            <h4 className="text-base font-bold text-zinc-200 mb-2">Generate SDK Snippets</h4>
            <p className="text-sm text-zinc-400 flex-1">
              Export Python or Node.js code instantly from the Playground to integrate.
            </p>
          </div>

          <div className="flex flex-col p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-all">
            <div className="flex items-center gap-2 mb-3">
              <Circle className="size-5 text-zinc-700 shrink-0" />
              <span className="text-xs font-bold text-zinc-600 uppercase tracking-wider">Step 7</span>
            </div>
            <h4 className="text-base font-bold text-zinc-200 mb-2">Deploy Agent-Bastion</h4>
            <p className="text-sm text-zinc-400 flex-1">
              Move from local dev to production seamlessly using identical Docker overlays.
            </p>
          </div>

          <div className="flex flex-col p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 justify-center items-center text-center">
            <ShieldCheck className="size-12 text-zinc-700 mb-4" />
            <h4 className="text-base font-bold text-zinc-300">8. Production Ready</h4>
            <p className="text-sm text-zinc-500 mt-2">
              Your AI Agents are now secure, observable, and scalable.
            </p>
          </div>

        </div>
      </div>

      {/* System & Observability Health Bar */}
      <div className="flex flex-col gap-4 mt-6">
        <div className="flex items-end justify-between pb-2 border-b border-zinc-800">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              Infrastructure Status
            </h2>
          </div>
          <span className="text-sm text-zinc-400 flex items-center gap-2">
            <span className="size-2 rounded-full bg-emerald-500 animate-pulse" /> All Systems Nominal
          </span>
        </div>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-4 mt-2">
          
          <div className="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Network className="size-4 text-zinc-400" />
              <span className="text-sm text-zinc-300 font-medium">API Gateway</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500" />
              <span className="text-sm font-bold text-white">HEALTHY</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Cpu className="size-4 text-zinc-400" />
              <span className="text-sm text-zinc-300 font-medium">Workers</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`size-2 rounded-full ${workerStatusStr === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span className="text-sm font-bold text-white uppercase">{workerStatusStr}</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-zinc-400" />
              <span className="text-sm text-zinc-300 font-medium">Security Engine</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500" />
              <span className="text-sm font-bold text-white">HEALTHY</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Activity className="size-4 text-zinc-400" />
              <span className="text-sm text-zinc-300 font-medium">Metrics</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`size-2 rounded-full ${overallObsHealth === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span className="text-sm font-bold text-white uppercase">{overallObsHealth === 'healthy' ? 'HEALTHY' : 'DEGRADED'}</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Server className="size-4 text-zinc-400" />
              <span className="text-sm text-zinc-300 font-medium">Queues</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`size-2 rounded-full ${redisStatus === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span className="text-sm font-bold text-white uppercase">{redisStatus === 'healthy' ? 'HEALTHY' : 'DEGRADED'}</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Fingerprint className="size-4 text-zinc-400" />
              <span className="text-sm text-zinc-300 font-medium">Audit Trails</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`size-2 rounded-full ${pgStatus === 'healthy' ? 'bg-emerald-500' : 'bg-red-500'}`} />
              <span className="text-sm font-bold text-white uppercase">{pgStatus === 'healthy' ? 'HEALTHY' : 'UNHEALTHY'}</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Database className="size-4 text-zinc-400" />
              <span className="text-sm text-zinc-300 font-medium">Observability</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`size-2 rounded-full ${overallObsHealth === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span className="text-sm font-bold text-white uppercase">{overallObsHealth === 'healthy' ? 'HEALTHY' : 'DEGRADED'}</span>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
