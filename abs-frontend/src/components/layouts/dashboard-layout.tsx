'use client';

import * as React from 'react';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { SidebarNav } from './sidebar-nav';
import { TopNav } from './top-nav';
import { CommandPalette } from './command-palette';
import { usePathname, useRouter } from 'next/navigation';
import { useAppStore } from '@/store/app-store';

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isAuthenticated = useAppStore((state) => state.isAuthenticated());
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  // Protect dashboard routes
  const isDocs = pathname?.startsWith('/dashboard/docs');
  
  React.useEffect(() => {
    if (mounted && !isAuthenticated && pathname?.startsWith('/dashboard') && !isDocs) {
      router.push('/login?tab=register');
    }
  }, [mounted, isAuthenticated, pathname, router, isDocs]);

  // Don't render until mounted to prevent hydration errors from zustand persist
  if (!mounted) {
    return null;
  }

  // If not authenticated and trying to access dashboard (except docs), don't render children
  if (!isAuthenticated && pathname?.startsWith('/dashboard') && !isDocs) {
    return null;
  }

  return (
    <SidebarProvider>
      <SidebarNav />
      <SidebarInset>
        <TopNav />
        <main className="flex-1 p-4 md:p-6 lg:p-8 overflow-x-hidden">
          {children}
        </main>
      </SidebarInset>
      <CommandPalette />
    </SidebarProvider>
  );
}
