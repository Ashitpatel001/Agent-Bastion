'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldAlert, ShieldCheck, Activity, Users } from 'lucide-react';
import { useSecurityStats, useAnalyticsTimeSeries, useIncidents, useSimulateTraffic } from '@/hooks/use-api';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Terminal, PlayCircle } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

function getSeverityColor(sev?: string) {
  const s = (sev || '').toLowerCase();
  if (s === 'critical') return 'text-red-500';
  if (s === 'high') return 'text-orange-500';
  if (s === 'medium') return 'text-amber-500';
  return 'text-emerald-400';
}

function formatTimeAgo(dateStr?: string) {
  if (!dateStr) return 'Recently';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins === 1 ? '' : 's'} ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hr${diffHours === 1 ? '' : 's'} ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
  } catch {
    return dateStr;
  }
}

export default function OverviewPage() {
  const { data: stats, isLoading } = useSecurityStats();
  const { data: timeSeriesResponse, isLoading: isLoadingChart } = useAnalyticsTimeSeries(30);
  const { data: incidentsResponse, isLoading: isLoadingIncidents } = useIncidents(1, 5);

  const chartList = timeSeriesResponse?.data || [];
  const incidentsList = incidentsResponse?.items || [];
  const simulateTraffic = useSimulateTraffic();

  const handleSimulate = async () => {
    await simulateTraffic.mutateAsync();
  };

  const isDashboardEmpty = stats?.total_actions === 0 && !isLoading;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your autonomous agents' security posture and metrics.
          </p>
        </div>
        
        {isDashboardEmpty && (
          <Button 
            onClick={handleSimulate} 
            disabled={simulateTraffic.isPending}
            className="bg-cyan-600 hover:bg-cyan-500 text-white shadow-[0_0_15px_rgba(8,145,178,0.4)]"
          >
            {simulateTraffic.isPending ? 'Simulating...' : (
              <>
                <PlayCircle className="mr-2 h-4 w-4" /> Simulate Proxy Traffic
              </>
            )}
          </Button>
        )}
      </div>

      {isDashboardEmpty && (
        <Card className="glass border-cyan-500/30 bg-gradient-to-br from-cyan-950/20 to-transparent">
          <CardHeader>
            <CardTitle className="text-xl text-cyan-400 flex items-center gap-2">
              <ShieldCheck className="h-6 w-6" /> 
              Welcome to the ABS Proxy Firewall!
            </CardTitle>
            <CardDescription className="text-zinc-300 text-base">
              Your autonomous agents are now protected. Follow these steps to route traffic through the zero-trust proxy and see real-time metrics.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800">
                <h3 className="font-semibold text-white mb-2">1. Connect Your Agents</h3>
                <p className="text-sm text-zinc-400 mb-3">Configure your agent's network requests to route through the ABS proxy endpoint.</p>
                <code className="text-xs text-cyan-300 bg-black/40 p-2 rounded block">export HTTP_PROXY=http://localhost:8000</code>
              </div>
              <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800">
                <h3 className="font-semibold text-white mb-2">2. Real-time Protection</h3>
                <p className="text-sm text-zinc-400">Our engine sits between your agent and the internet, inspecting payloads, URLs, and DOM structures in real-time.</p>
              </div>
              <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800">
                <h3 className="font-semibold text-white mb-2">3. Cost & Time Savings</h3>
                <p className="text-sm text-zinc-400">Reduce manual review time and prevent costly data breaches. ABS handles threats automatically.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="glass">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Actions Analyzed</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-20" /> : String(stats?.total_actions || '0')}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              +20.1% from last month
            </p>
          </CardContent>
        </Card>
        
        <Card className="glass border-emerald-500/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Safe Actions</CardTitle>
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">
              {isLoading ? <Skeleton className="h-8 w-20" /> : String(stats?.safe_actions || '0')}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              97% of total volume
            </p>
          </CardContent>
        </Card>
        
        <Card className="glass border-red-500/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Threats Blocked</CardTitle>
            <ShieldAlert className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">
              {isLoading ? <Skeleton className="h-8 w-20" /> : String(stats?.blocked_actions || '0')}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              +12 this week
            </p>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-20" /> : String(stats?.active_sessions || '0')}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Currently running jobs
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4 glass-panel">
          <CardHeader>
            <CardTitle>Activity Over Time</CardTitle>
            <CardDescription>Safe vs blocked actions across all agents</CardDescription>
          </CardHeader>
          <CardContent className="pl-2">
            <div className="h-[300px] w-full flex items-center justify-center">
              {isLoadingChart ? (
                <div className="flex flex-col items-center gap-2 text-muted-foreground">
                  <Skeleton className="h-full w-full rounded-md" />
                </div>
              ) : chartList.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No activity data available for this timeframe.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartList} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorSafe" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorBlocked" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#71717a" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false} 
                    />
                    <YAxis 
                      stroke="#71717a" 
                      fontSize={12} 
                      tickLine={false} 
                      axisLine={false} 
                      tickFormatter={(value) => `${value}`} 
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px' }}
                      itemStyle={{ color: '#e4e4e7' }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="safe" 
                      stroke="#10b981" 
                      fillOpacity={1} 
                      fill="url(#colorSafe)" 
                      name="Safe Actions"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="blocked" 
                      stroke="#ef4444" 
                      fillOpacity={1} 
                      fill="url(#colorBlocked)" 
                      name="Blocked Actions"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>
        
        <Card className="col-span-3 glass-panel">
          <CardHeader>
            <CardTitle>Recent Incidents</CardTitle>
            <CardDescription>Latest blocked actions requiring review</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {isLoadingIncidents ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4 py-2">
                    <Skeleton className="h-9 w-9 rounded-full" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-20" />
                    </div>
                    <Skeleton className="h-4 w-16" />
                  </div>
                ))
              ) : incidentsList.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
                  <ShieldCheck className="h-8 w-8 mb-2 text-emerald-500/50" />
                  <p className="text-sm font-medium">No recent incidents</p>
                  <p className="text-xs">All agents are operating safely.</p>
                </div>
              ) : (
                incidentsList.map((incident) => (
                  <div key={incident.id} className="flex items-center gap-4 border-b border-border pb-4 last:border-0 last:pb-0">
                    <div className={`flex h-9 w-9 items-center justify-center rounded-full bg-zinc-900 border border-zinc-800 ${getSeverityColor(incident.severity)}`}>
                      <ShieldAlert className="h-4 w-4" />
                    </div>
                    <div className="flex-1 space-y-1 overflow-hidden">
                      <p className="text-sm font-medium leading-none truncate">{incident.title}</p>
                      <p className="text-sm text-muted-foreground">{formatTimeAgo(incident.created_at)}</p>
                    </div>
                    <div className={`text-sm font-medium uppercase ${getSeverityColor(incident.severity)}`}>
                      {incident.severity}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

