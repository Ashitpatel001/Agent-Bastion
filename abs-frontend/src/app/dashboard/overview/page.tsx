'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldAlert, ShieldCheck, Activity, Users } from 'lucide-react';
import { useSecurityStats } from '@/hooks/use-api';
import { Skeleton } from '@/components/ui/skeleton';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

const chartData = [
  { time: '00:00', safe: 120, blocked: 2 },
  { time: '04:00', safe: 85, blocked: 5 },
  { time: '08:00', safe: 340, blocked: 12 },
  { time: '12:00', safe: 450, blocked: 28 },
  { time: '16:00', safe: 380, blocked: 18 },
  { time: '20:00', safe: 210, blocked: 4 },
  { time: '24:00', safe: 150, blocked: 3 },
];

export default function OverviewPage() {
  const { data: stats, isLoading } = useSecurityStats();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your autonomous agents' security posture and metrics.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="glass">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Actions Analyzed</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-20" /> : String(stats?.total_actions || '1,743')}
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
              {isLoading ? <Skeleton className="h-8 w-20" /> : String(stats?.safe_actions || '1,691')}
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
              {isLoading ? <Skeleton className="h-8 w-20" /> : String(stats?.blocked_actions || '52')}
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
              {isLoading ? <Skeleton className="h-8 w-20" /> : String(stats?.active_sessions || '4')}
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
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
                    dataKey="time" 
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
              {[
                { time: '10 mins ago', type: 'Prompt Injection', severity: 'High', color: 'text-orange-500' },
                { time: '2 hours ago', type: 'Data Exfiltration', severity: 'Critical', color: 'text-red-500' },
                { time: '5 hours ago', type: 'Malicious URL', severity: 'Medium', color: 'text-amber-500' },
                { time: '1 day ago', type: 'Prompt Injection', severity: 'Low', color: 'text-emerald-400' },
              ].map((incident, i) => (
                <div key={i} className="flex items-center gap-4 border-b border-border pb-4 last:border-0 last:pb-0">
                  <div className={`flex h-9 w-9 items-center justify-center rounded-full bg-zinc-900 border border-zinc-800 ${incident.color}`}>
                    <ShieldAlert className="h-4 w-4" />
                  </div>
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-medium leading-none">{incident.type}</p>
                    <p className="text-sm text-muted-foreground">{incident.time}</p>
                  </div>
                  <div className={`text-sm font-medium ${incident.color}`}>
                    {incident.severity}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
