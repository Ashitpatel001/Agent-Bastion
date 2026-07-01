'use client';

import * as React from 'react';
import { useSecurityEvents, useSecurityLogs } from '@/hooks/use-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatRelativeTime, formatDate, truncateUrl } from '@/utils/format';
import { RISK_LEVEL_COLORS } from '@/lib/constants';
import { RiskLevel } from '@/types';
import { Activity, ShieldAlert, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Radio, TerminalSquare, AlertOctagon, CheckCircle } from 'lucide-react';

interface NormalizedEvent {
  id: string | number;
  created_at: string;
  severity: string;
  source: string;
  event_type: string;
  details: Record<string, unknown> | string | null;
  riskScore?: number;
}

export default function LiveSecurityFeedPage() {
  const [page, setPage] = React.useState(1);
  const [expandedRows, setExpandedRows] = React.useState<Record<string, boolean>>({});

  const { data: eventsData, isLoading: isEventsLoading } = useSecurityEvents(page, 50);
  const { data: logsData, isLoading: isLogsLoading } = useSecurityLogs(page, 50);

  const isLoading = isEventsLoading || (eventsData?.items?.length === 0 && isLogsLoading);

  const normalizedEvents: NormalizedEvent[] = React.useMemo(() => {
    if (eventsData?.items && eventsData.items.length > 0) {
      return eventsData.items.map((e) => ({
        id: `ev-${e.id}`,
        created_at: e.created_at,
        severity: e.severity?.toUpperCase() || 'MEDIUM',
        source: e.source || 'Sentinel Monitor',
        event_type: e.event_type || 'SECURITY_EVENT',
        details: e.details || {},
      }));
    }

    if (logsData?.items && logsData.items.length > 0) {
      return logsData.items.map((log) => ({
        id: `log-${log.id}`,
        created_at: log.created_at,
        severity: log.risk_level || (log.risk_score > 80 ? 'CRITICAL' : log.risk_score > 60 ? 'HIGH' : log.risk_score > 40 ? 'MEDIUM' : 'LOW'),
        source: log.url || 'Agent Action Sentinel',
        event_type: log.event_type || 'AGENT_ACTION',
        details: log.risk_breakdown || (log.details ? { message: log.details } : { action_taken: log.action_taken, risk_score: log.risk_score }),
        riskScore: log.risk_score,
      }));
    }

    return [];
  }, [eventsData?.items, logsData?.items]);

  const totalEventsCount = eventsData?.total || logsData?.total || normalizedEvents.length;

  const criticalAlertCount = React.useMemo(() => {
    return normalizedEvents.filter(
      (ev) =>
        ev.severity === 'CRITICAL' ||
        ev.severity === RiskLevel.CRITICAL ||
        ev.severity === 'HIGH' ||
        ev.severity === RiskLevel.HIGH ||
        (ev.riskScore && ev.riskScore >= 75)
    ).length;
  }, [normalizedEvents]);

  const toggleExpand = (id: string | number) => {
    const strId = String(id);
    setExpandedRows((prev) => ({
      ...prev,
      [strId]: !prev[strId],
    }));
  };

  const getSeverityBadgeClass = (sev: string) => {
    const s = sev.toUpperCase();
    if (s === 'CRITICAL') return RISK_LEVEL_COLORS[RiskLevel.CRITICAL] || 'bg-red-950/60 text-red-400 border-red-900/60';
    if (s === 'HIGH') return RISK_LEVEL_COLORS[RiskLevel.HIGH] || 'bg-orange-950/60 text-orange-400 border-orange-900/60';
    if (s === 'MEDIUM') return RISK_LEVEL_COLORS[RiskLevel.MEDIUM] || 'bg-amber-950/60 text-amber-400 border-amber-900/60';
    if (s === 'LOW') return RISK_LEVEL_COLORS[RiskLevel.LOW] || 'bg-emerald-950/40 text-emerald-400 border-emerald-900/60';
    return RISK_LEVEL_COLORS[RiskLevel.SAFE] || 'bg-zinc-800 text-zinc-300';
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto h-full pb-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="size-8 text-cyan-500" />
            <h1 className="text-3xl font-bold tracking-tight">Live Security Feed</h1>
          </div>
          <p className="text-muted-foreground mt-1">
            Real-time security event monitoring and autonomous telemetry stream.
          </p>
        </div>

        <div className="flex items-center gap-3 px-4 py-2 rounded-full bg-zinc-900/90 border border-zinc-800 shadow-sm">
          <span className="relative flex size-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full size-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-mono font-medium text-zinc-200 flex items-center gap-1.5">
            <Radio className="size-3.5 text-emerald-400 animate-pulse" />
            Live Monitoring (Auto-refresh 5s)
          </span>
        </div>
      </div>

      {/* Stats Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="glass border-zinc-800 bg-zinc-900/40">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Total Streamed Events
            </CardTitle>
            <Activity className="size-4 text-cyan-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-zinc-100">
              {isLoading ? <Skeleton className="h-7 w-20" /> : totalEventsCount.toLocaleString()}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1 flex items-center gap-1">
              <CheckCircle className="size-3 text-emerald-400" /> Active stream telemetry
            </p>
          </CardContent>
        </Card>

        <Card className="glass border-zinc-800 bg-zinc-900/40">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              High / Critical Alerts
            </CardTitle>
            <AlertOctagon className="size-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-red-400">
              {isLoading ? <Skeleton className="h-7 w-12" /> : criticalAlertCount}
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              Requiring immediate review in current view
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Events Table */}
      <Card className="glass flex-1 flex flex-col overflow-hidden border-zinc-800">
        <CardHeader className="bg-zinc-900/50 border-b border-zinc-800 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <TerminalSquare className="size-4 text-cyan-400" /> Real-time Event Log
            </CardTitle>
            <CardDescription>
              Streaming events from active agents, DOM interceptors, and network proxy layers.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0 flex-1 overflow-auto">
          <Table>
            <TableHeader className="bg-zinc-950/80 sticky top-0 z-10 shadow-sm border-b border-zinc-800">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="w-[150px]">Time</TableHead>
                <TableHead className="w-[130px]">Severity</TableHead>
                <TableHead>Source / Target</TableHead>
                <TableHead>Event Type</TableHead>
                <TableHead className="w-[80px] text-right">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-52" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="h-6 w-6 ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : normalizedEvents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-12 text-muted-foreground">
                    No security events currently streaming. System state is nominal.
                  </TableCell>
                </TableRow>
              ) : (
                normalizedEvents.map((ev) => {
                  const isExpanded = !!expandedRows[String(ev.id)];
                  return (
                    <React.Fragment key={ev.id}>
                      <TableRow className="hover:bg-zinc-900/40 border-b border-zinc-800/50 transition-colors">
                        <TableCell className="font-mono text-xs text-zinc-400 whitespace-nowrap" title={formatDate(ev.created_at)}>
                          {formatRelativeTime(ev.created_at)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={`text-xs px-2 py-0.5 font-mono uppercase ${getSeverityBadgeClass(ev.severity)}`}>
                            {ev.severity}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs text-zinc-300">
                          {truncateUrl(ev.source, 45)}
                        </TableCell>
                        <TableCell className="font-medium text-xs">
                          <div className="flex items-center gap-1.5 text-zinc-200">
                            {ev.severity === 'CRITICAL' && <ShieldAlert className="size-3.5 text-red-500 shrink-0" />}
                            <span>{ev.event_type.replace(/_/g, ' ').toUpperCase()}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => toggleExpand(ev.id)}
                            title={isExpanded ? 'Hide JSON details' : 'View JSON details'}
                          >
                            {isExpanded ? <ChevronUp className="size-4 text-cyan-400" /> : <ChevronDown className="size-4 text-muted-foreground" />}
                          </Button>
                        </TableCell>
                      </TableRow>
                      {isExpanded && (
                        <TableRow className="bg-zinc-900/60 border-b border-zinc-800">
                          <TableCell colSpan={5} className="p-4">
                            <div className="rounded-lg border border-zinc-800 bg-zinc-950/90 p-3 space-y-2">
                              <div className="flex items-center justify-between border-b border-zinc-800/80 pb-1.5">
                                <span className="text-[11px] font-mono uppercase text-cyan-400">
                                  Event Payload JSON
                                </span>
                                <span className="text-[11px] font-mono text-muted-foreground">
                                  Event ID: {ev.id}
                                </span>
                              </div>
                              <pre className="text-xs font-mono text-zinc-300 overflow-x-auto p-2 bg-black/40 rounded">
                                {typeof ev.details === 'string'
                                  ? ev.details
                                  : JSON.stringify(ev.details, null, 2)}
                              </pre>
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
            {isLoading ? 'Loading stream...' : `Showing ${normalizedEvents.length} live events`}
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
              disabled={normalizedEvents.length < 50 || isLoading}
            >
              Next <ChevronRight className="size-4 ml-1" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
