'use client';

import * as React from 'react';
import Link from 'next/link';
import { useActivePolicy, useReputationCheck, useSecurityLogs } from '@/hooks/use-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDate, truncateUrl } from '@/utils/format';
import { RISK_LEVEL_COLORS, ACTION_TAKEN_COLORS } from '@/lib/constants';
import { ActionTaken, ReputationCheckResponse } from '@/types';
import { ShieldCheck, ShieldAlert, Globe, Loader2, ExternalLink, Search, Lock, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';

export default function ProxyFirewallPage() {
  const { data: policy, isLoading: isPolicyLoading } = useActivePolicy();
  const checkReputation = useReputationCheck();
  const { data: logsData, isLoading: isLogsLoading } = useSecurityLogs(1, 10);

  const [inputUrl, setInputUrl] = React.useState('');
  const [repResult, setRepResult] = React.useState<ReputationCheckResponse | null>(null);

  const handleCheckReputation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;
    try {
      const res = await checkReputation.mutateAsync(inputUrl.trim());
      setRepResult(res);
    } catch (err) {
      // Handled by API client or fallback
    }
  };

  const blockedLogs = React.useMemo(() => {
    if (!logsData?.items) return [];
    return logsData.items.filter(
      (log) =>
        log.action_taken === ActionTaken.BLOCKED ||
        log.action_taken === ActionTaken.BLOCK_AND_ESCALATE ||
        log.action_taken.toString().toUpperCase().includes('BLOCK')
    );
  }, [logsData?.items]);

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto h-full pb-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-8 text-cyan-500" />
            <h1 className="text-3xl font-bold tracking-tight">Proxy Firewall</h1>
          </div>
          <p className="text-muted-foreground mt-1">
            Network-level security controls and domain reputation verification.
          </p>
        </div>

        <Link href="/dashboard/policies">
          <Button variant="outline" className="border-cyan-800/60 text-cyan-400 hover:bg-cyan-950/40">
            Edit Firewall Rules <ExternalLink className="size-4 ml-2" />
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Section 1: Active Firewall Rules */}
        <Card className="glass lg:col-span-2 border-zinc-800 flex flex-col">
          <CardHeader className="bg-zinc-900/40 border-b border-zinc-800">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Lock className="size-5 text-cyan-400" /> Active Firewall Rules
            </CardTitle>
            <CardDescription>
              Current enforcement tokens dynamically loaded from the Sentinel policy engine.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-6 space-y-6 flex-1">
            {isPolicyLoading ? (
              <div className="space-y-4 py-4">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-4 w-1/4" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : (
              <>
                <div>
                  <h4 className="text-sm font-medium text-zinc-300 mb-2 flex items-center gap-2">
                    Blocked Domains <Badge variant="destructive" className="text-[10px] h-4 px-1.5">{policy?.blocked_domains?.length || 0}</Badge>
                  </h4>
                  <div className="flex flex-wrap gap-2 min-h-[32px] p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80">
                    {policy?.blocked_domains && policy.blocked_domains.length > 0 ? (
                      policy.blocked_domains.map((dom, idx) => (
                        <Badge key={idx} variant="destructive" className="bg-red-950/60 text-red-400 border-red-900/50 text-xs">
                          {dom}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-xs text-muted-foreground italic">No domains explicitly blocked in denylist.</span>
                    )}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-zinc-300 mb-2 flex items-center gap-2">
                    Trusted Domains <Badge variant="outline" className="text-[10px] h-4 px-1.5 border-emerald-800 text-emerald-400">{policy?.trusted_domains?.length || 0}</Badge>
                  </h4>
                  <div className="flex flex-wrap gap-2 min-h-[32px] p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80">
                    {policy?.trusted_domains && policy.trusted_domains.length > 0 ? (
                      policy.trusted_domains.map((dom, idx) => (
                        <Badge key={idx} variant="outline" className="bg-emerald-950/30 text-emerald-400 border-emerald-900/50 text-xs">
                          {dom}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-xs text-muted-foreground italic">No domains explicitly allowlisted.</span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  <div>
                    <h4 className="text-sm font-medium text-zinc-300 mb-2">Blocked Input Patterns (DLP)</h4>
                    <div className="flex flex-wrap gap-2 p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 min-h-[44px]">
                      {policy?.blocked_input_patterns && policy.blocked_input_patterns.length > 0 ? (
                        policy.blocked_input_patterns.map((pat, idx) => (
                          <Badge key={idx} variant="secondary" className="font-mono text-[11px] bg-purple-950/40 text-purple-300 border border-purple-900/40">
                            {pat}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground italic">Standard regex patterns active.</span>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-medium text-zinc-300 mb-2">Blocked Actions</h4>
                    <div className="flex flex-wrap gap-2 p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 min-h-[44px]">
                      {policy?.blocked_actions && policy.blocked_actions.length > 0 ? (
                        policy.blocked_actions.map((act, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs bg-zinc-800 text-zinc-300">
                            {act}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground italic">No action types blocked.</span>
                      )}
                    </div>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Section 2: Domain Reputation Checker */}
        <Card className="glass border-zinc-800 flex flex-col">
          <CardHeader className="bg-zinc-900/40 border-b border-zinc-800">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Globe className="size-5 text-cyan-400" /> Domain Reputation
            </CardTitle>
            <CardDescription>
              Verify real-time trust scores and threat categorization for target URLs.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-6 space-y-6 flex-1 flex flex-col justify-between">
            <form onSubmit={handleCheckReputation} className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Target Domain or URL
                </label>
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g. api.suspicious-host.com"
                    value={inputUrl}
                    onChange={(e) => setInputUrl(e.target.value)}
                    className="bg-zinc-950/80 border-zinc-800 font-mono text-sm focus:border-cyan-600"
                  />
                </div>
              </div>
              <Button
                type="submit"
                disabled={checkReputation.isPending || !inputUrl.trim()}
                className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium"
              >
                {checkReputation.isPending ? (
                  <>
                    <Loader2 className="size-4 mr-2 animate-spin" /> Analyzing Reputation...
                  </>
                ) : (
                  <>
                    <Search className="size-4 mr-2" /> Check Reputation
                  </>
                )}
              </Button>
            </form>

            <div className="mt-6 pt-6 border-t border-zinc-800/80 flex-1 flex flex-col justify-center">
              {repResult ? (
                <div className="space-y-4 rounded-lg bg-zinc-950/90 border border-zinc-800 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-zinc-400 truncate max-w-[150px]">
                      {repResult.domain || repResult.url}
                    </span>
                    <Badge
                      variant={repResult.is_safe ? 'outline' : 'destructive'}
                      className={`flex items-center gap-1 ${
                        repResult.is_safe
                          ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                          : 'bg-red-950/60 text-red-400 border-red-900/60'
                      }`}
                    >
                      {repResult.is_safe ? <CheckCircle2 className="size-3" /> : <AlertTriangle className="size-3" />}
                      {repResult.trust_level || (repResult.is_safe ? 'SAFE' : 'HIGH RISK')}
                    </Badge>
                  </div>
                  <p className="text-xs text-zinc-300 leading-relaxed bg-zinc-900/50 p-2.5 rounded border border-zinc-800/60">
                    {repResult.details || 'Domain reputation verified against global autonomous threat intelligence databases.'}
                  </p>
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground space-y-2">
                  <Globe className="size-8 mx-auto text-zinc-700 opacity-40" />
                  <p className="text-xs">Enter a domain or full URL above to run instant reputational diagnostics.</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Section 3: Recent Blocked Events */}
      <Card className="glass border-zinc-800 overflow-hidden">
        <CardHeader className="bg-zinc-900/40 border-b border-zinc-800">
          <CardTitle className="flex items-center gap-2">
            <XCircle className="size-5 text-red-500" /> Recent Blocked Events
          </CardTitle>
          <CardDescription>
            Live stream of intercepted network calls and unauthorized actions stopped by the firewall.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0 overflow-auto">
          <Table>
            <TableHeader className="bg-zinc-950/80 border-b border-zinc-800">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="w-[180px]">Timestamp</TableHead>
                <TableHead>Event Type</TableHead>
                <TableHead>Target URL</TableHead>
                <TableHead>Risk Score</TableHead>
                <TableHead>Action Taken</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLogsLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-48" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  </TableRow>
                ))
              ) : blockedLogs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    No recently blocked events observed. Agent operations are within authorized parameters.
                  </TableCell>
                </TableRow>
              ) : (
                blockedLogs.map((log) => (
                  <TableRow key={log.id} className="hover:bg-zinc-900/40 border-b border-zinc-800/50">
                    <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(log.created_at)}
                    </TableCell>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <ShieldAlert className="size-4 text-red-500" />
                        <span className="text-xs uppercase tracking-wide">
                          {log.event_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {log.url ? (
                        <a
                          href={log.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-cyan-400 hover:underline text-sm truncate max-w-[280px] block"
                          title={log.url}
                        >
                          {truncateUrl(log.url, 45)}
                        </a>
                      ) : (
                        <span className="text-muted-foreground text-sm">N/A</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={RISK_LEVEL_COLORS[log.risk_level]}>
                        {log.risk_score}/100
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className={`text-sm font-semibold ${ACTION_TAKEN_COLORS[log.action_taken]}`}>
                        {log.action_taken}
                      </span>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
