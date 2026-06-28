import { HeroSection } from '@/components/landing/hero';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Shield, Lock, Eye, CheckCircle2 } from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* Marketing Navbar */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Shield className="size-4" />
            </div>
            <span className="text-xl font-bold tracking-tight">ABSs</span>
          </div>
          <nav className="hidden md:flex gap-6 text-sm font-medium text-muted-foreground">
            <Link href="#features" className="hover:text-foreground transition-colors">Features</Link>
            <Link href="#how-it-works" className="hover:text-foreground transition-colors">How it works</Link>
            <Link href="#pricing" className="hover:text-foreground transition-colors">Pricing</Link>
            <Link href="/docs" className="hover:text-foreground transition-colors">Documentation</Link>
          </nav>
          <div className="flex items-center gap-4">
            <Link href="/login" className="hidden sm:block text-sm font-medium hover:text-primary transition-colors">
              Sign In
            </Link>
            <Link href="/login">
              <Button className="rounded-full bg-primary text-primary-foreground hover:bg-primary/90">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <HeroSection />

      {/* Features Section */}
      <section id="features" className="py-24 bg-zinc-950">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Enterprise-Grade Agent Security
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Everything you need to deploy autonomous agents in production without risking your data or infrastructure.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                title: 'DOM Sanitizer Lens',
                description: 'Automatically strips malicious hidden prompts, invisible text, and weaponized CSS from the DOM before your agent sees it.',
                icon: Eye,
              },
              {
                title: 'Action Sentinel',
                description: 'Validates every agent action against your security policies. Blocks dangerous downloads, form submissions, and data exfiltration.',
                icon: Shield,
              },
              {
                title: 'Forensic Audit Logs',
                description: 'Records every action, DOM state, and network request. Features Explainable AI (XAI) to help you understand why an action was blocked.',
                icon: Lock,
              },
            ].map((feature, i) => (
              <div key={i} className="glass rounded-2xl p-8 hover:bg-zinc-900/80 transition-colors">
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      
      {/* Footer */}
      <footer className="border-t border-border/40 py-12 bg-background text-center text-muted-foreground">
        <div className="flex items-center justify-center gap-2 mb-4">
          <Shield className="size-5 text-primary" />
          <span className="text-xl font-bold tracking-tight text-foreground">ABSs</span>
        </div>
        <p className="text-sm">© {new Date().getFullYear()} ABSs Security. All rights reserved.</p>
      </footer>
    </main>
  );
}
