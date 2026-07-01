import type { Metadata } from 'next';
import './globals.css';
import { AppProviders } from '@/providers/app-providers';
import { Toaster } from '@/components/ui/sonner';

export const metadata: Metadata = {
  title: 'ABSs | Zero-Trust Security Proxy for AI Agents',
  description: 'Enterprise-grade agentic browser security suite. Protect your autonomous AI agents from prompt injections and data exfiltration.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className="dark">
      <body className="font-sans min-h-screen bg-background text-foreground antialiased selection:bg-primary/30 selection:text-primary-foreground">
        <AppProviders>
          {children}
          <Toaster richColors theme="dark" position="top-right" />
        </AppProviders>
      </body>
    </html>
  );
}
