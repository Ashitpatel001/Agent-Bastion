'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileCode2, ShieldCheck, Server, Cpu, ExternalLink, BookOpen, Layers } from 'lucide-react';
import Link from 'next/link';

export default function DocsPage() {
  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <FileCode2 className="size-8 text-primary" /> System & Architecture Documentation
          </h1>
          <p className="text-zinc-400">
            Authoritative technical specification of the Agent Bastion zero-trust AI infrastructure proxy.
          </p>
        </div>
        <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-5 py-6 shadow-lg">
            <ExternalLink className="mr-2 size-4" /> Open Swagger / OpenAPI Reference
          </Button>
        </a>
      </div>

      <Tabs defaultValue="architecture" className="w-full">
        <TabsList className="grid w-full grid-cols-4 bg-zinc-900 border border-zinc-800 p-1 rounded-xl font-mono text-xs">
          <TabsTrigger value="architecture" className="rounded-lg">1. System Topology</TabsTrigger>
          <TabsTrigger value="security" className="rounded-lg">2. Action Sentinel</TabsTrigger>
          <TabsTrigger value="workers" className="rounded-lg">3. Celery & Redis</TabsTrigger>
          <TabsTrigger value="api" className="rounded-lg">4. API v1 Routes</TabsTrigger>
        </TabsList>

        <TabsContent value="architecture" className="mt-6 space-y-6">
          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-white flex items-center gap-2">
                <Layers className="size-5 text-primary" /> Multi-Layer Zero-Trust Gateway Architecture
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Agent Bastion sits directly between your autonomous agent client and external web resources.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 font-sans text-sm text-zinc-300 leading-relaxed">
              <p>
                Unlike standard HTTP proxies, Agent Bastion is designed specifically for autonomous LLM agents (LangChain, Playwright, CrewAI). It enforces rate limits at the Caddy ingress layer (`Port 80/443`) and passes JSON payloads to the FastAPI control plane (`Port 8000`).
              </p>
              <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs space-y-2">
                <div className="text-cyan-400 font-bold">Inbound Request Pipeline:</div>
                <div>1. Agent SDK / cURL sends `POST /api/v1/agents` with `X-API-Key` header.</div>
                <div>2. FastAPI middleware validates tenant schema and JWT token (`src/api/auth.py`).</div>
                <div>3. Action Sentinel (`src/security/action_sentinel.py`) inspects target URL and DOM prompt scope.</div>
                <div>4. Celery broker queues task into `default`, `high_priority`, or `security_scan` Redis queues.</div>
                <div>5. Worker executes action inside isolated browser sandbox and streams real-time SSE updates (`/events/stream`).</div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="mt-6 space-y-6">
          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-white flex items-center gap-2">
                <ShieldCheck className="size-5 text-emerald-400" /> Action Sentinel & DOM Sanitization Lens
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Preventing MITRE ATT&CK T1566 phishing traps and prompt injections (`T1048` exfiltration).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 font-sans text-sm text-zinc-300 leading-relaxed">
              <p>
                When autonomous agents navigate websites, adversarial attackers can hide malicious instructions inside invisible DOM elements (`opacity: 0`, `font-size: 0px`, or `hidden` form fields) that instruct the LLM to ignore prior safety bounds.
              </p>
              <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs text-emerald-400">
                ✓ Implemented countermeasure: `ActionSentinel.sanitize_dom()` traverses incoming HTML/DOM trees, strips zero-visibility text nodes, and verifies MITRE ATT&CK compliance prior to agent execution.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="workers" className="mt-6 space-y-6">
          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-white flex items-center gap-2">
                <Cpu className="size-5 text-cyan-400" /> Distributed Celery Worker Clusters over Redis
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Async task queuing with dedicated priority separation (`src/workers/celery_app.py`).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 font-sans text-sm text-zinc-300 leading-relaxed">
              <p>
                Agent execution can involve lengthy browser automation tasks. To maintain high API concurrency, Agent Bastion delegates heavy tasks across distributed worker nodes (`abs-worker-agent` and `abs-worker-xai`).
              </p>
              <div className="grid sm:grid-cols-2 gap-4 font-mono text-xs">
                <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                  <span className="text-white font-bold block mb-1">`abs-worker-agent` Pool</span>
                  <span className="text-zinc-400 font-sans text-xs">Consumes `high_priority` and `default` queues for immediate browser DOM actions and task completion.</span>
                </div>
                <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800">
                  <span className="text-white font-bold block mb-1">`abs-worker-xai` Pool</span>
                  <span className="text-zinc-400 font-sans text-xs">Consumes `security_scan` queue for generating human-readable explainability logs (`XaiLogs`) asynchronously.</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api" className="mt-6 space-y-6">
          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-white flex items-center gap-2">
                <Server className="size-5 text-purple-400" /> Core API v1 Route Directory (`/api/v1/*`)
              </CardTitle>
              <CardDescription className="text-zinc-400">
                All routes enforced with OAuth2 / JWT bearer auth or proxy `X-API-Key` headers.
              </CardDescription>
            </CardHeader>
            <CardContent className="font-mono text-xs space-y-3">
              <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex justify-between items-center">
                <span className="text-emerald-400 font-bold">POST /api/v1/agents</span>
                <span className="text-zinc-400">Dispatch an autonomous task session</span>
              </div>
              <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex justify-between items-center">
                <span className="text-cyan-400 font-bold">GET /api/v1/dx/overview</span>
                <span className="text-zinc-400">Control plane overview & onboarding progress</span>
              </div>
              <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex justify-between items-center">
                <span className="text-cyan-400 font-bold">GET /api/v1/observability/health</span>
                <span className="text-zinc-400">Live subsystem component health checks</span>
              </div>
              <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex justify-between items-center">
                <span className="text-purple-400 font-bold">GET /api/v1/events/stream</span>
                <span className="text-zinc-400">Server-Sent Events (SSE) live telemetry feed</span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
