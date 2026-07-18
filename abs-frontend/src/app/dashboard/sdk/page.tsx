'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/store/app-store';
import { Code, Copy, Check, Terminal, ShieldCheck, ArrowRight, Play, BookOpen } from 'lucide-react';
import { toast } from 'sonner';

export default function SdkPage() {
  const { apiKey, tenantName } = useAppStore();
  const [copiedSection, setCopiedSection] = React.useState<string | null>(null);
  const [selectedLang, setSelectedLang] = React.useState<'python' | 'js' | 'curl'>('python');

  const activeToken = apiKey || 'abs_live_demo_key_12345';

  const copyText = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(id);
    toast.success('Snippet copied to clipboard!');
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const pythonSnippet = `from abss import AgentBastionClient

# Initialize secure client for tenant: ${tenantName || 'Enterprise'}
client = AgentBastionClient(
    api_key="${activeToken}",
    base_url="http://localhost:8000"
)

# Submit an autonomous agent task with DOM sanitization
session = client.agents.submit(
    prompt="Audit financial portal for security compliance",
    target_url="https://portal.acme.corp/login",
    priority=8
)

print(f"Session Dispatched: {session.session_id}")
print(f"Status: {session.status}")`;

  const jsSnippet = `import { AgentBastionClient } from '@abss/sdk';

// Initialize secure client for tenant: ${tenantName || 'Enterprise'}
const client = new AgentBastionClient({
  apiKey: '${activeToken}',
  baseUrl: 'http://localhost:8000'
});

async function runSecureAgent() {
  const session = await client.agents.submit({
    prompt: 'Audit financial portal for security compliance',
    targetUrl: 'https://portal.acme.corp/login',
    priority: 8
  });

  console.log('Session Dispatched:', session.sessionId);
}

runSecureAgent();`;

  const curlSnippet = `curl -X POST "http://localhost:8000/api/v1/agents" \\
  -H "X-API-Key: ${activeToken}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "task_prompt": "Audit financial portal for security compliance",
    "target_url": "https://portal.acme.corp/login",
    "priority": 8
  }'`;

  return (
    <div className="flex flex-col gap-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1 max-w-4xl">
          <h1 className="text-3xl font-bold tracking-tight uppercase flex items-center gap-2 text-white">
            <Code className="size-6 text-primary" /> SDK & CODE GENERATOR
          </h1>
          <p className="text-sm text-zinc-400">Interactive integration snippets pre-injected with your live proxy credentials.</p>
          
          <div className="flex flex-wrap gap-3 mt-3 font-mono text-xs text-zinc-300">
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800">
              [ Supported: Python, Node.js, cURL ]
            </span>
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800 flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
              [ Credentials Auto-Injected ]
            </span>
          </div>

          <details className="mt-4 group cursor-pointer">
            <summary className="text-xs font-semibold text-primary hover:underline list-none inline-flex items-center gap-1">
              Learn how the SDK works <span className="group-open:rotate-90 transition-transform">&gt;</span>
            </summary>
            <div className="mt-3 p-4 rounded-xl border border-primary/20 bg-primary/5 text-xs text-zinc-300 leading-relaxed max-w-2xl">
              The SDK is your programmatic bridge to the Agent-Bastion control plane. It automatically handles secure <strong className="text-white font-mono">Proxy Authentication</strong>, <strong className="text-white font-mono">SSE Telemetry Parsing</strong>, and automated queue routing so you can focus entirely on your AI agent logic.
            </div>
          </details>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 flex flex-col justify-between">
          <CardHeader>
            <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
              <Terminal className="size-5 text-cyan-400" /> 1. Install Client SDK
            </CardTitle>
            <CardDescription className="text-zinc-400">Official library releases for Python & Node.js</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 font-mono text-xs">
            <div>
              <span className="text-zinc-400 block mb-1">Python Package (`pip`)</span>
              <div className="flex items-center justify-between p-3 rounded-xl bg-zinc-950 border border-zinc-800">
                <span className="text-emerald-400 font-bold">$ pip install agent-bastion</span>
                <Button size="sm" variant="ghost" onClick={() => copyText('pip install agent-bastion', 'pip')} className="h-6 px-2 text-zinc-400 hover:text-white">
                  {copiedSection === 'pip' ? <Check className="size-3 text-emerald-400" /> : <Copy className="size-3" />}
                </Button>
              </div>
            </div>

            <div>
              <span className="text-zinc-400 block mb-1">Node.js / TypeScript (`npm`)</span>
              <div className="flex items-center justify-between p-3 rounded-xl bg-zinc-950 border border-zinc-800">
                <span className="text-cyan-400 font-bold">$ npm install @abss/sdk</span>
                <Button size="sm" variant="ghost" onClick={() => copyText('npm install @abss/sdk', 'npm')} className="h-6 px-2 text-zinc-400 hover:text-white">
                  {copiedSection === 'npm' ? <Check className="size-3 text-emerald-400" /> : <Copy className="size-3" />}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-2 glass-panel bg-zinc-900/60 border-zinc-800 flex flex-col justify-between">
          <CardHeader className="pb-3 border-b border-zinc-800/80">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <CardTitle className="text-lg font-bold text-white">2. Interactive Code Generator</CardTitle>
                <CardDescription className="text-zinc-400">Code snippet auto-configured with your tenant key</CardDescription>
              </div>
              <div className="flex items-center gap-2 bg-zinc-950 p-1 rounded-xl border border-zinc-800 font-mono text-xs">
                <button
                  onClick={() => setSelectedLang('python')}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-all ${selectedLang === 'python' ? 'bg-primary text-white' : 'text-zinc-400 hover:text-white'}`}
                >
                  Python
                </button>
                <button
                  onClick={() => setSelectedLang('js')}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-all ${selectedLang === 'js' ? 'bg-primary text-white' : 'text-zinc-400 hover:text-white'}`}
                >
                  Node / TS
                </button>
                <button
                  onClick={() => setSelectedLang('curl')}
                  className={`px-3 py-1.5 rounded-lg font-bold transition-all ${selectedLang === 'curl' ? 'bg-primary text-white' : 'text-zinc-400 hover:text-white'}`}
                >
                  cURL
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-4 relative">
            <pre className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 font-mono text-xs text-zinc-300 overflow-x-auto leading-relaxed max-h-[340px]">
              {selectedLang === 'python' ? pythonSnippet : selectedLang === 'js' ? jsSnippet : curlSnippet}
            </pre>
            <div className="absolute top-7 right-6">
              <Button
                size="sm"
                onClick={() => copyText(selectedLang === 'python' ? pythonSnippet : selectedLang === 'js' ? jsSnippet : curlSnippet, 'code')}
                className="bg-zinc-800 hover:bg-zinc-700 text-white font-sans text-xs"
              >
                {copiedSection === 'code' ? <Check className="mr-1.5 size-3.5 text-emerald-400" /> : <Copy className="mr-1.5 size-3.5" />}
                {copiedSection === 'code' ? 'Copied Snippet' : 'Copy Code'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
