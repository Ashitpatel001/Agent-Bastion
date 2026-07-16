'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar';
import { NAVIGATION_ITEMS, APP_NAME } from '@/lib/constants';
import { useAppStore } from '@/store/app-store';
import { ShieldCheck, ShieldAlert, LayoutDashboard, Terminal, FileCode2, KeyRound, Settings, LogOut, Activity, BrainCircuit, Code, Cpu, Layers, Server } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';

const ICON_MAP: Record<string, React.ElementType> = {
  LayoutDashboard,
  Terminal,
  ShieldAlert,
  FileCode2,
  KeyRound,
  Settings,
  Activity,
  BrainCircuit,
  ShieldCheck,
  Code,
  Cpu,
  Layers,
  Server,
};

export function SidebarNav() {
  const pathname = usePathname();
  const { tenantName, tenantTier, clearCredentials } = useAppStore();

  const handleLogout = () => {
    clearCredentials();
    window.location.href = '/login';
  };

  return (
    <Sidebar variant="sidebar" collapsible="icon">
      <SidebarHeader className="h-16 flex items-center border-b px-4 border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" className="w-full justify-start cursor-default">
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <ShieldCheck className="size-5" />
              </div>
              <div className="flex flex-col gap-0.5 leading-none">
                <span className="font-semibold text-base">{APP_NAME}</span>
                <span className="text-xs text-muted-foreground truncate">
                  Enterprise Proxy
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarMenu className="px-2 mt-4 gap-1">
          {NAVIGATION_ITEMS.map((item) => {
            const Icon = ICON_MAP[item.icon] || LayoutDashboard;
            const itemHref = item.href || item.url || '#';
            const isActive = pathname?.startsWith(itemHref) || false;
            
            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton 
                  isActive={isActive} 
                  tooltip={item.title}
                  render={
                    <Link href={itemHref} className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-3">
                        <Icon className="size-4" />
                        <span>{item.title}</span>
                      </div>
                      {item.badge && (
                        <Badge variant="destructive" className="ml-auto flex h-5 w-5 items-center justify-center rounded-full p-0 text-[10px]">
                          {item.badge}
                        </Badge>
                      )}
                    </Link>
                  }
                />
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarContent>

      <SidebarFooter className="p-4 border-t border-sidebar-border">
        <div className="flex items-center gap-3">
          <Avatar className="size-8 border">
            <AvatarFallback className="bg-primary/10 text-primary text-xs">
              {tenantName?.substring(0, 2).toUpperCase() || 'TE'}
            </AvatarFallback>
          </Avatar>
          <div className="flex flex-col flex-1 overflow-hidden">
            <span className="text-sm font-medium truncate">{tenantName || 'Tenant'}</span>
            <span className="text-xs text-muted-foreground truncate">{tenantTier || 'FREE'} Tier</span>
          </div>
          <button 
            onClick={handleLogout}
            className="p-2 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground transition-colors"
            title="Log out"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
