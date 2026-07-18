'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Terminal, Copy, Check, ShieldCheck, Play, ArrowRight, Server, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

export default function CliPage() {
  const [copiedCmd, setCopiedCmd] = React.useState<string | null>(null);
  const [activeCommand, setActiveCommand] = React.useState('init');

  const copyCommand = (cmd: string, id: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCmd(id);
    toast.success('Command copied to clipboard');
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const cliOutputs: Record<string, string> = {
    init: `$ agent-bastion init --name "Enterprise-Proxy" --tier PRO
[+] Initializing Agent-Bastion configuration in ./agent-bastion/
[✓] Generated policies.json with MITRE ATT&CK T1566 and T1048 WAF rules
[✓] Generated docker-compose.dev.yml (Local Dev Mode)
[✓] Generated docker-compose.yml (Production Mode)
[✓] Namespace initialized successfully. Ready to deploy.`,
    deploy: `$ agent-bastion deploy --mode production
[+] Verifying production environment readiness...
[✓] Caddy reverse proxy port 80 / 443 bound
[✓] Celery worker cluster (abs-worker-agent, abs-worker-xai) ready
[✓] PostgreSQL pgvector and Redis broker online
[+] Launching container stack...
[✓] Agent Bastion Control Plane active at http://localhost:8000`,
    status: `$ agent-bastion status
SYSTEM STATUS REPORT
--------------------------------------------------
API Gateway:         HEALTHY (Port 8000)
PostgreSQL Database: ONLINE (Multi-tenant schema)
Redis Message Queue: ONLINE (0 dead letters)
Active Workers:      2 nodes (Celery pool)
WAF Security Engine: ACTIVE (Action Sentinel)`
  };

  return (
    <div className="flex flex-col gap-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1 max-w-4xl">
          <h1 className="text-3xl font-bold tracking-tight uppercase flex items-center gap-2 text-white">
            <Terminal className="size-6 text-primary" /> COMMAND-LINE INTERFACE
          </h1>
          <p className="text-sm text-zinc-400">Control and inspect zero-trust agent gateways from your terminal.</p>
          
          <div className="flex flex-wrap gap-3 mt-3 font-mono text-xs text-zinc-300">
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800">
              [ Package: agent-bastion ]
            </span>
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800 flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
              [ Binary Installed ]
            </span>
          </div>

          <details className="mt-4 group cursor-pointer">
            <summary className="text-xs font-semibold text-primary hover:underline list-none inline-flex items-center gap-1">
              Learn how the CLI works <span className="group-open:rotate-90 transition-transform">&gt;</span>
            </summary>
            <div className="mt-3 p-4 rounded-xl border border-primary/20 bg-primary/5 text-xs text-zinc-300 leading-relaxed max-w-2xl">
              The CLI is the operational interface for Agent-Bastion. Use it to quickly scaffold proxy projects, deploy modular Docker-compose overlays, manage isolated tenants, and stream live worker logs without ever leaving your terminal.
            </div>
          </details>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 flex flex-col justify-between">
          <CardHeader>
            <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldCheck className="size-5 text-emerald-400" /> CLI Installation Guide
            </CardTitle>
            <CardDescription className="text-zinc-400">Standard distribution via Python pip</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 font-mono text-xs">
            <div>
              <span className="text-zinc-400 block mb-1">Install via PyPI (`agent-bastion`)</span>
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-zinc-950 border border-zinc-800">
                <span className="text-emerald-400 font-bold">$ pip install agent-bastion</span>
                <Button size="sm" variant="ghost" onClick={() => copyCommand('pip install agent-bastion', 'pip')} className="h-6 px-2 text-zinc-400 hover:text-white">
                  {copiedCmd === 'pip' ? <Check className="size-3 text-emerald-400" /> : <Copy className="size-3" />}
                </Button>
              </div>
            </div>

            <div>
              <span className="text-zinc-400 block mb-1">Verify CLI Binary Version</span>
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-zinc-950 border border-zinc-800">
                <span className="text-cyan-400 font-bold">$ agent-bastion version</span>
                <Button size="sm" variant="ghost" onClick={() => copyCommand('agent-bastion version', 'ver')} className="h-6 px-2 text-zinc-400 hover:text-white">
                  {copiedCmd === 'ver' ? <Check className="size-3 text-emerald-400" /> : <Copy className="size-3" />}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-2 glass-panel bg-zinc-900/60 border-zinc-800 flex flex-col justify-between">
          <CardHeader className="pb-3 border-b border-zinc-800/80">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <CardTitle className="text-lg font-bold text-white">Interactive Shell Preview & Simulator</CardTitle>
                <CardDescription className="text-zinc-400">Click a command to preview exact stdout response</CardDescription>
              </div>
              <div className="flex items-center gap-2 bg-zinc-950 p-1 rounded-xl border border-zinc-800 font-mono text-xs">
                <button
                  onClick={() => setActiveCommand('init')}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-all ${activeCommand === 'init' ? 'bg-primary text-white' : 'text-zinc-400 hover:text-white'}`}
                >
                  init
                </button>
                <button
                  onClick={() => setActiveCommand('deploy')}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-all ${activeCommand === 'deploy' ? 'bg-primary text-white' : 'text-zinc-400 hover:text-white'}`}
                >
                  deploy
                </button>
                <button
                  onClick={() => setActiveCommand('status')}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-all ${activeCommand === 'status' ? 'bg-primary text-white' : 'text-zinc-400 hover:text-white'}`}
                >
                  status
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            <pre className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs text-zinc-300 overflow-x-auto leading-relaxed min-h-[220px]">
              {cliOutputs[activeCommand]}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
