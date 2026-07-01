'use client';

import * as React from 'react';
import { useSettings, useUpdateSettings } from '@/hooks/use-api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { Save, Loader2, Bell, Globe, Database, Shield } from 'lucide-react';

export default function SettingsPage() {
  const { data: settings, isLoading } = useSettings();
  const updateMutation = useUpdateSettings();

  const [email, setEmail] = React.useState('');
  const [webhook, setWebhook] = React.useState('');
  const [timezone, setTimezone] = React.useState('UTC');
  const [retention, setRetention] = React.useState(90);

  React.useEffect(() => {
    if (settings) {
      setEmail(settings.notification_email || '');
      setWebhook(settings.webhook_url || '');
      setTimezone(settings.timezone || 'UTC');
      setRetention(settings.data_retention_days || 90);
    }
  }, [settings]);

  async function handleSave() {
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

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="size-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-8 p-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Namespace Settings</h1>
        <p className="text-muted-foreground mt-1">Configure telemetry, webhooks, and retention rules for your autonomous agent proxy.</p>
      </div>

      <div className="space-y-6">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-4">
          <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
            <Bell className="size-5 text-primary" />
            <div>
              <h2 className="font-semibold text-lg">Alert Notifications</h2>
              <p className="text-sm text-muted-foreground">Receive instant alerts when critical security events trigger MITRE rules.</p>
            </div>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Notification Email</label>
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="security-alerts@acme.com"
              className="bg-zinc-900/80 max-w-md"
            />
          </div>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-4">
          <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
            <Globe className="size-5 text-primary" />
            <div>
              <h2 className="font-semibold text-lg">SIEM Webhook Integration</h2>
              <p className="text-sm text-muted-foreground">Stream live audit telemetry directly to Splunk, Datadog, or Slack.</p>
            </div>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Webhook URL</label>
            <Input
              value={webhook}
              onChange={(e) => setWebhook(e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              className="bg-zinc-900/80"
            />
          </div>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-4">
          <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
            <Database className="size-5 text-primary" />
            <div>
              <h2 className="font-semibold text-lg">Data & Telemetry Retention</h2>
              <p className="text-sm text-muted-foreground">Configure how long raw DOM snapshots and screenshots are preserved.</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-md">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Timezone</label>
              <Input
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="bg-zinc-900/80"
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Retention (Days)</label>
              <Input
                type="number"
                value={retention}
                onChange={(e) => setRetention(Number(e.target.value))}
                className="bg-zinc-900/80"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={updateMutation.isPending} className="gap-2 px-6">
            {updateMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
            Save Configuration
          </Button>
        </div>
      </div>
    </div>
  );
}
