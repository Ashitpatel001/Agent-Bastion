'use client';

import * as React from 'react';
import { useAppStore } from '@/store/app-store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { KeyRound, Copy, Check, Eye, EyeOff, AlertTriangle, RefreshCw, Plus, Trash2, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { useApiKeys, useCreateApiKey, useRotateApiKey, useRevokeApiKey } from '@/hooks/use-api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

export default function KeysPage() {
  const { apiKey, tenantName, setCredentials, tenantId, userEmail, tenantTier } = useAppStore();
  const { data: keysData, isLoading, refetch } = useApiKeys();
  const createKey = useCreateApiKey();
  const rotateKey = useRotateApiKey();
  const revokeKey = useRevokeApiKey();

  const [showKey, setShowKey] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [newKeyName, setNewKeyName] = React.useState('Production Agent Key');
  const [newKeyScope, setNewKeyScope] = React.useState('agents:write,observability:read');

  const keysList = keysData?.items || [];

  const handleCopy = (text?: string) => {
    const target = text || apiKey;
    if (!target) return;
    navigator.clipboard.writeText(target);
    setCopied(true);
    toast.success('API Key copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await createKey.mutateAsync({
        name: newKeyName,
        scopes: newKeyScope.split(',').map((s) => s.trim()),
      });
      toast.success('New API Key Generated!', {
        description: `Key prefix: ${res.prefix || res.api_key?.substring(0, 10) || 'abs_key_...'}. Store it securely.`,
      });
      setIsCreateOpen(false);
      refetch();
    } catch (err: any) {
      toast.error('Creation failed', { description: err.message || 'Error creating API key.' });
    }
  };

  const handleRotate = async (keyId: string) => {
    try {
      const res = await rotateKey.mutateAsync(keyId);
      if (res.new_api_key && tenantId && tenantName && userEmail && tenantTier) {
        setCredentials(tenantId, res.new_api_key, tenantName, userEmail, tenantTier);
      }
      toast.success('API Key Rotated Successfully', {
        description: 'Your previous API key has been revoked and replaced.',
      });
      refetch();
    } catch (err: any) {
      toast.error('Rotation failed', { description: err.message || 'Error rotating API key.' });
    }
  };

  const handleRevoke = async (keyId: string) => {
    try {
      await revokeKey.mutateAsync(keyId);
      toast.success('API Key Revoked', { description: `Key ${keyId} has been deactivated.` });
      refetch();
    } catch (err: any) {
      toast.error('Revocation failed', { description: err.message || 'Error revoking API key.' });
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1 max-w-4xl">
          <h1 className="text-3xl font-bold tracking-tight uppercase flex items-center gap-2 text-white">
            <KeyRound className="size-6 text-primary" /> API KEYS & PROXY QUOTAS
          </h1>
          <p className="text-sm text-zinc-400">Cryptographic token generation and scoped security access.</p>
          
          <div className="flex flex-wrap gap-3 mt-3 font-mono text-xs text-zinc-300">
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800">
              [ Active Keys: {isLoading ? '...' : keysList.length} ]
            </span>
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800 flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
              [ JWT Validation Active ]
            </span>
          </div>

          <details className="mt-4 group cursor-pointer">
            <summary className="text-xs font-semibold text-primary hover:underline list-none inline-flex items-center gap-1">
              Learn how API Keys work <span className="group-open:rotate-90 transition-transform">&gt;</span>
            </summary>
            <div className="mt-3 p-4 rounded-xl border border-primary/20 bg-primary/5 text-xs text-zinc-300 leading-relaxed max-w-2xl">
              API Keys authenticate your autonomous agents into the Agent-Bastion proxy infrastructure. They are cryptographically bound to your namespace and restricted to scoped <strong className="text-white font-mono">Role-Based Access Control (RBAC)</strong> policies.
            </div>
          </details>
        </div>

        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger render={<Button className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-5 py-6 shadow-lg" />}>
            <Plus className="mr-2 size-5" /> Generate API Key
          </DialogTrigger>
          <DialogContent className="bg-zinc-950 border-zinc-800 text-zinc-100 sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-xl font-bold text-white">Create Scoped Proxy API Key</DialogTitle>
              <DialogDescription className="text-zinc-400 text-xs">
                Generate a new cryptographic token bound to `{tenantName}` for SDK authentication.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4 mt-2">
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1">Key Name / Identifier</label>
                <Input
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  className="bg-zinc-900 border-zinc-800 text-white rounded-xl"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1">Permissions Scopes (comma-separated)</label>
                <Input
                  value={newKeyScope}
                  onChange={(e) => setNewKeyScope(e.target.value)}
                  className="bg-zinc-900 border-zinc-800 text-white font-mono text-xs rounded-xl"
                />
              </div>
              <Button
                type="submit"
                disabled={createKey.isPending}
                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold py-6 rounded-xl shadow-lg"
              >
                {createKey.isPending ? 'Generating Key...' : 'Generate Scoped API Key'}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="glass-panel border-primary/30 bg-zinc-900/60 shadow-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <ShieldCheck className="size-5 text-emerald-400" /> Primary Session Proxy Key
          </CardTitle>
          <CardDescription className="text-zinc-400">
            This key grants full access to the proxy engine and security APIs for <strong className="text-white font-mono">{tenantName}</strong>. 
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label className="text-xs font-mono text-zinc-400">Proxy Bearer / X-API-Key</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input 
                  value={apiKey || 'abs_live_default_token'} 
                  type={showKey ? 'text' : 'password'}
                  readOnly
                  className="font-mono bg-zinc-950 border-zinc-800 text-white pr-10 rounded-xl py-6"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white"
                >
                  {showKey ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
                </button>
              </div>
              <Button onClick={() => handleCopy()} className="bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl px-6 py-6 font-semibold">
                {copied ? <Check className="size-4 mr-2 text-emerald-400" /> : <Copy className="size-4 mr-2" />}
                {copied ? 'Copied' : 'Copy Key'}
              </Button>
            </div>
          </div>

          <div className="rounded-xl bg-amber-950/20 border border-amber-500/30 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="size-5 text-amber-400 mt-0.5 shrink-0" />
              <div>
                <h4 className="text-sm font-bold text-amber-300">Security Warning</h4>
                <p className="text-xs text-amber-200/70 mt-1 leading-relaxed font-mono">
                  This key provides full administrative access to your tenant policies and agent telemetry. 
                  Always inject it into your agents via environment variables (`ABS_API_KEY`) or secret vaults.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
        <CardFooter className="bg-zinc-950/60 border-t border-zinc-800 rounded-b-xl py-4 flex items-center justify-between">
          <p className="text-xs font-mono text-zinc-500">Cryptographic JWT / API Key validation enabled.</p>
          <Button
            variant="outline"
            onClick={() => handleRotate('key_primary_v1')}
            disabled={rotateKey.isPending}
            className="border-zinc-700 bg-zinc-900 text-zinc-200 hover:bg-zinc-800 text-xs font-mono"
          >
            <RefreshCw className="mr-2 size-3.5" /> Rotate Primary Key
          </Button>
        </CardFooter>
      </Card>

      {/* Scoped Keys Directory */}
      <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
        <CardHeader className="border-b border-zinc-800/80 pb-4">
          <CardTitle className="text-lg font-bold text-white">Active Scoped Keys Directory</CardTitle>
          <CardDescription className="text-zinc-400">Scoped keys mapped to specific agent pipelines</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse font-mono text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 bg-zinc-950/60">
                  <th className="py-3 px-4 font-semibold">KEY NAME</th>
                  <th className="py-3 px-4 font-semibold">PREFIX</th>
                  <th className="py-3 px-4 font-semibold">SCOPES</th>
                  <th className="py-3 px-4 font-semibold">STATUS</th>
                  <th className="py-3 px-4 font-semibold text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 text-zinc-300 font-sans">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-zinc-500">
                      Loading API Keys...
                    </td>
                  </tr>
                ) : keysList.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-14 text-center">
                      <div className="flex flex-col items-center justify-center space-y-3">
                        <KeyRound className="size-10 text-primary/40" />
                        <h4 className="text-sm font-semibold text-zinc-300">No API Keys Generated</h4>
                        <p className="text-xs text-zinc-500">Generate an API key to start integrating Agent-Bastion into your workflows.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  keysList.map((k: any, idx: number) => (
                    <tr key={k.id || idx} className="hover:bg-zinc-900/40 transition-colors">
                      <td className="py-3 px-4 font-bold text-white font-sans">{k.name || 'Agent Proxy Key'}</td>
                      <td className="py-3 px-4 font-mono text-cyan-400">{k.prefix || 'abs_token...'}</td>
                      <td className="py-3 px-4 font-mono">
                        <div className="flex flex-wrap gap-1">
                          {(k.scopes || ['*']).map((sc: string, i: number) => (
                            <span key={i} className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 text-[10px]">
                              {sc}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          {k.status || 'ACTIVE'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleCopy(k.prefix || apiKey)}
                          className="h-7 px-2.5 text-xs border-zinc-800 bg-zinc-950 text-zinc-300 font-sans"
                        >
                          Copy Prefix
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleRevoke(k.id || 'key_primary_v1')}
                          disabled={revokeKey.isPending}
                          className="h-7 px-2.5 text-xs font-sans"
                        >
                          <Trash2 className="mr-1 size-3" /> Revoke
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
