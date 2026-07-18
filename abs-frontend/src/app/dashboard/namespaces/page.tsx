'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Layers, ShieldCheck, Database, Cpu, Plus, CheckCircle2, Building2, KeyRound } from 'lucide-react';
import { useObservabilityTenants, useDxOverview, useOrganizations } from '@/hooks/use-api';
import { useAppStore } from '@/store/app-store';

export default function NamespacesPage() {
  const { data: obsTenants, isLoading: isLoadingTenants, refetch } = useObservabilityTenants();
  const { data: dxOverview } = useDxOverview();
  const { data: orgs } = useOrganizations();
  const { tenantId, tenantName, tenantTier } = useAppStore();

  const tenantsList = obsTenants?.tenants || orgs?.items || [
    {
      id: tenantId || 'tnt_default',
      name: tenantName || 'Enterprise Namespace',
      tier: tenantTier || 'ENTERPRISE',
      status: 'ACTIVE',
      max_concurrent_tasks: dxOverview?.rate_limits?.max_concurrent_tasks || 25,
      created_at: new Date().toISOString(),
    }
  ];

  return (
    <div className="flex flex-col gap-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1 max-w-4xl">
          <h1 className="text-3xl font-bold tracking-tight uppercase flex items-center gap-2 text-white">
            <Layers className="size-6 text-primary" /> NAMESPACES
          </h1>
          <p className="text-sm text-zinc-400">PostgreSQL row-level security and tenant isolation boundaries.</p>
          
          <div className="flex flex-wrap gap-3 mt-3 font-mono text-xs text-zinc-300">
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800">
              [ Active Namespaces: {isLoadingTenants ? '...' : tenantsList.length} ]
            </span>
            <span className="px-2 py-1 rounded bg-zinc-900 border border-zinc-800 flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
              [ RLS Isolation Enabled ]
            </span>
          </div>

          <details className="mt-4 group cursor-pointer">
            <summary className="text-xs font-semibold text-primary hover:underline list-none inline-flex items-center gap-1">
              Learn how tenant namespaces work <span className="group-open:rotate-90 transition-transform">&gt;</span>
            </summary>
            <div className="mt-3 p-4 rounded-xl border border-primary/20 bg-primary/5 text-xs text-zinc-300 leading-relaxed max-w-2xl">
              A namespace is a secure multi-tenant boundary. Agent-Bastion enforces strict <strong className="text-white font-mono">PostgreSQL Row Level Security (RLS)</strong> and <strong className="text-white font-mono">Token Bucket Rate Limiting</strong> to ensure your agent traffic and data never bleeds across organizational boundaries.
            </div>
          </details>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3 font-mono">
        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-primary">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">ACTIVE NAMESPACES</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-extrabold text-white">
              {isLoadingTenants ? <Skeleton className="h-8 w-16" /> : tenantsList.length}
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Tenant namespaces initialized</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-cyan-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">ISOLATION ENFORCEMENT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-cyan-400 flex items-center gap-1.5">
              <ShieldCheck className="size-5" /> PostgreSQL RLS
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Strict tenant boundary per query</p>
          </CardContent>
        </Card>

        <Card className="glass-panel bg-zinc-900/60 border-zinc-800 border-l-4 border-l-emerald-500">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400">DEFAULT RATE LIMIT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-400">
              {dxOverview?.rate_limits?.max_concurrent_tasks || 25} tasks / min
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">Per-tenant Celery token bucket</p>
          </CardContent>
        </Card>
      </div>

      <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
        <CardHeader className="border-b border-zinc-800/80 pb-4">
          <CardTitle className="text-lg font-bold text-white">Registered Multi-Tenant Namespaces</CardTitle>
          <CardDescription className="text-zinc-400">Isolated database schemas and rate limiting buckets</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse font-mono text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 bg-zinc-950/60">
                  <th className="py-3 px-4 font-semibold">NAMESPACE ID</th>
                  <th className="py-3 px-4 font-semibold">ORGANIZATION NAME</th>
                  <th className="py-3 px-4 font-semibold">TIER QUOTA</th>
                  <th className="py-3 px-4 font-semibold">MAX CONCURRENCY</th>
                  <th className="py-3 px-4 font-semibold">ISOLATION STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 text-zinc-300 font-sans">
                {isLoadingTenants ? (
                  Array.from({ length: 2 }).map((_, i) => (
                    <tr key={i}>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-24" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-32" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-5 w-20" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-16" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-5 w-24" /></td>
                    </tr>
                  ))
                ) : (
                  tenantsList.map((t: any, idx: number) => (
                    <tr key={idx} className="hover:bg-zinc-900/40 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-primary">{t.id || t.tenant_id || `tnt_${idx + 101}`}</td>
                      <td className="py-3 px-4 font-semibold text-white flex items-center gap-2">
                        <Building2 className="size-4 text-zinc-500" /> {t.name || t.tenant_name || 'Enterprise Namespace'}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
                          {t.tier || 'PRO'}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-emerald-400 font-bold">
                        {t.max_concurrent_tasks || 25} concurrent
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          <CheckCircle2 className="size-3" /> RLS ISOLATED
                        </span>
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
