import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Shield, Lock, Eye, CheckCircle2, Terminal, Code, Cpu, Layers, Server, Activity, ArrowRight, Network, FileCode2, Play } from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 font-sans antialiased">
      {/* Infrastructure Header / Control Plane Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-xl">
        <div className="container mx-auto flex h-16 items-center justify-between px-6 lg:px-12">
          <div className="flex items-center gap-3">
            <div className="flex aspect-square size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
              <Shield className="size-5" />
            </div>
            <div className="flex flex-col leading-none">
              <span className="text-lg font-extrabold tracking-tight text-white">Agent Bastion</span>
              <span className="text-[10px] font-mono font-bold uppercase text-primary tracking-widest mt-0.5">Control Plane</span>
            </div>
          </div>

          <nav className="hidden xl:flex items-center gap-7 text-xs font-mono font-semibold text-zinc-400">
            <Link href="#features" className="hover:text-white transition-colors">01 / Features</Link>
            <Link href="#architecture" className="hover:text-white transition-colors">02 / Architecture</Link>
            <Link href="#quickstart" className="hover:text-white transition-colors">03 / Quickstart</Link>
            <Link href="#deployments" className="hover:text-white transition-colors">04 / Deployment Modes</Link>
            <Link href="#sdk-cli" className="hover:text-white transition-colors">05 / SDK & CLI</Link>
            <Link href="/dashboard/docs" className="hover:text-white transition-colors">06 / Docs</Link>
          </nav>

          <div className="flex items-center gap-4">
            <Link href="/login" className="text-xs font-mono font-bold text-zinc-300 hover:text-white transition-colors">
              Sign In →
            </Link>
            <Link href="/dashboard/overview">
              <Button className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-semibold px-5 shadow-lg shadow-primary/20 text-xs">
                Launch Dashboard
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* 1. HERO SECTION */}
      <section className="relative pt-24 pb-20 border-b border-zinc-900 overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:32px_32px]"></div>
        <div className="absolute left-1/2 top-10 -z-10 -translate-x-1/2 h-[450px] w-[800px] rounded-full bg-primary/15 blur-[140px] pointer-events-none"></div>

        <div className="container mx-auto px-6 lg:px-12 relative z-10 text-center max-w-5xl">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-primary/20 border border-primary/30 text-primary text-xs font-mono font-bold mb-8 shadow-sm">
            <Activity className="size-3.5 animate-pulse" /> PRODUCTION INFRASTRUCTURE FOR AUTONOMOUS AI AGENTS
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Deploy & Secure Autonomous Agents Without Infrastructure Risk.
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-zinc-300 max-w-3xl mx-auto leading-relaxed">
            Agent Bastion is <span className="text-white font-bold underline decoration-primary decoration-2">NOT a chatbot</span> or an AI assistant. It is a multi-tenant zero-trust security proxy that intercepts, verifies, and audits LLM agent network traffic in real-time.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link href="/dashboard/overview">
              <Button size="lg" className="rounded-xl px-8 py-7 bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-base shadow-xl shadow-primary/25">
                Open Control Plane Dashboard <ArrowRight className="ml-2.5 h-5 w-5" />
              </Button>
            </Link>
            <Link href="#quickstart">
              <Button size="lg" variant="outline" className="rounded-xl px-8 py-7 border-zinc-700 hover:bg-zinc-900 text-zinc-200 font-bold text-base">
                <Terminal className="mr-2.5 h-5 w-5 text-primary" /> 3-Minute Quickstart
              </Button>
            </Link>
          </div>

          <div className="mt-14 pt-8 border-t border-zinc-900/80 grid grid-cols-2 md:grid-cols-4 gap-6 text-left font-mono text-xs text-zinc-400">
            <div>
              <span className="text-zinc-500 block text-[10px]">THREAT INSPECTION</span>
              <span className="text-white font-bold text-sm">Real-time DOM & Prompt Lens</span>
            </div>
            <div>
              <span className="text-zinc-500 block text-[10px]">TENANT ISOLATION</span>
              <span className="text-white font-bold text-sm">PostgreSQL + pgvector RBAC</span>
            </div>
            <div>
              <span className="text-zinc-500 block text-[10px]">QUEUING & WORKERS</span>
              <span className="text-white font-bold text-sm">Celery Cluster over Redis</span>
            </div>
            <div>
              <span className="text-zinc-500 block text-[10px]">DEPLOYMENT PARITY</span>
              <span className="text-white font-bold text-sm">Local Dev == Production Mode</span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. FEATURES SECTION */}
      <section id="features" className="py-24 border-b border-zinc-900 bg-zinc-950/80">
        <div className="container mx-auto px-6 lg:px-12">
          <div className="max-w-2xl mb-16">
            <span className="text-xs font-mono font-bold text-primary uppercase tracking-widest">01 / Implemented Capabilities</span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white mt-2">
              Architected for Zero-Trust AI Execution.
            </h2>
            <p className="mt-3 text-zinc-400 text-base">
              Every feature below corresponds directly to implemented backend services (`src/security`, `src/workers`, `src/api`).
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <div className="p-7 rounded-2xl bg-zinc-900/60 border border-zinc-800 hover:border-primary/50 transition-all">
              <div className="size-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-5 font-bold">
                <Eye className="size-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Action Sentinel & DOM Lens</h3>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
                Inspects browser interactions, strips invisible adversarial instructions, and prevents malicious credential dumping or form submissions before execution.
              </p>
              <div className="mt-4 pt-4 border-t border-zinc-800/80 font-mono text-xs text-emerald-400">
                ✓ Implemented in `src/security/action_sentinel.py`
              </div>
            </div>

            <div className="p-7 rounded-2xl bg-zinc-900/60 border border-zinc-800 hover:border-primary/50 transition-all">
              <div className="size-12 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center mb-5 font-bold">
                <Cpu className="size-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Distributed Worker Cluster</h3>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
                Asynchronous Celery workers handle heavy DOM explainability (`XAI Worker`) and deep inspection tasks without blocking high-priority proxy calls.
              </p>
              <div className="mt-4 pt-4 border-t border-zinc-800/80 font-mono text-xs text-cyan-400">
                ✓ Implemented in `src/workers/celery_app.py`
              </div>
            </div>

            <div className="p-7 rounded-2xl bg-zinc-900/60 border border-zinc-800 hover:border-primary/50 transition-all">
              <div className="size-12 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center mb-5 font-bold">
                <Lock className="size-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Multi-Tenant RBAC & Quotas</h3>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
                Strict PostgreSQL row-level and middleware tenant separation (`TenantTier.FREE`, `PRO`, `ENTERPRISE`) with per-namespace rate limits and scopes.
              </p>
              <div className="mt-4 pt-4 border-t border-zinc-800/80 font-mono text-xs text-purple-400">
                ✓ Implemented in `src/api/auth.py`
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. ARCHITECTURE SECTION */}
      <section id="architecture" className="py-24 border-b border-zinc-900">
        <div className="container mx-auto px-6 lg:px-12">
          <div className="max-w-2xl mb-16">
            <span className="text-xs font-mono font-bold text-primary uppercase tracking-widest">02 / System Topology</span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white mt-2">
              Transparent Proxy Inspection Pipeline.
            </h2>
            <p className="mt-3 text-zinc-400 text-base">
              Agent requests pass through Caddy reverse proxy into our FastAPI engine, where real-time security policies evaluate each action.
            </p>
          </div>

          <div className="p-8 rounded-2xl bg-zinc-900/50 border border-zinc-800 font-mono text-xs">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6 text-center">
              <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 w-full md:w-1/5">
                <div className="text-primary font-bold text-sm mb-1">Agent Client</div>
                <div className="text-[11px] text-zinc-400">Python / JS SDK / CLI</div>
              </div>
              <div className="text-zinc-600 font-bold">→ HTTP Proxy →</div>
              <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 w-full md:w-1/5">
                <div className="text-white font-bold text-sm mb-1">Caddy Proxy</div>
                <div className="text-[11px] text-zinc-400">Automatic TLS & Ports</div>
              </div>
              <div className="text-zinc-600 font-bold">→ Inspect →</div>
              <div className="p-5 rounded-xl bg-primary/10 border border-primary/40 w-full md:w-1/4">
                <div className="text-primary font-bold text-sm mb-1">FastAPI Security Gateway</div>
                <div className="text-[11px] text-zinc-300">Action Sentinel + RBAC</div>
              </div>
              <div className="text-zinc-600 font-bold">→ Dispatch →</div>
              <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 w-full md:w-1/5">
                <div className="text-cyan-400 font-bold text-sm mb-1">Redis & Celery</div>
                <div className="text-[11px] text-zinc-400">Async Workers & DB Store</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. QUICK START SECTION */}
      <section id="quickstart" className="py-24 border-b border-zinc-900 bg-zinc-950">
        <div className="container mx-auto px-6 lg:px-12">
          <div className="max-w-2xl mb-16">
            <span className="text-xs font-mono font-bold text-primary uppercase tracking-widest">03 / Quickstart</span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white mt-2">
              Connect Your Autonomous Agent in Under 3 Minutes.
            </h2>
            <p className="mt-3 text-zinc-400 text-base">
              Use standard HTTP requests or the Agent Bastion SDK to route agent actions through the security proxy.
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            <div className="rounded-2xl bg-zinc-900 border border-zinc-800 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800 bg-zinc-950 font-mono text-xs text-zinc-400">
                <span>cURL Direct API Proxy</span>
                <span className="text-emerald-400 font-bold">HTTP/1.1 200 OK</span>
              </div>
              <pre className="p-6 text-xs font-mono text-zinc-300 overflow-x-auto leading-relaxed">
{`curl -X POST "http://localhost:8000/api/v1/agents" \\
  -H "X-API-Key: <YOUR_API_KEY>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "task_prompt": "Audit corporate portal for security vulnerabilities",
    "target_url": "https://example.com/login",
    "priority": 5
  }'`}
              </pre>
            </div>

            <div className="rounded-2xl bg-zinc-900 border border-zinc-800 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800 bg-zinc-950 font-mono text-xs text-zinc-400">
                <span>Python SDK Example (`pip install agent-bastion`)</span>
                <span className="text-cyan-400 font-bold">Python 3.11+</span>
              </div>
              <pre className="p-6 text-xs font-mono text-zinc-300 overflow-x-auto leading-relaxed">
{`from abss import AgentBastionClient

client = AgentBastionClient(
    api_key="<YOUR_API_KEY>",
    base_url="http://localhost:8000"
)

# Submit a secure agent task with real-time DOM inspection
task = client.agents.submit(
    prompt="Audit corporate portal for security vulnerabilities",
    target_url="https://example.com/login"
)
print(f"Dispatched Session: {task.session_id}")`}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* 5. DEPLOYMENT MODES SECTION */}
      <section id="deployments" className="py-24 border-b border-zinc-900 bg-zinc-900/30">
        <div className="container mx-auto px-6 lg:px-12">
          <div className="max-w-3xl mb-16">
            <span className="text-xs font-mono font-bold text-primary uppercase tracking-widest">04 / Deployment Parity</span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white mt-2">
              Exact Identical Architecture in Local Dev & Production.
            </h2>
            <p className="mt-3 text-zinc-400 text-base">
              There is only ONE product: Agent Bastion. No stripped-down community editions or mock architectures.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="p-8 rounded-2xl bg-zinc-900 border border-zinc-800 flex flex-col justify-between">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 font-mono text-xs font-bold mb-4">
                  LOCAL DEVELOPMENT MODE
                </div>
                <h3 className="text-2xl font-extrabold text-white">Full-Stack Sandbox</h3>
                <p className="mt-2 text-sm text-zinc-400">
                  Runs real JWT Auth, RBAC, Celery workers, PostgreSQL, and observability engines locally without external cloud dependencies.
                </p>
                
                <div className="mt-6 space-y-2.5 font-mono text-xs text-zinc-300">
                  <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>JWT Auth & Refresh Token Rotation</span></div>
                  <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Multi-Tenant Namespaces & API Keys</span></div>
                  <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Celery Workers & Redis Queue</span></div>
                  <div className="flex items-center gap-2 text-zinc-500"><span>✕ HTTPS / TLS / Cloudflare Domain (Disabled locally)</span></div>
                </div>
              </div>

              <div className="mt-8 pt-5 border-t border-zinc-800">
                <span className="text-xs font-mono text-zinc-500 block mb-2">RUN COMMAND:</span>
                <code className="bg-black/60 px-3.5 py-2.5 rounded-lg text-xs font-mono text-cyan-400 block border border-zinc-800">
                  docker compose -f docker-compose.dev.yml up --build
                </code>
              </div>
            </div>

            <div className="p-8 rounded-2xl bg-zinc-900 border border-primary/40 flex flex-col justify-between relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-primary text-primary-foreground px-4 py-1 text-xs font-mono font-bold rounded-bl-xl">
                PRODUCTION READY
              </div>
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/15 text-primary font-mono text-xs font-bold mb-4">
                  PRODUCTION MODE
                </div>
                <h3 className="text-2xl font-extrabold text-white">Zero-Trust Cloud Gateway</h3>
                <p className="mt-2 text-sm text-zinc-400">
                  Enables HTTPS, TLS, automatic Caddy routing, and enterprise WAF rules on top of our exact local core engine.
                </p>
                
                <div className="mt-6 space-y-2.5 font-mono text-xs text-zinc-300">
                  <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>HTTPS, TLS & Domain WAF Enabled</span></div>
                  <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Multi-Tenant Namespaces & API Keys</span></div>
                  <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Distributed Celery Workers & Telemetry</span></div>
                  <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400" /> <span>Immutable Audit Trail & Prometheus Export</span></div>
                </div>
              </div>

              <div className="mt-8 pt-5 border-t border-zinc-800">
                <span className="text-xs font-mono text-zinc-500 block mb-2">RUN COMMAND:</span>
                <code className="bg-black/60 px-3.5 py-2.5 rounded-lg text-xs font-mono text-emerald-400 block border border-zinc-800">
                  docker compose up --build
                </code>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. SECURITY FEATURES SECTION */}
      <section id="security" className="py-24 border-b border-zinc-900">
        <div className="container mx-auto px-6 lg:px-12">
          <div className="max-w-2xl mb-16">
            <span className="text-xs font-mono font-bold text-primary uppercase tracking-widest">05 / Security Safeguards</span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white mt-2">
              Action Sentinel Threat Inspection Matrix.
            </h2>
          </div>

          <div className="grid md:grid-cols-4 gap-6 font-mono text-xs">
            <div className="p-6 rounded-xl bg-zinc-900/70 border border-zinc-800">
              <span className="text-red-400 font-bold text-sm block mb-2">MITRE ATT&CK T1566</span>
              <p className="text-zinc-400 leading-relaxed font-sans">Detects and blocks phishing payloads and adversarial credential harvesting attempts embedded inside DOM elements.</p>
            </div>
            <div className="p-6 rounded-xl bg-zinc-900/70 border border-zinc-800">
              <span className="text-orange-400 font-bold text-sm block mb-2">Prompt Injection Shield</span>
              <p className="text-zinc-400 leading-relaxed font-sans">Strips invisible text (`font-size: 0`, `opacity: 0`) and hidden instructions intended to hijack LLM behavior.</p>
            </div>
            <div className="p-6 rounded-xl bg-zinc-900/70 border border-zinc-800">
              <span className="text-amber-400 font-bold text-sm block mb-2">Credential Protection</span>
              <p className="text-zinc-400 leading-relaxed font-sans">Blocks agents from submitting private API tokens or company secrets to untrusted third-party domains.</p>
            </div>
            <div className="p-6 rounded-xl bg-zinc-900/70 border border-zinc-800">
              <span className="text-emerald-400 font-bold text-sm block mb-2">XAI Explainability</span>
              <p className="text-zinc-400 leading-relaxed font-sans">Generates clear human-readable explanations (`XaiLogs`) for every security block directly in the audit trail.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 7. SDK & CLI SECTION */}
      <section id="sdk-cli" className="py-24 border-b border-zinc-900 bg-zinc-950">
        <div className="container mx-auto px-6 lg:px-12">
          <div className="max-w-2xl mb-16">
            <span className="text-xs font-mono font-bold text-primary uppercase tracking-widest">06 / Developer Tools</span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white mt-2">
              Supported SDK & Command-Line Tools.
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="p-8 rounded-2xl bg-zinc-900 border border-zinc-800">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <Code className="size-5 text-primary" /> Python & JS SDK
                </h3>
                <span className="text-xs font-mono text-zinc-500">v2.0.0</span>
              </div>
              <p className="text-sm text-zinc-400 mb-6">
                Direct integration into LangChain, AutoGen, CrewAI, or custom OpenAI tool loop agents.
              </p>
              <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs text-zinc-300 space-y-2">
                <div className="text-emerald-400">$ pip install agent-bastion</div>
                <div className="text-cyan-400">$ npm install @abss/sdk</div>
              </div>
            </div>

            <div className="p-8 rounded-2xl bg-zinc-900 border border-zinc-800">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <Terminal className="size-5 text-cyan-400" /> CLI Tool (`agent-bastion`)
                </h3>
                <span className="text-xs font-mono text-zinc-500">CLI v2.0</span>
              </div>
              <p className="text-sm text-zinc-400 mb-6">
                Initialize configurations, deploy local or prod clusters, and inspect live queue health right from your shell.
              </p>
              <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs text-zinc-300 space-y-2">
                <div className="text-emerald-400">$ agent-bastion init</div>
                <div className="text-emerald-400">$ agent-bastion deploy --mode production</div>
                <div className="text-zinc-500">$ agent-bastion version</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 8. DOCUMENTATION & DASHBOARD PREVIEW SECTION */}
      <section className="py-24 border-b border-zinc-900 bg-zinc-900/40">
        <div className="container mx-auto px-6 lg:px-12 text-center max-w-4xl">
          <h2 className="text-3xl font-extrabold text-white">
            Ready to Inspect & Secure Your Autonomous Agents?
          </h2>
          <p className="mt-4 text-zinc-400 text-lg">
            Access the complete production control plane or explore our OpenAPI `/docs` specification.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <Link href="/dashboard/overview">
              <Button size="lg" className="rounded-xl px-8 py-7 bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-base shadow-xl">
                Open Dashboard <ArrowRight className="ml-2.5 h-5 w-5" />
              </Button>
            </Link>
            <Link href="/dashboard/docs">
              <Button size="lg" variant="outline" className="rounded-xl px-8 py-7 border-zinc-700 hover:bg-zinc-900 text-zinc-200 font-bold text-base">
                <FileCode2 className="mr-2.5 h-5 w-5 text-primary" /> View API & System Docs
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-zinc-900 bg-zinc-950 text-center text-xs font-mono text-zinc-500">
        <div className="flex items-center justify-center gap-2 mb-3 text-white font-bold text-sm">
          <Shield className="size-4 text-primary" /> Agent Bastion Control Plane
        </div>
        <p>Production Infrastructure for Autonomous AI Agents. © {new Date().getFullYear()}</p>
      </footer>
    </main>
  );
}
