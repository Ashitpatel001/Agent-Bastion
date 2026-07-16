'use client';

import React, { useEffect, useState } from 'react';
import { apiClient } from '@/services/api';
import { Code, Terminal, CheckCircle2, AlertTriangle, RefreshCw, Copy, Check } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default function DeveloperDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedTab, setCopiedTab] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'python_sdk' | 'javascript_sdk' | 'curl'>('python_sdk');

  const fetchQuickstart = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDxQuickstart();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load developer quickstart data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuickstart();
  }, []);

  const handleCopy = (code: string, tab: string) => {
    navigator.clipboard.writeText(code);
    setCopiedTab(tab);
    setTimeout(() => setCopiedTab(null), 2000);
  };

  const steps = data?.steps || [];
  const progress = data?.progress_percentage || 0;
  const examples = data?.code_examples || {};

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Code className="size-6 text-primary" />
            Developer SDK & Quickstart Portal
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            5-Minute interactive onboarding checklist and copy-paste SDK snippets generated directly for Tenant `{data?.tenant_name || 'Your Tenant'}`.
          </p>
        </div>
        <Button onClick={fetchQuickstart} variant="outline" size="sm" className="gap-2" disabled={loading}>
          <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Progress
        </Button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm flex items-center gap-3">
          <AlertTriangle className="size-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Progress Bar & Checklist */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <CheckCircle2 className="size-5 text-emerald-500" />
                5-Minute Onboarding Checklist
              </CardTitle>
              <CardDescription>Verify your tenant setup, API key generation, and first task dispatch.</CardDescription>
            </div>
            <Badge variant="outline" className="text-emerald-500 font-mono text-sm px-3 py-1">
              {progress}% Complete
            </Badge>
          </div>
          <div className="w-full bg-muted/60 h-2 rounded-full mt-3 overflow-hidden">
            <div 
              className="bg-primary h-full transition-all duration-500 ease-in-out" 
              style={{ width: `${progress}%` }} 
            />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="p-6 text-center text-muted-foreground text-sm">Inspecting onboarding checklist...</div>
          ) : (
            steps.map((step: any, idx: number) => (
              <div key={idx} className="flex items-start justify-between p-3.5 rounded-lg border bg-card gap-4">
                <div className="flex items-start gap-3.5">
                  <div className={`mt-0.5 p-1.5 rounded-full ${step.completed ? 'bg-emerald-500/10 text-emerald-500' : 'bg-muted text-muted-foreground'}`}>
                    <CheckCircle2 className="size-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">{step.title}</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">{step.description}</p>
                  </div>
                </div>
                <Badge variant={step.completed ? 'default' : 'secondary'} className="text-[11px]">
                  {step.completed ? 'Completed' : 'Pending'}
                </Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Interactive SDK Playground Snippets */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Terminal className="size-4 text-primary" />
            Interactive Code Generator (Copy & Paste Ready)
          </CardTitle>
          <CardDescription>
            These snippets are dynamically generated for your current tenant environment (`{apiClient['baseUrl']}`).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex border-b border-border gap-2 mb-4">
            <Button
              variant={activeTab === 'python_sdk' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab('python_sdk')}
              className="text-xs"
            >
              Python SDK
            </Button>
            <Button
              variant={activeTab === 'javascript_sdk' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab('javascript_sdk')}
              className="text-xs"
            >
              JavaScript / TypeScript SDK
            </Button>
            <Button
              variant={activeTab === 'curl' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab('curl')}
              className="text-xs"
            >
              cURL (Command Line)
            </Button>
          </div>

          <div className="relative rounded-lg bg-zinc-950 p-4 border border-zinc-800 text-zinc-100 font-mono text-xs overflow-x-auto">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => handleCopy(examples[activeTab] || '', activeTab)}
              className="absolute top-2 right-2 h-7 w-7 text-zinc-400 hover:text-white"
              title="Copy snippet"
            >
              {copiedTab === activeTab ? <Check className="size-3.5 text-emerald-400" /> : <Copy className="size-3.5" />}
            </Button>
            <pre className="pr-8">{examples[activeTab] || '# Loading SDK snippets...'}</pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
