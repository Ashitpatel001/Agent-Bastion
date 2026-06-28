'use client';

import * as React from 'react';
import { useSecurityLogs } from '@/hooks/use-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDate, truncateUrl } from '@/utils/format';
import { RISK_LEVEL_COLORS, ACTION_TAKEN_COLORS } from '@/lib/constants';
import { Eye, ShieldAlert, ChevronLeft, ChevronRight } from 'lucide-react';

export default function IncidentsPage() {
  const [page, setPage] = React.useState(1);
  const { data, isLoading } = useSecurityLogs(page, 20);

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto h-full">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Incidents & Forensics</h1>
        <p className="text-muted-foreground">
          Review security events, intercepted actions, and threat telemetry from your autonomous agents.
        </p>
      </div>

      <Card className="glass flex-1 flex flex-col overflow-hidden border-zinc-800">
        <CardHeader className="bg-zinc-900/50 border-b border-zinc-800">
          <CardTitle>Security Audit Log</CardTitle>
          <CardDescription>
            All network requests, DOM mutations, and agent actions are logged and analyzed here.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0 flex-1 overflow-auto">
          <Table>
            <TableHeader className="bg-zinc-950/80 sticky top-0 z-10 shadow-sm border-b border-zinc-800">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="w-[180px]">Timestamp</TableHead>
                <TableHead>Event Type</TableHead>
                <TableHead>Target</TableHead>
                <TableHead>Risk Score</TableHead>
                <TableHead>Action Taken</TableHead>
                <TableHead className="text-right">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-48" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="h-8 w-8 ml-auto" /></TableCell>
                  </TableRow>
                ))
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No security incidents found. Your agents are operating safely.
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((log) => (
                  <TableRow key={log.id} className="hover:bg-zinc-900/40 border-b border-zinc-800/50">
                    <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(log.created_at)}
                    </TableCell>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        {log.risk_score > 60 && <ShieldAlert className="size-4 text-red-500" />}
                        {log.event_type.replace(/_/g, ' ').toUpperCase()}
                      </div>
                    </TableCell>
                    <TableCell>
                      {log.url ? (
                        <a href={log.url} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline text-sm truncate max-w-[200px] block" title={log.url}>
                          {truncateUrl(log.url, 40)}
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
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <Eye className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
        <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-800 bg-zinc-900/50">
          <div className="text-sm text-muted-foreground">
            {isLoading ? 'Loading...' : `Showing ${data?.items.length || 0} of ${data?.total || 0} events`}
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1 || isLoading}
            >
              <ChevronLeft className="size-4 mr-1" /> Previous
            </Button>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setPage(p => p + 1)}
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
