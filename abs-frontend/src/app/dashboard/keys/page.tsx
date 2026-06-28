'use client';

import * as React from 'react';
import { useAppStore } from '@/store/app-store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { KeyRound, Copy, Check, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

export default function KeysPage() {
  const { apiKey, tenantName } = useAppStore();
  const [showKey, setShowKey] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    if (!apiKey) return;
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    toast.success('API Key copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto h-full">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">API Credentials</h1>
        <p className="text-muted-foreground">
          Manage your organization's API keys for integrating the ABSs proxy into your autonomous agent deployments.
        </p>
      </div>

      <Card className="glass-panel border-cyan-900/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="size-5 text-cyan-500" /> Active API Key
          </CardTitle>
          <CardDescription>
            This key grants full access to the proxy engine and security APIs for <strong>{tenantName}</strong>. 
            Do not expose this key in client-side code.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <Label>Proxy API Key</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input 
                  value={apiKey || ''} 
                  type={showKey ? 'text' : 'password'}
                  readOnly
                  className="font-mono bg-zinc-900/50 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              <Button onClick={handleCopy} variant="secondary" className="w-24">
                {copied ? <Check className="size-4 mr-2 text-emerald-500" /> : <Copy className="size-4 mr-2" />}
                {copied ? 'Copied' : 'Copy'}
              </Button>
            </div>
          </div>

          <div className="rounded-lg bg-amber-950/30 border border-amber-900/50 p-4 mt-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="size-5 text-amber-500 mt-0.5 shrink-0" />
              <div>
                <h4 className="text-sm font-medium text-amber-500">Security Warning</h4>
                <p className="text-sm text-amber-200/70 mt-1">
                  This key provides full administrative access to your tenant policies and agent telemetry. 
                  Always inject it into your agents via environment variables or secure secret managers.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
        <CardFooter className="bg-zinc-900/30 border-t border-zinc-800 rounded-b-xl py-4 flex justify-between">
          <p className="text-sm text-muted-foreground">Key generated at account creation.</p>
          <Button variant="outline" className="text-destructive hover:text-destructive hover:bg-destructive/10">
            Roll API Key
          </Button>
        </CardFooter>
      </Card>

      <Card className="glass">
        <CardHeader>
          <CardTitle>Integration Examples</CardTitle>
          <CardDescription>How to configure your agents to route through the ABSs proxy.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="text-sm font-medium mb-2">Python (LangChain / Playwright)</h4>
            <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 font-mono text-sm overflow-x-auto text-zinc-300">
              <span className="text-purple-400">import</span> os<br/>
              <span className="text-purple-400">from</span> abs_sdk <span className="text-purple-400">import</span> SecureProxy<br/>
              <br/>
              <span className="text-zinc-500"># Initialize the proxy with your API key</span><br/>
              proxy = SecureProxy(api_key=os.environ[<span className="text-green-400">"ABS_API_KEY"</span>])<br/>
              <br/>
              <span className="text-zinc-500"># Connect your agent's browser to the secure proxy</span><br/>
              browser = await playwright.chromium.launch(<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;proxy=proxy.get_connection_settings()<br/>
              )<br/>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
