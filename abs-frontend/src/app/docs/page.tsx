import React from 'react';
import Link from 'next/link';
import { Shield, BookOpen, Settings, AlertTriangle, Eye, ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function DocsPage() {
  return (
    <main className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur">
        <div className="container mx-auto flex h-16 items-center px-4">
          <Link href="/">
            <Button variant="ghost" size="sm" className="gap-2">
              <ChevronLeft className="size-4" /> Back to Home
            </Button>
          </Link>
          <div className="flex-1 flex justify-center">
            <div className="flex items-center gap-2">
              <Shield className="size-5 text-primary" />
              <span className="text-xl font-bold tracking-tight">ABSs Docs</span>
            </div>
          </div>
          <div className="w-[110px]"></div> {/* Spacer for centering */}
        </div>
      </header>

      <div className="container mx-auto px-4 py-12 max-w-4xl">
        <div className="mb-12">
          <h1 className="text-4xl font-extrabold tracking-tight mb-4">Documentation</h1>
          <p className="text-xl text-muted-foreground">
            Learn how to integrate ABSs with your autonomous agents and secure your AI deployments.
          </p>
        </div>

        <div className="space-y-16">
          {/* Quick Start */}
          <section>
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-primary/10 rounded-lg text-primary">
                <BookOpen className="size-6" />
              </div>
              <h2 className="text-3xl font-bold">Quick Start Guide</h2>
            </div>
            <div className="prose prose-invert max-w-none">
              <p className="text-muted-foreground text-lg mb-4">
                To start protecting your agent, you need to configure it to route all HTTP and WebSocket requests through the ABSs Proxy.
              </p>
              <div className="bg-zinc-950 p-6 rounded-xl border border-zinc-800">
                <h3 className="text-lg font-semibold mb-2 text-foreground">1. Obtain your API Key</h3>
                <p className="text-muted-foreground mb-4">Log in to the dashboard and navigate to Settings to generate your Tenant API Key.</p>
                
                <h3 className="text-lg font-semibold mb-2 text-foreground">2. Configure your Agent Environment</h3>
                <p className="text-muted-foreground mb-4">Set the following environment variables in your agent's execution environment:</p>
                <pre className="bg-black/50 p-4 rounded-lg text-sm text-zinc-300 font-mono overflow-x-auto">
                  HTTP_PROXY=http://proxy.abs-security.com:8080<br/>
                  HTTPS_PROXY=http://proxy.abs-security.com:8080<br/>
                  ABS_API_KEY=your_tenant_api_key
                </pre>
              </div>
            </div>
          </section>

          {/* Using the Dashboard */}
          <section>
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-primary/10 rounded-lg text-primary">
                <Eye className="size-6" />
              </div>
              <h2 className="text-3xl font-bold">Using the Live Dashboard</h2>
            </div>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-zinc-900/50 p-6 rounded-xl border border-zinc-800">
                <h3 className="text-lg font-semibold mb-2">Live Security Feed</h3>
                <p className="text-muted-foreground">
                  The Live Feed displays real-time telemetry from your agents. Events update automatically without needing to refresh the page.
                  You can see exactly what URLs your agents are visiting and whether any prompt injections were detected in the DOM.
                </p>
              </div>
              <div className="bg-zinc-900/50 p-6 rounded-xl border border-zinc-800">
                <h3 className="text-lg font-semibold mb-2">Expanding Event Details</h3>
                <p className="text-muted-foreground">
                  Click the downward chevron icon on the right side of any event in the feed to expand its JSON payload. 
                  This provides deep visibility into why an action was blocked and the exact payload that triggered the alert.
                </p>
              </div>
            </div>
          </section>

          {/* Policy Management */}
          <section>
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-primary/10 rounded-lg text-primary">
                <Settings className="size-6" />
              </div>
              <h2 className="text-3xl font-bold">Policy Management</h2>
            </div>
            <div className="prose prose-invert max-w-none">
              <p className="text-muted-foreground text-lg mb-6">
                ABSs uses a zero-trust model. By default, risky actions like executing arbitrary code or downloading unverified files are flagged.
              </p>
              <ul className="space-y-4 text-muted-foreground list-disc pl-6">
                <li><strong className="text-foreground">Allowlists:</strong> Explicitly define domains your agent is permitted to communicate with.</li>
                <li><strong className="text-foreground">Action Policies:</strong> Configure whether actions like `click`, `type`, or `submit_form` require explicit approval or are blocked outright.</li>
                <li><strong className="text-foreground">Data Exfiltration Prevention:</strong> ABSs automatically scrubs sensitive credentials (like AWS keys or credit card numbers) before the agent transmits them to third parties.</li>
              </ul>
            </div>
          </section>

          {/* Troubleshooting */}
          <section>
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-primary/10 rounded-lg text-primary">
                <AlertTriangle className="size-6" />
              </div>
              <h2 className="text-3xl font-bold">Troubleshooting (Logs not showing?)</h2>
            </div>
            <div className="bg-zinc-950 p-6 rounded-xl border border-zinc-800">
              <p className="text-muted-foreground mb-4">
                If the Live Security Feed is empty, ensure the following:
              </p>
              <ol className="space-y-3 text-muted-foreground list-decimal pl-6 marker:text-primary">
                <li>You are correctly authenticated (check if you are logged in).</li>
                <li>Your agent is actively running and making requests through the ABSs proxy.</li>
                <li>The API Key injected into your agent matches your account's API Key.</li>
              </ol>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
