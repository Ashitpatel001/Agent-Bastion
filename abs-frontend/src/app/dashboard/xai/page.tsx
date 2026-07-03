'use client';

import * as React from 'react';
import { useXaiLogs } from '@/hooks/use-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { formatDate, truncateUrl } from '@/utils/format';
import { RISK_LEVEL_COLORS, ACTION_TAKEN_COLORS } from '@/lib/constants';
import { BrainCircuit, Loader2, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

export default function XaiExplanationsPage() {
  const [page, setPage] = React.useState(1);
  const [activeTab, setActiveTab] = React.useState<'all' | 'pending'>('all');
  const [expandedRows, setExpandedRows] = React.useState<Record<string | number, boolean>>({});

  const isPendingFilter = activeTab === 'pending';
  const { data, isLoading } = useXaiLogs(page, 20, isPendingFilter);

  const toggleExpand = (id: string | number) => {
    setExpandedRows((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleTabChange = (val: string) => {
    setActiveTab(val as 'all' | 'pending');
    setPage(1);
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto h-full">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BrainCircuit className="size-8 text-cyan-500" />
            <h1 className="text-3xl font-bold tracking-tight">XAI Explanations</h1>
          </div>
          <p className="text-muted-foreground mt-1">
            AI-generated security analysis for blocked actions and threat telemetry.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-[300px]">
          <TabsList className="grid w-full grid-cols-2 bg-zinc-900 border border-zinc-800">
            <TabsTrigger value="all">All Explained</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <Card className="glass flex-1 flex flex-col overflow-hidden border-zinc-800">
        <CardHeader className="bg-zinc-900/50 border-b border-zinc-800 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="size-4 text-cyan-400" /> Explainable AI Audit Log
            </CardTitle>
            <CardDescription>
              Deep neural analysis detailing exactly why autonomous requests were intercepted or allowed.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0 flex-1 overflow-auto">
          <Table>
            <TableHeader className="bg-zinc-950/80 sticky top-0 z-10 shadow-sm border-b border-zinc-800">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="w-[170px]">Timestamp</TableHead>
                <TableHead>Event Type</TableHead>
                <TableHead>Target URL</TableHead>
                <TableHead>Risk Score</TableHead>
                <TableHead>Action Taken</TableHead>
                <TableHead className="w-[280px]">XAI Analysis</TableHead>
                <TableHead className="w-[60px] text-right"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-48" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="h-6 w-6 ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : !data || data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                    No XAI explanation records found matching this filter.
                  </TableCell>
                </TableRow>
              ) : (
                data.items.map((log) => {
                  const isExpanded = !!expandedRows[log.id];
                  const isPending = log.xai_pending || !log.xai_explanation;

                  return (
                    <React.Fragment key={log.id}>
                      <TableRow className="hover:bg-zinc-900/40 border-b border-zinc-800/50 transition-colors">
                        <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                          {formatDate(log.created_at)}
                        </TableCell>
                        <TableCell className="font-medium">
                          <Badge variant="secondary" className="font-mono text-xs uppercase bg-zinc-800 text-zinc-300">
                            {log.event_type ? log.event_type.replace(/_/g, ' ') : 'UNKNOWN'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {log.url ? (
                            <a
                              href={log.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-cyan-400 hover:underline text-sm truncate max-w-[220px] block"
                              title={log.url}
                            >
                              {truncateUrl(log.url, 38)}
                            </a>
                          ) : (
                            <span className="text-muted-foreground text-sm">N/A</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={RISK_LEVEL_COLORS[log.risk_level as keyof typeof RISK_LEVEL_COLORS] || 'border-zinc-700'}>
                            {log.risk_score}/100
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <span className={`text-sm font-semibold ${ACTION_TAKEN_COLORS[log.action_taken as keyof typeof ACTION_TAKEN_COLORS] || 'text-zinc-400'}`}>
                            {log.action_taken}
                          </span>
                        </TableCell>
                        <TableCell>
                          {isPending ? (
                            <div className="flex items-center gap-2 text-amber-400 text-xs">
                              <Loader2 className="size-3.5 animate-spin" />
                              <span>Generating analysis...</span>
                            </div>
                          ) : (
                            <p className="text-xs text-zinc-300 line-clamp-2 max-w-[280px]">
                              {log.xai_explanation}
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => toggleExpand(log.id)}
                            title={isExpanded ? 'Collapse analysis' : 'Expand analysis'}
                          >
                            {isExpanded ? <ChevronUp className="size-4 text-cyan-400" /> : <ChevronDown className="size-4 text-muted-foreground" />}
                          </Button>
                        </TableCell>
                      </TableRow>
                      {isExpanded && (
                        <TableRow className="bg-zinc-900/60 border-b border-zinc-800">
                          <TableCell colSpan={7} className="p-4">
                            <div className="rounded-lg border border-cyan-900/40 bg-cyan-950/10 p-4 space-y-2">
                              <div className="flex items-center justify-between border-b border-cyan-900/30 pb-2">
                                <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                                  <Sparkles className="size-3.5" /> Complete Sentinel Explanation
                                </span>
                                <span className="text-xs text-muted-foreground font-mono">
                                  ID: #{log.id}
                                </span>
                              </div>
                              {isPending ? (
                                <div className="flex items-center gap-2 py-4 text-amber-400 text-sm">
                                  <Loader2 className="size-4 animate-spin" />
                                  <span>The Sentinel is currently analyzing telemetry for this event...</span>
                                </div>
                              ) : (
                                <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap font-sans">
                                  {log.xai_explanation}
                                </div>
                              )}
                              {log.details && (typeof log.details === 'string' ? log.details.length > 0 : Object.keys(log.details).length > 0) && (
                                <div className="mt-3 pt-3 border-t border-zinc-800/60">
                                  <span className="text-xs font-medium text-muted-foreground block mb-1">Raw Telemetry Details:</span>
                                  <pre className="text-[11px] font-mono bg-zinc-950/80 p-2.5 rounded border border-zinc-800 text-zinc-400 overflow-x-auto">
                                    {typeof log.details === 'string' ? log.details : JSON.stringify(log.details, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
        <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-800 bg-zinc-900/50">
          <div className="text-sm text-muted-foreground">
            {isLoading ? 'Loading...' : `Showing ${data?.items.length || 0} of ${data?.total || 0} explanations`}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || isLoading}
            >
              <ChevronLeft className="size-4 mr-1" /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={!data || data.items.length < data.page_size || isLoading}
            >
              Next <ChevronRight className="size-4 ml-1" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
