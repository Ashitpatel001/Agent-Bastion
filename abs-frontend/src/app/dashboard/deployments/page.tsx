'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Server, CheckCircle2, Copy, Check, Terminal, ShieldCheck, AlertTriangle, Layers, Cpu, Database } from 'lucide-react';
import { toast } from 'sonner';
import { useInfrastructureStatus } from '@/hooks/use-api';

export default function DeploymentsPage() {
  const { data: infraStatus, refetch } = useInfrastructureStatus();
  const [copiedMode, setCopiedMode] = React.useState<string | null>(null);

  const copyText = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMode(id);
    toast.success('Run command copied to clipboard');
    setTimeout(() => setCopiedMode(null), 2000);
  };

  return (
    <div className="flex flex-col gap-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <Server className="size-8 text-primary" /> Deployment Parity & Environment Modes
          </h1>
          <p className="text-zinc-400">
            Verify identical core container architecture across local development and enterprise production topologies.
          </p>
        </div>
      </div>

      <div className="p-5 rounded-2xl bg-gradient-to-r from-zinc-900 via-zinc-900/90 to-primary/10 border border-primary/30 flex flex-col sm:flex-row items-center justify-between gap-4 font-mono text-xs">
        <div className="flex items-center gap-3">
          <ShieldCheck className="size-6 text-emerald-400 shrink-0" />
          <div>
            <span className="text-white font-bold block text-sm font-sans">100% Architectural Parity Rule Active</span>
            <span className="text-zinc-400">There is only ONE product: Agent Bastion. Codebase remains identical in both deployment modes.</span>
          </div>
        </div>
        <span className="px-3 py-1.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-bold shrink-0">
          ● ZERO CONFIGURATION DRIFT
        </span>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Local Development Mode */}
        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 flex flex-col justify-between">
          <div>
            <CardHeader className="pb-3 border-b border-zinc-800/80">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-1 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 font-mono text-xs font-bold">
                  MODE 1: LOCAL DEVELOPMENT
                </span>
                <span className="text-xs font-mono text-emerald-400">PORT 8000</span>
              </div>
              <CardTitle className="text-2xl font-bold text-white mt-3">Local Sandbox Stack</CardTitle>
              <CardDescription className="text-zinc-400">
                Full-stack container execution without external domain or SSL dependencies (`docker-compose.dev.yml`).
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-4 font-mono text-xs">
              <div className="space-y-2 text-zinc-300">
                <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>FastAPI Gateway API (`/api/v1/*`)</span></div>
                <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Multi-Tenant PostgreSQL + pgvector</span></div>
                <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Redis Message Broker (`redis:6379`)</span></div>
                <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Celery Worker Nodes (`abs-worker-agent`)</span></div>
                <div className="flex items-center gap-2 text-zinc-500"><span>✕ Caddy Automatic TLS / HTTPS (Disabled locally)</span></div>
              </div>
            </CardContent>
          </div>

          <div className="p-6 border-t border-zinc-800 bg-zinc-950/60 rounded-b-xl space-y-2 font-mono text-xs">
            <span className="text-zinc-500 block">DOCKER LAUNCH COMMAND:</span>
            <div className="flex items-center justify-between p-3 rounded-lg bg-black border border-zinc-800">
              <code className="text-cyan-400 font-bold truncate">docker compose -f docker-compose.dev.yml up --build</code>
              <Button size="sm" variant="ghost" onClick={() => copyText('docker compose -f docker-compose.dev.yml up --build', 'dev')} className="h-7 px-2 text-zinc-400 hover:text-white shrink-0">
                {copiedMode === 'dev' ? <Check className="size-3.5 text-emerald-400" /> : <Copy className="size-3.5" />}
              </Button>
            </div>
          </div>
        </Card>

        {/* Production Mode */}
        <Card className="glass-panel bg-zinc-900/60 border-primary/40 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-primary text-primary-foreground px-4 py-1 text-xs font-mono font-bold rounded-bl-xl">
            PRODUCTION READY
          </div>
          <div>
            <CardHeader className="pb-3 border-b border-zinc-800/80">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-1 rounded bg-primary/20 text-primary border border-primary/40 font-mono text-xs font-bold">
                  MODE 2: ENTERPRISE PRODUCTION
                </span>
                <span className="text-xs font-mono text-emerald-400">PORT 80 / 443</span>
              </div>
              <CardTitle className="text-2xl font-bold text-white mt-3">Zero-Trust Cloud Gateway</CardTitle>
              <CardDescription className="text-zinc-400">
                Enables automatic Caddy TLS termination, domain routing, and enterprise WAF rules (`docker-compose.yml`).
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-4 font-mono text-xs">
              <div className="space-y-2 text-zinc-300">
                <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Caddy Reverse Proxy (`Port 80/443` Automatic TLS)</span></div>
                <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>FastAPI Gateway API (`/api/v1/*`)</span></div>
                <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Multi-Tenant PostgreSQL + pgvector</span></div>
                <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Distributed Celery Workers (`abs-worker-agent`, `xai`)</span></div>
                <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Prometheus Metrics Export (`/metrics`)</span></div>
              </div>
            </CardContent>
          </div>

          <div className="p-6 border-t border-zinc-800 bg-zinc-950/60 rounded-b-xl space-y-2 font-mono text-xs">
            <span className="text-zinc-500 block">DOCKER LAUNCH COMMAND:</span>
            <div className="flex items-center justify-between p-3 rounded-lg bg-black border border-zinc-800">
              <code className="text-emerald-400 font-bold truncate">docker compose up --build -d</code>
              <Button size="sm" variant="ghost" onClick={() => copyText('docker compose up --build -d', 'prod')} className="h-7 px-2 text-zinc-400 hover:text-white shrink-0">
                {copiedMode === 'prod' ? <Check className="size-3.5 text-emerald-400" /> : <Copy className="size-3.5" />}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
