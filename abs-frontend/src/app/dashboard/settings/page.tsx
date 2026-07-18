'use client';

import * as React from 'react';
import { useSettings, useUpdateSettings, useOrganizations, useCreateOrganization, useChangePassword } from '@/hooks/use-api';
import { useAppStore } from '@/store/app-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { Save, Loader2, Bell, Globe, Database, Shield, Building2, Lock, KeyRound, Plus, CheckCircle2 } from 'lucide-react';

export default function SettingsPage() {
  const { data: settings, isLoading } = useSettings();
  const updateMutation = useUpdateSettings();
  const { data: orgs, refetch: refetchOrgs } = useOrganizations();
  const createOrg = useCreateOrganization();
  const changePwd = useChangePassword();
  const { tenantName, tenantTier, userEmail } = useAppStore();

  // General state
  const [email, setEmail] = React.useState('');
  const [webhook, setWebhook] = React.useState('');
  const [timezone, setTimezone] = React.useState('UTC');
  const [retention, setRetention] = React.useState(90);

  // New Org state
  const [orgName, setOrgName] = React.useState('');
  const [orgEmail, setOrgEmail] = React.useState('');

  // Change Password state
  const [oldPassword, setOldPassword] = React.useState('');
  const [newPassword, setNewPassword] = React.useState('');

  React.useEffect(() => {
    if (settings) {
      setEmail(settings.notification_email || userEmail || '');
      setWebhook(settings.webhook_url || '');
      setTimezone(settings.timezone || 'UTC');
      setRetention(settings.data_retention_days || 90);
    }
  }, [settings, userEmail]);

  async function handleSaveGeneral() {
    try {
      await updateMutation.mutateAsync({
        notification_email: email,
        webhook_url: webhook,
        timezone: timezone,
        data_retention_days: Number(retention),
      });
      toast.success('Settings saved successfully!');
    } catch (error: any) {
      toast.error('Failed to update settings', { description: error.message });
    }
  }

  async function handleCreateOrg(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createOrg.mutateAsync({ name: orgName, email: orgEmail });
      toast.success('Organization Created!', { description: `Namespace ${orgName} registered.` });
      setOrgName('');
      setOrgEmail('');
      refetchOrgs();
    } catch (err: any) {
      toast.error('Failed to create organization', { description: err.message });
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    try {
      await changePwd.mutateAsync({ current_password: oldPassword, old_password: oldPassword, new_password: newPassword });

      toast.success('Password changed successfully!', { description: 'Token rotation triggered.' });
      setOldPassword('');
      setNewPassword('');
    } catch (err: any) {
      toast.error('Password update failed', { description: err.message });
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="size-8 animate-spin text-primary" />
      </div>
    );
  }

  const orgList = orgs?.items || [{ id: 'tnt_enterprise', name: tenantName || 'Enterprise Tenant', tier: tenantTier || 'ENTERPRISE', status: 'ACTIVE' }];

  return (
    <div className="space-y-8 pb-12 max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          <Shield className="size-8 text-primary" /> Control Plane Settings & Tenant Management
        </h1>
        <p className="text-zinc-400 mt-1">Configure telemetry webhooks, organization namespaces, and security credentials.</p>
      </div>

      <Tabs defaultValue="general" className="w-full">
        <TabsList className="grid w-full grid-cols-3 bg-zinc-900 border border-zinc-800 p-1 rounded-xl font-mono text-xs">
          <TabsTrigger value="general" className="rounded-lg">1. General & Webhooks</TabsTrigger>
          <TabsTrigger value="tenants" className="rounded-lg">2. Organizations & Namespaces</TabsTrigger>
          <TabsTrigger value="security" className="rounded-lg">3. Password & Security</TabsTrigger>
        </TabsList>

        {/* General Tab */}
        <TabsContent value="general" className="mt-6 space-y-6">
          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader className="border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-3">
                <Bell className="size-5 text-primary" />
                <div>
                  <CardTitle className="text-lg font-bold text-white">Alert & Notification Routing</CardTitle>
                  <CardDescription className="text-zinc-400">Receive instant alerts when critical security events trigger WAF rules.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="grid gap-2 max-w-md">
                <label className="text-xs font-semibold text-zinc-300">Notification Email</label>
                <Input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="security-alerts@acme.com"
                  className="bg-zinc-950 border-zinc-800 text-white rounded-xl"
                />
              </div>
            </CardContent>
          </Card>

          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader className="border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-3">
                <Globe className="size-5 text-primary" />
                <div>
                  <CardTitle className="text-lg font-bold text-white">SIEM Webhook Integration</CardTitle>
                  <CardDescription className="text-zinc-400">Stream live audit telemetry directly to Splunk, Datadog, or Slack.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="grid gap-2">
                <label className="text-xs font-semibold text-zinc-300">Webhook Endpoint URL</label>
                <Input
                  value={webhook}
                  onChange={(e) => setWebhook(e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                  className="bg-zinc-950 border-zinc-800 text-white rounded-xl"
                />
              </div>
            </CardContent>
          </Card>

          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader className="border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-3">
                <Database className="size-5 text-primary" />
                <div>
                  <CardTitle className="text-lg font-bold text-white">Data & Telemetry Retention</CardTitle>
                  <CardDescription className="text-zinc-400">Configure how long raw DOM snapshots and screenshots are preserved.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 gap-4 max-w-md">
              <div className="grid gap-2">
                <label className="text-xs font-semibold text-zinc-300">Timezone</label>
                <Input
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="bg-zinc-950 border-zinc-800 text-white rounded-xl"
                />
              </div>
              <div className="grid gap-2">
                <label className="text-xs font-semibold text-zinc-300">Retention (Days)</label>
                <Input
                  type="number"
                  value={retention}
                  onChange={(e) => setRetention(Number(e.target.value))}
                  className="bg-zinc-950 border-zinc-800 text-white rounded-xl"
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveGeneral} disabled={updateMutation.isPending} className="gap-2 px-8 py-6 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground font-semibold shadow-lg">
              {updateMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
              Save General Configuration
            </Button>
          </div>
        </TabsContent>

        {/* Tenants Tab */}
        <TabsContent value="tenants" className="mt-6 space-y-6">
          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader className="border-b border-zinc-800 pb-4">
              <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                <Building2 className="size-5 text-cyan-400" /> Active Organizations & Namespaces
              </CardTitle>
              <CardDescription className="text-zinc-400">Isolated database schemas managed under your admin account</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-left border-collapse font-mono text-xs">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-400 bg-zinc-950/60">
                    <th className="py-3 px-4 font-semibold">TENANT ID</th>
                    <th className="py-3 px-4 font-semibold">ORGANIZATION NAME</th>
                    <th className="py-3 px-4 font-semibold">TIER</th>
                    <th className="py-3 px-4 font-semibold text-right">STATUS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60 text-zinc-300 font-sans">
                  {orgList.map((o: any, idx: number) => (
                    <tr key={idx} className="hover:bg-zinc-900/40">
                      <td className="py-3 px-4 font-mono font-bold text-primary">{o.id || `tnt_${idx + 1}`}</td>
                      <td className="py-3 px-4 font-bold text-white">{o.name || 'Enterprise Namespace'}</td>
                      <td className="py-3 px-4 font-mono text-cyan-400">{o.tier || 'ENTERPRISE'}</td>
                      <td className="py-3 px-4 text-right">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          {o.status || 'ACTIVE'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader className="border-b border-zinc-800 pb-4">
              <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="size-5 text-primary" /> Register New Tenant Namespace (`/api/v1/organizations`)
              </CardTitle>
              <CardDescription className="text-zinc-400">Create a dedicated multi-tenant boundary for another team or project</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <form onSubmit={handleCreateOrg} className="space-y-4 max-w-md">
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1">Organization Name</label>
                  <Input
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="Acme Autonomous Labs"
                    className="bg-zinc-950 border-zinc-800 text-white rounded-xl"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1">Admin Email</label>
                  <Input
                    type="email"
                    value={orgEmail}
                    onChange={(e) => setOrgEmail(e.target.value)}
                    placeholder="admin@acme.com"
                    className="bg-zinc-950 border-zinc-800 text-white rounded-xl"
                    required
                  />
                </div>
                <Button type="submit" disabled={createOrg.isPending} className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-6 py-6 rounded-xl shadow-lg">
                  {createOrg.isPending ? 'Registering Namespace...' : 'Create Isolated Namespace'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="mt-6 space-y-6">
          <Card className="glass-panel bg-zinc-900/60 border-zinc-800">
            <CardHeader className="border-b border-zinc-800 pb-4">
              <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                <Lock className="size-5 text-emerald-400" /> Change Control Plane Password (`/api/v1/auth/password`)
              </CardTitle>
              <CardDescription className="text-zinc-400">Rotate user credentials and force refresh token expiration</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1">Current Password</label>
                  <Input
                    type="password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    placeholder="••••••••"
                    className="bg-zinc-950 border-zinc-800 text-white rounded-xl"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1">New Password (Min 8 chars)</label>
                  <Input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                    className="bg-zinc-950 border-zinc-800 text-white rounded-xl"
                    required
                  />
                </div>
                <Button type="submit" disabled={changePwd.isPending} className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-6 py-6 rounded-xl shadow-lg">
                  {changePwd.isPending ? 'Updating Credentials...' : 'Update Password & Rotate Tokens'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
