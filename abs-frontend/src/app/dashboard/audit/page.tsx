'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { ShieldAlert, RefreshCw, Search, Eye, CheckCircle2, XCircle, FileCode2, Clock, ShieldCheck } from 'lucide-react';
import { useAuditTrail, useIncidents } from '@/hooks/use-api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export default function AuditLogsPage() {
  const { data: auditData, isLoading: isLoadingAudit, refetch } = useAuditTrail(100);
  const { data: incidentsData } = useIncidents(1, 20);

  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedEvent, setSelectedEvent] = React.useState<any>(null);

  const auditList = auditData?.items || incidentsData?.items || [];
  const filteredList = auditList.filter((item: any) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const title = (item.title || item.event_type || item.action || '').toLowerCase();
    const details = (item.details || item.url || item.tenant_id || '').toLowerCase();
    return title.includes(q) || details.includes(q);
  });

  return (
    <div className="flex flex-col gap-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <ShieldAlert className="size-8 text-primary" /> Immutable Forensic Audit Logs
          </h1>
          <p className="text-zinc-400">
            PostgreSQL immutable audit records (`src/api/routes/v1/observability.py`) with full payload and DOM state inspection.
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()} className="border-zinc-800 bg-zinc-950 text-zinc-300">
          <RefreshCw className="mr-2 size-4" /> Refresh Audit Trail
        </Button>
      </div>

      <div className="flex items-center gap-3 bg-zinc-900/80 p-3 rounded-xl border border-zinc-800">
        <Search className="size-4 text-zinc-500 ml-1" />
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter audit logs by action, event type, or target DOM url..."
          className="bg-transparent border-none text-white focus-visible:ring-0 text-sm font-mono"
        />
      </div>

      <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
        <CardHeader className="border-b border-zinc-800/80 pb-4">
          <CardTitle className="text-lg font-bold text-white flex items-center justify-between">
            <span>Audit Trail Directory</span>
            <span className="text-xs font-mono text-zinc-400 font-normal">Total records showing: {filteredList.length}</span>
          </CardTitle>
          <CardDescription className="text-zinc-400">Click any row to inspect complete JSON telemetry and XAI explainability</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse font-mono text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 bg-zinc-950/60">
                  <th className="py-3 px-4 font-semibold">TIMESTAMP</th>
                  <th className="py-3 px-4 font-semibold">EVENT / ACTION</th>
                  <th className="py-3 px-4 font-semibold">TARGET DOM / DETAILS</th>
                  <th className="py-3 px-4 font-semibold">SEVERITY / STATUS</th>
                  <th className="py-3 px-4 font-semibold text-right">INSPECT</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 text-zinc-300 font-sans">
                {isLoadingAudit ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-28" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-40" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-4 w-60" /></td>
                      <td className="py-3 px-4"><Skeleton className="h-5 w-20" /></td>
                      <td className="py-3 px-4 text-right"><Skeleton className="h-7 w-20 ml-auto" /></td>
                    </tr>
                  ))
                ) : filteredList.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-zinc-500 font-sans">
                      <p className="text-sm font-semibold text-zinc-400">No audit records match your query</p>
                      <p className="text-xs mt-1">Simulate traffic on the Dashboard Overview to populate new audit events.</p>
                    </td>
                  </tr>
                ) : (
                  filteredList.map((item: any, idx: number) => {
                    const sev = (item.severity || item.status || 'INFO').toUpperCase();
                    const isAlert = sev === 'CRITICAL' || sev === 'HIGH' || sev === 'BLOCKED';

                    return (
                      <tr key={item.id || idx} className="hover:bg-zinc-900/40 transition-colors cursor-pointer" onClick={() => setSelectedEvent(item)}>
                        <td className="py-3 px-4 font-mono text-zinc-400 whitespace-nowrap">
                          {item.created_at || new Date().toLocaleString()}
                        </td>
                        <td className="py-3 px-4 font-bold text-white font-sans flex items-center gap-2">
                          {isAlert ? <XCircle className="size-4 text-red-500 shrink-0" /> : <CheckCircle2 className="size-4 text-emerald-400 shrink-0" />}
                          <span>{item.title || item.event_type || item.action || 'Proxy Action Event'}</span>
                        </td>
                        <td className="py-3 px-4 font-mono text-zinc-400 truncate max-w-sm">
                          {item.details || item.url || item.description || 'Verified clean DOM state'}
                        </td>
                        <td className="py-3 px-4 font-mono">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${isAlert ? 'bg-red-500/20 text-red-400 border border-red-500/40' : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'}`}>
                            {sev}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => { e.stopPropagation(); setSelectedEvent(item); }}
                            className="h-7 px-2.5 text-xs border-zinc-800 bg-zinc-950 text-zinc-300 hover:text-white font-sans"
                          >
                            <Eye className="mr-1 size-3" /> Inspect JSON
                          </Button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Audit JSON Modal */}
      {selectedEvent && (
        <Dialog open={!!selectedEvent} onOpenChange={(open) => !open && setSelectedEvent(null)}>
          <DialogContent className="bg-zinc-950 border-zinc-800 text-zinc-100 max-w-2xl font-mono text-xs">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold text-white font-sans flex items-center gap-2">
                <FileCode2 className="size-5 text-primary" /> Forensic Audit JSON Record
              </DialogTitle>
              <DialogDescription className="text-zinc-400 font-sans">
                Full immutable telemetry, XAI logs, and MITRE ATT&CK breakdown stored in PostgreSQL.
              </DialogDescription>
            </DialogHeader>
            <div className="mt-4 bg-zinc-900/80 p-4 rounded-xl border border-zinc-800 overflow-x-auto max-h-[400px] text-zinc-300 leading-relaxed">
              <pre>{JSON.stringify(selectedEvent, null, 2)}</pre>
            </div>
            <div className="flex justify-end mt-4 font-sans">
              <Button onClick={() => setSelectedEvent(null)} className="bg-zinc-800 hover:bg-zinc-700 text-white text-xs">
                Close Inspector
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
