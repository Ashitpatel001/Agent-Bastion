'use client';

import * as React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Shield, Lock, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function HeroSection() {
  return (
    <section className="relative overflow-hidden bg-background pt-24 pb-32">
      {/* Background gradients */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
      <div className="absolute left-1/2 top-0 -z-10 -translate-x-1/2 blur-3xl xl:-top-6" aria-hidden="true">
        <div className="aspect-[1155/678] w-[72.1875rem] bg-gradient-to-tr from-[#06b6d4] to-[#3b82f6] opacity-30" style={{ clipPath: 'polygon(74.1% 44.1%, 100% 61.6%, 97.5% 26.9%, 85.5% 0.1%, 80.7% 2%, 72.5% 32.5%, 60.2% 62.4%, 52.4% 68.1%, 47.5% 58.3%, 45.2% 34.5%, 27.5% 76.7%, 0.1% 64.9%, 17.9% 100%, 27.6% 76.8%, 76.1% 97.7%, 74.1% 44.1%)' }}></div>
      </div>
      
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-3xl"
        >
          <div className="mb-8 flex justify-center">
            <span className="relative rounded-full px-3 py-1 text-sm leading-6 text-cyan-400 ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 cursor-pointer transition-all bg-cyan-400/5 backdrop-blur-sm">
              Announcing ABSs v2.0 <ArrowRight className="inline-block ml-1 h-3 w-3" />
            </span>
          </div>
          
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl mb-6">
            The Zero-Trust Proxy for <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">Autonomous AI</span>
          </h1>
          
          <p className="mt-6 text-lg leading-8 text-muted-foreground max-w-2xl mx-auto">
            Protect your agents from prompt injections, data exfiltration, and unauthorized actions.
            ABSs sits between your LLM and the browser, intercepting threats in real-time.
          </p>
          
          <div className="mt-10 flex items-center justify-center gap-x-6">
            <Link href="/login">
              <Button size="lg" className="rounded-full px-8 bg-cyan-500 hover:bg-cyan-600 text-black font-semibold">
                Get Started <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="/docs">
              <Button size="lg" variant="outline" className="rounded-full px-8 glass">
                View Documentation
              </Button>
            </Link>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="mt-16 sm:mt-24 mx-auto max-w-5xl"
        >
          <div className="glass-panel rounded-xl p-2 md:p-4 shadow-2xl ring-1 ring-white/10 relative overflow-hidden">
            {/* Mock Dashboard UI */}
            <div className="rounded-lg bg-zinc-950 border border-zinc-800 overflow-hidden shadow-inner">
              <div className="flex items-center px-4 py-3 border-b border-zinc-800 bg-zinc-900/50">
                <div className="flex gap-2">
                  <div className="h-3 w-3 rounded-full bg-red-500/80"></div>
                  <div className="h-3 w-3 rounded-full bg-amber-500/80"></div>
                  <div className="h-3 w-3 rounded-full bg-emerald-500/80"></div>
                </div>
                <div className="mx-auto text-xs font-mono text-zinc-500 flex items-center gap-2">
                  <Lock className="size-3" /> soc.abs-security.com
                </div>
              </div>
              <div className="p-6 text-left grid md:grid-cols-3 gap-6">
                <div className="col-span-2 space-y-4 font-mono text-sm">
                  <div className="flex text-zinc-400 gap-4"><span className="text-blue-400">10:42:01</span> <span>Agent initiated session</span></div>
                  <div className="flex text-zinc-400 gap-4"><span className="text-blue-400">10:42:05</span> <span>Navigated to internal-wiki.acme.com</span></div>
                  <div className="flex text-amber-400 gap-4"><span className="text-blue-400">10:42:12</span> <span>WARNING: Detected suspicious DOM element</span></div>
                  <div className="flex text-red-500 font-semibold gap-4 bg-red-500/10 p-2 rounded"><span className="text-red-400">10:42:13</span> <span>BLOCKED: Data Exfiltration Attempt (T1048)</span></div>
                  <div className="flex text-zinc-400 gap-4"><span className="text-blue-400">10:42:14</span> <span>Agent session terminated safely.</span></div>
                </div>
                <div className="space-y-4">
                  <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
                    <div className="text-xs text-zinc-500 mb-1">THREAT SCORE</div>
                    <div className="text-3xl font-bold text-red-500 flex items-center gap-2">
                      94 <Activity className="size-5" />
                    </div>
                  </div>
                  <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
                    <div className="text-xs text-zinc-500 mb-1">SENTINEL STATUS</div>
                    <div className="text-emerald-500 font-medium flex items-center gap-2">
                      <Shield className="size-4" /> Active & Protecting
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
