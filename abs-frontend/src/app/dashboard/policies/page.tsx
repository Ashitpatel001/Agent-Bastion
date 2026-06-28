'use client';

import * as React from 'react';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { useActivePolicy, useUpdatePolicy } from '@/hooks/use-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Loader2, ShieldCheck, Plus, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const formSchema = z.object({
  is_active: z.boolean(),
  require_human_approval: z.boolean(),
  max_risk_tolerance: z.number().min(0).max(100),
  blocked_domains: z.array(z.string()),
  trusted_domains: z.array(z.string()),
  blocked_actions: z.array(z.string()),
});

export default function PoliciesPage() {
  const { data: policy, isLoading: isPolicyLoading } = useActivePolicy();
  const updatePolicy = useUpdatePolicy();
  
  const [newBlockedDomain, setNewBlockedDomain] = React.useState('');
  const [newTrustedDomain, setNewTrustedDomain] = React.useState('');
  const [newBlockedAction, setNewBlockedAction] = React.useState('');
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      is_active: true,
      require_human_approval: false,
      max_risk_tolerance: 50,
      blocked_domains: [],
      trusted_domains: [],
      blocked_actions: [],
    },
  });

  React.useEffect(() => {
    if (policy) {
      form.reset({
        is_active: policy.is_active ?? true,
        require_human_approval: policy.require_human_approval ?? false,
        max_risk_tolerance: policy.max_risk_tolerance ?? 50,
        blocked_domains: policy.blocked_domains ?? [],
        trusted_domains: policy.trusted_domains ?? [],
        blocked_actions: policy.blocked_actions ?? [],
      });
    }
  }, [policy, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      await updatePolicy.mutateAsync(values);
      toast.success('Security policy updated', {
        description: 'Changes have been deployed to the Action Sentinel.',
      });
    } catch (error: any) {
      toast.error('Update failed', {
        description: error.message || 'An error occurred while updating the policy.',
      });
    }
  }
  
  const addToArray = (field: 'blocked_domains' | 'trusted_domains' | 'blocked_actions', value: string, setter: React.Dispatch<React.SetStateAction<string>>) => {
    if (!value.trim()) return;
    const current = form.getValues(field);
    if (!current.includes(value.trim())) {
      form.setValue(field, [...current, value.trim()], { shouldDirty: true });
    }
    setter('');
  };
  
  const removeFromArray = (field: 'blocked_domains' | 'trusted_domains' | 'blocked_actions', index: number) => {
    const current = [...form.getValues(field)];
    current.splice(index, 1);
    form.setValue(field, current, { shouldDirty: true });
  };

  if (isPolicyLoading) {
    return <div className="flex h-[400px] items-center justify-center"><Loader2 className="size-8 animate-spin text-muted-foreground" /></div>;
  }

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto h-full">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Security Policies</h1>
        <p className="text-muted-foreground">
          Configure the boundaries and constraints for your autonomous agents.
        </p>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card className="glass-panel border-cyan-900/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="size-5 text-cyan-500" /> Core Engine Settings
              </CardTitle>
              <CardDescription>
                Global toggles for the proxy protection layer.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">Active Protection</FormLabel>
                      <FormDescription>
                        When disabled, the proxy allows all traffic without inspection. Use with extreme caution.
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="require_human_approval"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">Require Human Approval (HITL)</FormLabel>
                      <FormDescription>
                        Suspend agent actions that exceed the risk tolerance until manually approved.
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
              
              <FormField
                control={form.control}
                name="max_risk_tolerance"
                render={({ field }) => (
                  <FormItem className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                    <div className="flex justify-between mb-4 items-center">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base">Maximum Risk Tolerance ({field.value})</FormLabel>
                        <FormDescription>
                          Any action evaluated above this score (0-100) will be blocked or flagged.
                        </FormDescription>
                      </div>
                      <Badge variant={field.value > 70 ? 'destructive' : 'default'} className="h-6">
                        Score: {field.value}
                      </Badge>
                    </div>
                    <FormControl>
                      <input 
                        type="range"
                        min="0"
                        max="100"
                        value={field.value}
                        onChange={(e) => field.onChange(parseInt(e.target.value))}
                        className="w-full accent-cyan-500"
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <div className="grid md:grid-cols-2 gap-6">
            <Card className="glass">
              <CardHeader>
                <CardTitle className="text-lg">Network Filtering</CardTitle>
                <CardDescription>Control which domains agents can access.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <Label>Blocked Domains (Denylist)</Label>
                  <div className="flex gap-2">
                    <Input 
                      placeholder="e.g. *.ru, bit.ly" 
                      value={newBlockedDomain}
                      onChange={(e) => setNewBlockedDomain(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addToArray('blocked_domains', newBlockedDomain, setNewBlockedDomain); } }}
                    />
                    <Button type="button" variant="secondary" onClick={() => addToArray('blocked_domains', newBlockedDomain, setNewBlockedDomain)}>
                      <Plus className="size-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {form.watch('blocked_domains').map((domain, idx) => (
                      <Badge key={idx} variant="destructive" className="flex items-center gap-1 pr-1 bg-red-950/50 text-red-400 border-red-900/50">
                        {domain}
                        <div className="hover:bg-red-900/50 rounded-full p-0.5 cursor-pointer" onClick={() => removeFromArray('blocked_domains', idx)}>
                          <X className="size-3" />
                        </div>
                      </Badge>
                    ))}
                  </div>
                </div>
                
                <div className="space-y-3">
                  <Label>Trusted Domains (Allowlist)</Label>
                  <div className="flex gap-2">
                    <Input 
                      placeholder="e.g. github.com, *.internal.acme" 
                      value={newTrustedDomain}
                      onChange={(e) => setNewTrustedDomain(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addToArray('trusted_domains', newTrustedDomain, setNewTrustedDomain); } }}
                    />
                    <Button type="button" variant="secondary" onClick={() => addToArray('trusted_domains', newTrustedDomain, setNewTrustedDomain)}>
                      <Plus className="size-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {form.watch('trusted_domains').map((domain, idx) => (
                      <Badge key={idx} variant="outline" className="flex items-center gap-1 pr-1 bg-emerald-950/30 text-emerald-400 border-emerald-900/50">
                        {domain}
                        <div className="hover:bg-emerald-900/50 rounded-full p-0.5 cursor-pointer" onClick={() => removeFromArray('trusted_domains', idx)}>
                          <X className="size-3" />
                        </div>
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="glass">
              <CardHeader>
                <CardTitle className="text-lg">Behavioral Controls</CardTitle>
                <CardDescription>Restrict specific agent capabilities.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <Label>Blocked Actions</Label>
                  <div className="flex gap-2">
                    <Input 
                      placeholder="e.g. form_submit, file_download" 
                      value={newBlockedAction}
                      onChange={(e) => setNewBlockedAction(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addToArray('blocked_actions', newBlockedAction, setNewBlockedAction); } }}
                    />
                    <Button type="button" variant="secondary" onClick={() => addToArray('blocked_actions', newBlockedAction, setNewBlockedAction)}>
                      <Plus className="size-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {form.watch('blocked_actions').map((action, idx) => (
                      <Badge key={idx} variant="secondary" className="flex items-center gap-1 pr-1">
                        {action}
                        <div className="hover:bg-zinc-700 rounded-full p-0.5 cursor-pointer" onClick={() => removeFromArray('blocked_actions', idx)}>
                          <X className="size-3" />
                        </div>
                      </Badge>
                    ))}
                    {form.watch('blocked_actions').length === 0 && (
                      <span className="text-sm text-muted-foreground">No explicit actions blocked.</span>
                    )}
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex-col items-start pt-6 bg-zinc-900/30 mt-6 border-t border-zinc-800 rounded-b-xl">
                <p className="text-xs text-muted-foreground mb-4">
                  Note: The XAI Sentinel will still automatically block highly dangerous actions regardless of these settings if they exceed the risk tolerance threshold.
                </p>
                <Button type="submit" disabled={updatePolicy.isPending || !form.formState.isDirty} className="w-full">
                  {updatePolicy.isPending && <Loader2 className="mr-2 size-4 animate-spin" />}
                  Deploy Policy Updates
                </Button>
              </CardFooter>
            </Card>
          </div>
        </form>
      </Form>
    </div>
  );
}
