'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { useRegisterTenant } from '@/hooks/use-api';
import { useAppStore } from '@/store/app-store';
import { APP_NAME } from '@/lib/constants';
import { ShieldCheck, ArrowRight, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';

const formSchema = z.object({
  name: z.string().min(2, { message: 'Organization name must be at least 2 characters.' }),
  email: z.string().email({ message: 'Please enter a valid email address.' }),
});

export default function LoginPage() {
  const router = useRouter();
  const registerTenant = useRegisterTenant();
  const setCredentials = useAppStore((state) => state.setCredentials);
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      email: '',
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      const response = await registerTenant.mutateAsync(values);
      
      setCredentials(
        response.tenant.id,
        response.raw_api_key,
        response.tenant.name,
        response.tenant.email,
        response.tenant.tier
      );
      
      toast.success('Registration successful!', {
        description: 'Your API key has been securely stored in your browser session.',
      });
      
      router.push('/dashboard/overview');
    } catch (error: any) {
      toast.error('Registration failed', {
        description: error.message || 'An error occurred while creating your tenant.',
      });
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Left side - Form */}
      <div className="flex flex-1 flex-col justify-center px-4 py-12 sm:px-6 lg:flex-none lg:px-20 xl:px-24 border-r border-border bg-background">
        <div className="mx-auto w-full max-w-sm lg:w-96">
          <div className="flex items-center gap-2 mb-8">
            <div className="flex aspect-square size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
              <ShieldCheck className="size-6" />
            </div>
            <span className="text-2xl font-bold tracking-tight">{APP_NAME}</span>
          </div>
          
          <h2 className="mt-8 text-2xl font-semibold tracking-tight text-foreground">
            Sign in to your SOC Console
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Register a new tenant namespace to get started. No credit card required.
          </p>

          <div className="mt-10">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Organization Name</FormLabel>
                      <FormControl>
                        <Input placeholder="Acme Corp" {...field} className="bg-zinc-900/50" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Work Email</FormLabel>
                      <FormControl>
                        <Input type="email" placeholder="security@acme.com" {...field} className="bg-zinc-900/50" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Button 
                  type="submit" 
                  className="w-full group" 
                  disabled={registerTenant.isPending}
                >
                  {registerTenant.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      Continue <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </>
                  )}
                </Button>
              </form>
            </Form>
          </div>
        </div>
      </div>

      {/* Right side - Visual */}
      <div className="relative hidden w-0 flex-1 lg:block bg-zinc-950 overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
        <div className="absolute left-0 right-0 top-0 -z-10 m-auto h-[310px] w-[310px] rounded-full bg-primary/20 opacity-20 blur-[100px]"></div>
        
        <div className="flex h-full flex-col justify-center p-16">
          <div className="glass-panel rounded-2xl p-8 max-w-2xl shadow-2xl relative">
            <div className="absolute -top-4 -right-4 bg-primary text-primary-foreground px-4 py-1 rounded-full text-xs font-bold shadow-lg shadow-primary/20">
              Zero-Trust Architecture
            </div>
            <h3 className="text-xl font-medium mb-4 text-zinc-200">Terminal Output</h3>
            <div className="font-mono text-sm text-zinc-400 space-y-2">
              <p className="flex items-center gap-2"><span className="text-emerald-500">➜</span> <span>Initializing secure proxy sandbox...</span></p>
              <p className="flex items-center gap-2"><span className="text-emerald-500">➜</span> <span>Establishing isolated DOM environment...</span></p>
              <p className="flex items-center gap-2"><span className="text-emerald-500">➜</span> <span>Injecting Action Sentinel layer...</span></p>
              <p className="flex items-center gap-2"><span className="text-emerald-500">➜</span> <span className="text-zinc-200">Waiting for agent instructions...</span></p>
              <br />
              <p className="text-xs text-zinc-500">// Your agents are now shielded from prompt injections and data exfiltration.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
