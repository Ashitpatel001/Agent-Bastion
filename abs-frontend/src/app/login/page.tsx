'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { useLogin, useRegisterV1 } from '@/hooks/use-api';
import { useAppStore } from '@/store/app-store';
import { APP_NAME } from '@/lib/constants';
import { TenantTier } from '@/types';
import { ShieldCheck, ArrowRight, Loader2, KeyRound, Lock, Mail, Building } from 'lucide-react';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const loginSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email address.' }),
  password: z.string().min(1, { message: 'Password is required.' }),
});

const registerSchema = z.object({
  name: z.string().min(2, { message: 'Organization name must be at least 2 characters.' }),
  email: z.string().email({ message: 'Please enter a valid email address.' }),
  password: z.string().min(8, { message: 'Password must be at least 8 characters.' }),
});

export default function LoginPage() {
  const router = useRouter();
  const loginMutation = useLogin();
  const registerMutation = useRegisterV1();
  const setCredentials = useAppStore((state) => state.setCredentials);
  const [activeTab, setActiveTab] = React.useState('signin');

  const loginForm = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: 'admin@abss.internal',
      password: 'Admin123!',
    },
  });

  const registerForm = useForm<z.infer<typeof registerSchema>>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: '',
      email: '',
      password: '',
    },
  });

  async function onLoginSubmit(values: z.infer<typeof loginSchema>) {
    try {
      const res = await loginMutation.mutateAsync(values);
      // Fallback ID/Key for sign-in session if API key wasn't explicitly returned
      const tenantId = res.tenant_id || 'tnt_default';
      const apiKey = res.access_token || 'abs_live_demo_key';
      const tenantName = res.tenant_name || 'Enterprise Tenant';
      
      setCredentials(
        tenantId,
        apiKey,
        tenantName,
        values.email,
        TenantTier.ENTERPRISE
      );

      toast.success('Signed in successfully!', {
        description: 'Authenticated against API v1.',
      });
      router.push('/dashboard/overview');
    } catch (error: any) {
      toast.error('Sign in failed', {
        description: error.message || 'Check your credentials.',
      });
    }
  }

  async function onRegisterSubmit(values: z.infer<typeof registerSchema>) {
    try {
      const response = await registerMutation.mutateAsync(values);
      setCredentials(
        response.tenant_id,
        response.raw_api_key,
        response.tenant_name,
        values.email,
        TenantTier.PRO
      );
      toast.success('Namespace created successfully!', {
        description: 'Your API key and user account have been initialized.',
      });
      router.push('/dashboard/overview');
    } catch (error: any) {
      toast.error('Registration failed', {
        description: error.message || 'An error occurred while registering namespace.',
      });
    }
  }

  return (
    <div className="flex min-h-screen bg-background">
      {/* Left side - Form */}
      <div className="flex flex-1 flex-col justify-center px-4 py-12 sm:px-6 lg:flex-none lg:px-20 xl:px-24 border-r border-border">
        <div className="mx-auto w-full max-w-sm lg:w-96">
          <div className="flex items-center gap-2 mb-8">
            <div className="flex aspect-square size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
              <ShieldCheck className="size-6" />
            </div>
            <span className="text-2xl font-bold tracking-tight">{APP_NAME} <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-md font-mono">v2.0</span></span>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="signin">Sign In</TabsTrigger>
              <TabsTrigger value="register">Register Namespace</TabsTrigger>
            </TabsList>

            <TabsContent value="signin" className="space-y-6">
              <div>
                <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                  Welcome back
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Sign in to access your autonomous security console.
                </p>
              </div>

              <Form {...loginForm}>
                <form onSubmit={loginForm.handleSubmit(onLoginSubmit)} className="space-y-4">
                  <FormField
                    control={loginForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Work Email</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input placeholder="admin@abss.internal" {...field} className="pl-9 bg-zinc-900/50" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={loginForm.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Password</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input type="password" placeholder="••••••••" {...field} className="pl-9 bg-zinc-900/50" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <Button type="submit" className="w-full group mt-2" disabled={loginMutation.isPending}>
                    {loginMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        Sign In <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                      </>
                    )}
                  </Button>
                </form>
              </Form>
            </TabsContent>

            <TabsContent value="register" className="space-y-6">
              <div>
                <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                  Create Namespace
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Deploy a dedicated zero-trust firewall for your agents.
                </p>
              </div>

              <Form {...registerForm}>
                <form onSubmit={registerForm.handleSubmit(onRegisterSubmit)} className="space-y-4">
                  <FormField
                    control={registerForm.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Organization Name</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Building className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input placeholder="Acme Corp AI Labs" {...field} className="pl-9 bg-zinc-900/50" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={registerForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Admin Email</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input type="email" placeholder="security@acme.com" {...field} className="pl-9 bg-zinc-900/50" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={registerForm.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Admin Password</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input type="password" placeholder="Min. 8 characters" {...field} className="pl-9 bg-zinc-900/50" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <Button type="submit" className="w-full group mt-2" disabled={registerMutation.isPending}>
                    {registerMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        Register Namespace <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                      </>
                    )}
                  </Button>
                </form>
              </Form>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Right side - Visual */}
      <div className="relative hidden w-0 flex-1 lg:block bg-zinc-950 overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
        <div className="absolute left-0 right-0 top-0 -z-10 m-auto h-[310px] w-[310px] rounded-full bg-primary/20 opacity-20 blur-[100px]"></div>
        
        <div className="flex h-full flex-col justify-center p-16">
          <div className="glass-panel rounded-2xl p-8 max-w-2xl shadow-2xl relative border border-zinc-800 bg-zinc-900/40 backdrop-blur-xl">
            <div className="absolute -top-4 -right-4 bg-primary text-primary-foreground px-4 py-1 rounded-full text-xs font-bold shadow-lg shadow-primary/20 flex items-center gap-1.5">
              <KeyRound className="size-3.5" /> API v1 Connected
            </div>
            <h3 className="text-xl font-medium mb-4 text-zinc-200 flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse" /> Active Protection Matrix
            </h3>
            <div className="font-mono text-sm text-zinc-400 space-y-2">
              <p className="flex items-center gap-2"><span className="text-emerald-500">➜</span> <span>Routing endpoints to <span className="text-primary font-bold">/api/v1/...</span></span></p>
              <p className="flex items-center gap-2"><span className="text-emerald-500">➜</span> <span>Action Sentinel DOM Inspection: <span className="text-emerald-400">ONLINE</span></span></p>
              <p className="flex items-center gap-2"><span className="text-emerald-500">➜</span> <span>XAI Explainability Worker: <span className="text-emerald-400">ACTIVE</span></span></p>
              <p className="flex items-center gap-2"><span className="text-emerald-500">➜</span> <span className="text-zinc-200">Listening on port 8000 for autonomous agent traffic...</span></p>
              <br />
              <p className="text-xs text-zinc-500">// Protected against prompt injection, credential dumping, and MITRE ATT&CK T1566.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
