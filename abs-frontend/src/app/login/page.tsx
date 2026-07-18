'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { useLogin, useRegisterV1, useResetPassword } from '@/hooks/use-api';
import { useAppStore } from '@/store/app-store';
import { APP_NAME } from '@/lib/constants';
import { TenantTier } from '@/types';
import { ShieldCheck, ArrowRight, Loader2, KeyRound, Lock, Mail, Building, CheckCircle2, Shield, RefreshCw, Key, Users } from 'lucide-react';
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

const forgotSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid registered email address.' }),
});

export default function LoginPage() {
  const router = useRouter();
  const loginMutation = useLogin();
  const registerMutation = useRegisterV1();
  const resetMutation = useResetPassword();
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

  const forgotForm = useForm<z.infer<typeof forgotSchema>>({
    resolver: zodResolver(forgotSchema),
    defaultValues: {
      email: '',
    },
  });

  async function onLoginSubmit(values: z.infer<typeof loginSchema>) {
    try {
      const res = await loginMutation.mutateAsync(values);
      const tenantId = res.tenant_id || 'tnt_default';
      const apiKey = res.access_token || 'abs_live_demo_key'; // Use JWT access token
      const tenantName = res.tenant_name || 'Enterprise Tenant';
      
      setCredentials(
        tenantId,
        apiKey,
        tenantName,
        values.email,
        TenantTier.ENTERPRISE
      );

      toast.success('Signed in successfully against API v1!', {
        description: 'JWT access token & refresh token rotation active.',
      });
      router.push('/dashboard/playground');
    } catch (error: any) {
      toast.error('Sign in failed', {
        description: error.message || 'Verify your credentials against API v1.',
      });
    }
  }

  async function onRegisterSubmit(values: z.infer<typeof registerSchema>) {
    try {
      await registerMutation.mutateAsync(values);
      toast.success('Organization & Namespace registered!', {
        description: 'Your account has been created. Please sign in.',
      });
      setActiveTab('signin');
    } catch (error: any) {
      toast.error('Registration failed', {
        description: error.message || 'An error occurred while creating namespace.',
      });
    }
  }

  async function onForgotSubmit(values: z.infer<typeof forgotSchema>) {
    try {
      await resetMutation.mutateAsync(values.email);
      toast.success('Password reset link dispatched!', {
        description: `If an account exists for ${values.email}, instructions have been sent via secure email gateway.`,
      });
      setActiveTab('signin');
    } catch (error: any) {
      toast.success('Password reset link dispatched!', {
        description: `If an account exists for ${values.email}, instructions have been sent via secure email gateway.`,
      });
      setActiveTab('signin');
    }
  }

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100 font-sans">
      {/* Left side - Authentication Form */}
      <div className="flex flex-1 flex-col justify-center px-6 py-12 lg:flex-none lg:px-20 xl:px-24 border-r border-zinc-800 bg-zinc-950/90 z-10">
        <div className="mx-auto w-full max-w-sm lg:w-96">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-2.5">
              <div className="flex aspect-square size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
                <ShieldCheck className="size-6" />
              </div>
              <div className="flex flex-col leading-none">
                <span className="text-xl font-extrabold tracking-tight text-white">{APP_NAME}</span>
                <span className="text-[10px] font-mono text-primary font-bold uppercase mt-0.5">Control Plane Auth</span>
              </div>
            </div>
            <span className="text-xs bg-zinc-900 border border-zinc-800 text-zinc-400 px-2.5 py-1 rounded-md font-mono">
              v2.0
            </span>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-6 bg-zinc-900 border border-zinc-800 p-1 rounded-xl">
              <TabsTrigger value="signin" className="rounded-lg text-xs font-semibold">Login</TabsTrigger>
              <TabsTrigger value="register" className="rounded-lg text-xs font-semibold">Sign Up</TabsTrigger>
              <TabsTrigger value="forgot" className="rounded-lg text-xs font-semibold">Reset</TabsTrigger>
            </TabsList>

            {/* Login / Sign In */}
            <TabsContent value="signin" className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-white">
                  Sign In to Control Plane
                </h2>
                <p className="mt-1 text-sm text-zinc-400">
                  Authenticate against API v1 with JWT & RBAC enforcement.
                </p>
              </div>

              <Form {...loginForm}>
                <form onSubmit={loginForm.handleSubmit(onLoginSubmit)} className="space-y-4">
                  <FormField
                    control={loginForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-zinc-300 font-semibold text-xs">Work Email</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Mail className="absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
                            <Input placeholder="admin@abss.internal" {...field} className="pl-10 bg-zinc-900 border-zinc-800 text-white rounded-xl focus:border-primary" />
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
                        <div className="flex items-center justify-between">
                          <FormLabel className="text-zinc-300 font-semibold text-xs">Password</FormLabel>
                          <button
                            type="button"
                            onClick={() => setActiveTab('forgot')}
                            className="text-xs text-primary hover:underline font-mono"
                          >
                            Forgot password?
                          </button>
                        </div>
                        <FormControl>
                          <div className="relative">
                            <Lock className="absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
                            <Input type="password" placeholder="••••••••" {...field} className="pl-10 bg-zinc-900 border-zinc-800 text-white rounded-xl focus:border-primary" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <Button type="submit" className="w-full group mt-2 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-xl py-6 shadow-lg shadow-primary/20" disabled={loginMutation.isPending}>
                    {loginMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        Sign In & Authenticate <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                      </>
                    )}
                  </Button>
                </form>
              </Form>
            </TabsContent>

            {/* Register / Sign Up */}
            <TabsContent value="register" className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-white">
                  Create Organization Namespace
                </h2>
                <p className="mt-1 text-sm text-zinc-400">
                  Deploy a dedicated multi-tenant zero-trust gateway for your AI agents.
                </p>
              </div>

              <Form {...registerForm}>
                <form onSubmit={registerForm.handleSubmit(onRegisterSubmit)} className="space-y-4">
                  <FormField
                    control={registerForm.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-zinc-300 font-semibold text-xs">Organization Name</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Building className="absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
                            <Input placeholder="Acme Corp AI Labs" {...field} className="pl-10 bg-zinc-900 border-zinc-800 text-white rounded-xl focus:border-primary" />
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
                        <FormLabel className="text-zinc-300 font-semibold text-xs">Admin Email</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Mail className="absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
                            <Input type="email" placeholder="security@acme.com" {...field} className="pl-10 bg-zinc-900 border-zinc-800 text-white rounded-xl focus:border-primary" />
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
                        <FormLabel className="text-zinc-300 font-semibold text-xs">Admin Password</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Lock className="absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
                            <Input type="password" placeholder="Min. 8 characters" {...field} className="pl-10 bg-zinc-900 border-zinc-800 text-white rounded-xl focus:border-primary" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <Button type="submit" className="w-full group mt-2 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-xl py-6 shadow-lg shadow-primary/20" disabled={registerMutation.isPending}>
                    {registerMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        Sign Up & Initialize Namespace <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                      </>
                    )}
                  </Button>
                </form>
              </Form>
            </TabsContent>

            {/* Forgot Password */}
            <TabsContent value="forgot" className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-white">
                  Forgot Password
                </h2>
                <p className="mt-1 text-sm text-zinc-400">
                  Enter your registered admin email to request a secure password reset token.
                </p>
              </div>

              <Form {...forgotForm}>
                <form onSubmit={forgotForm.handleSubmit(onForgotSubmit)} className="space-y-4">
                  <FormField
                    control={forgotForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-zinc-300 font-semibold text-xs">Registered Admin Email</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Mail className="absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
                            <Input type="email" placeholder="admin@abss.internal" {...field} className="pl-10 bg-zinc-900 border-zinc-800 text-white rounded-xl focus:border-primary" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <Button type="submit" className="w-full group mt-2 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-xl py-6 shadow-lg shadow-primary/20" disabled={resetMutation.isPending}>
                    {resetMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        Dispatch Reset Token <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                      </>
                    )}
                  </Button>

                  <div className="text-center mt-4">
                    <button
                      type="button"
                      onClick={() => setActiveTab('signin')}
                      className="text-xs text-zinc-400 hover:text-white font-mono"
                    >
                      ← Back to Login
                    </button>
                  </div>
                </form>
              </Form>
            </TabsContent>
          </Tabs>

          {/* Security Features & Session Management Note */}
          <div className="mt-8 pt-6 border-t border-zinc-900 space-y-3">
            <h4 className="text-xs font-mono uppercase tracking-wider text-zinc-500 font-bold">Production Auth Safeguards</h4>
            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-zinc-400">
              <div className="flex items-center gap-1.5 bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/80">
                <Shield className="size-3.5 text-emerald-400 shrink-0" />
                <span>JWT Access Token</span>
              </div>
              <div className="flex items-center gap-1.5 bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/80">
                <RefreshCw className="size-3.5 text-cyan-400 shrink-0" />
                <span>Token Rotation</span>
              </div>
              <div className="flex items-center gap-1.5 bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/80">
                <Key className="size-3.5 text-amber-400 shrink-0" />
                <span>API Key Scopes</span>
              </div>
              <div className="flex items-center gap-1.5 bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/80">
                <Users className="size-3.5 text-purple-400 shrink-0" />
                <span>RBAC Support</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Visual & Technical Matrix */}
      <div className="relative hidden w-0 flex-1 lg:block bg-zinc-950 overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:28px_28px]"></div>
        <div className="absolute left-1/4 top-1/3 -z-10 h-[380px] w-[380px] rounded-full bg-primary/20 opacity-25 blur-[120px]"></div>
        <div className="absolute right-1/4 bottom-1/4 -z-10 h-[300px] w-[300px] rounded-full bg-cyan-500/15 opacity-20 blur-[100px]"></div>
        
        <div className="flex h-full flex-col justify-center p-16 xl:p-24">
          <div className="glass-panel rounded-2xl p-8 max-w-2xl shadow-2xl relative border border-zinc-800 bg-zinc-900/50 backdrop-blur-2xl">
            <div className="absolute -top-3.5 right-6 bg-primary text-primary-foreground px-3.5 py-1 rounded-full text-xs font-mono font-bold shadow-lg shadow-primary/25 flex items-center gap-1.5">
              <KeyRound className="size-3.5" /> API v1 Connected
            </div>
            <h3 className="text-xl font-bold mb-4 text-white flex items-center gap-2.5">
              <span className="size-2.5 rounded-full bg-emerald-500 animate-pulse" /> Zero-Trust Autonomous Agent Gateway
            </h3>
            <div className="font-mono text-xs text-zinc-300 space-y-3 leading-relaxed">
              <p className="flex items-start gap-2.5">
                <span className="text-emerald-400 font-bold">➜</span> 
                <span>All routes verified by <span className="text-white font-bold">FastAPI + OAuth2/JWT Bearer</span> authentication layer.</span>
              </p>
              <p className="flex items-start gap-2.5">
                <span className="text-emerald-400 font-bold">➜</span> 
                <span>Role-Based Access Control (RBAC): Owner, Admin, Operator, Security Analyst, Developer, Viewer.</span>
              </p>
              <p className="flex items-start gap-2.5">
                <span className="text-emerald-400 font-bold">➜</span> 
                <span>Session Management: Automatic refresh token rotation & PostgreSQL revocation on password change or logout.</span>
              </p>
              <p className="flex items-start gap-2.5">
                <span className="text-emerald-400 font-bold">➜</span> 
                <span>Proxies outbound LLM requests, checking DOM structures against MITRE ATT&CK T1566 and prompt injections.</span>
              </p>
            </div>
            
            <div className="mt-6 pt-5 border-t border-zinc-800/80 flex items-center justify-between text-xs text-zinc-500 font-mono">
              <span>Status: <span className="text-emerald-400 font-bold">LISTENING ON PORT 8000</span></span>
              <span>Mode: <span className="text-cyan-400 font-bold">MULTI-TENANT ISOLATION</span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
