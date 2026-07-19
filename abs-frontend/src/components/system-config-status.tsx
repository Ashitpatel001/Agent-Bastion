import * as React from 'react';
import { useLlmStatus } from '@/hooks/use-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, AlertCircle, Database, Server, Cpu, Globe, Key, Settings2, RefreshCw } from 'lucide-react';

export function SystemConfigStatus() {
  const { data: status, isLoading, refetch } = useLlmStatus();
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  if (isLoading) return null;

  const isReady = status?.ready;

  return (
    <Card className="bg-zinc-950/60 border-zinc-800 shadow-xl overflow-hidden">
      <div className={`h-1 w-full ${isReady ? 'bg-emerald-500' : 'bg-red-500 animate-pulse'}`} />
      <CardHeader className="pb-4">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-lg font-semibold flex items-center gap-2 text-white">
              <Settings2 className="size-5 text-zinc-400" /> System Configuration
            </CardTitle>
            <CardDescription>
              Production backend status and LLM configuration
            </CardDescription>
          </div>
          <Button variant="ghost" size="icon" onClick={handleRefresh} disabled={isRefreshing} className="size-8">
            <RefreshCw className={`size-4 text-zinc-400 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        
        {/* Core Infrastructure */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="flex flex-col gap-1 p-3 bg-zinc-900/50 rounded-lg border border-zinc-800">
            <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-500 uppercase tracking-wider">
              <Database className="size-3" /> Database
            </div>
            <div className="flex items-center gap-1.5 text-sm font-medium text-emerald-400">
              <CheckCircle2 className="size-4" /> RUNNING
            </div>
          </div>
          <div className="flex flex-col gap-1 p-3 bg-zinc-900/50 rounded-lg border border-zinc-800">
            <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-500 uppercase tracking-wider">
              <Server className="size-3" /> Redis
            </div>
            <div className="flex items-center gap-1.5 text-sm font-medium text-emerald-400">
              <CheckCircle2 className="size-4" /> RUNNING
            </div>
          </div>
          <div className="flex flex-col gap-1 p-3 bg-zinc-900/50 rounded-lg border border-zinc-800">
            <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-500 uppercase tracking-wider">
              <Cpu className="size-3" /> Workers
            </div>
            <div className="flex items-center gap-1.5 text-sm font-medium text-emerald-400">
              <CheckCircle2 className="size-4" /> RUNNING
            </div>
          </div>
          <div className="flex flex-col gap-1 p-3 bg-zinc-900/50 rounded-lg border border-zinc-800">
            <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-500 uppercase tracking-wider">
              <Globe className="size-3" /> API Gateway
            </div>
            <div className="flex items-center gap-1.5 text-sm font-medium text-emerald-400">
              <CheckCircle2 className="size-4" /> RUNNING
            </div>
          </div>
          <div className="flex flex-col gap-1 p-3 bg-zinc-900/50 rounded-lg border border-zinc-800 md:col-span-4">
            <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-500 uppercase tracking-wider">
              <Globe className="size-3" /> Browser Runtime
            </div>
            <div className="flex items-center gap-1.5 text-sm font-medium text-emerald-400">
              <CheckCircle2 className="size-4" /> RUNNING
            </div>
          </div>
        </div>

        {/* LLM Provider Configuration */}
        <div className="space-y-4 pt-4 border-t border-zinc-800">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-300">LLM API Keys</h3>
            {!isReady ? (
              <span className="flex items-center gap-1 text-xs font-bold text-red-500 bg-red-500/10 px-2 py-1 rounded">
                <AlertCircle className="size-3" /> NOT CONFIGURED
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded">
                <CheckCircle2 className="size-3" /> CONFIGURED
              </span>
            )}
          </div>
          
          <div className="grid gap-3">
            <div className="flex items-center justify-between p-3 bg-zinc-900/40 rounded-lg border border-zinc-800">
              <div className="flex items-center gap-2">
                <Key className="size-4 text-zinc-400" />
                <span className="text-sm font-medium text-zinc-200">Gemini API Key</span>
              </div>
              {status?.providers?.gemini?.configured ? (
                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1"><CheckCircle2 className="size-3"/> CONFIGURED</span>
              ) : (
                <span className="text-xs font-bold text-zinc-500">NOT CONFIGURED</span>
              )}
            </div>

            <div className="flex items-center justify-between p-3 bg-zinc-900/40 rounded-lg border border-zinc-800">
              <div className="flex items-center gap-2">
                <Key className="size-4 text-zinc-400" />
                <span className="text-sm font-medium text-zinc-200">OpenAI API Key</span>
              </div>
              {status?.providers?.openai?.configured ? (
                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1"><CheckCircle2 className="size-3"/> CONFIGURED</span>
              ) : (
                <span className="text-xs font-bold text-zinc-500">NOT CONFIGURED</span>
              )}
            </div>

            <div className="flex items-center justify-between p-3 bg-zinc-900/40 rounded-lg border border-zinc-800">
              <div className="flex items-center gap-2">
                <Key className="size-4 text-zinc-400" />
                <span className="text-sm font-medium text-zinc-200">Groq API Key</span>
              </div>
              {status?.providers?.groq?.configured ? (
                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1"><CheckCircle2 className="size-3"/> CONFIGURED</span>
              ) : (
                <span className="text-xs font-bold text-zinc-500">NOT CONFIGURED</span>
              )}
            </div>
          </div>
          
          {!isReady && (
            <div className="mt-4 bg-red-950/20 p-4 rounded-lg border border-red-900/30">
              <h4 className="text-sm font-bold text-red-400 mb-2 flex items-center gap-2">
                <AlertCircle className="size-4" /> How to Configure
              </h4>
              <ol className="list-decimal list-inside space-y-2 text-xs text-red-300/80 font-mono ml-1">
                <li>Add <span className="text-red-300 font-semibold bg-red-900/40 px-1 py-0.5 rounded">GEMINI_API_KEY</span> (Recommended) or another provider key to your <span className="text-red-300 font-semibold bg-red-900/40 px-1 py-0.5 rounded">.env</span> file</li>
                <li>Restart the Docker deployment (<span className="text-red-300 font-semibold bg-red-900/40 px-1 py-0.5 rounded">docker compose restart</span>)</li>
                <li>Click <span className="text-red-300 font-semibold cursor-pointer underline hover:text-red-200" onClick={handleRefresh}>Refresh Configuration</span></li>
              </ol>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
