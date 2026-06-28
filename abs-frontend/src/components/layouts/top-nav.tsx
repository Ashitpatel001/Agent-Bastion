'use client';

import * as React from 'react';
import { usePathname } from 'next/navigation';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { Separator } from '@/components/ui/separator';
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb';
import { Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/store/app-store';

export function TopNav() {
  const pathname = usePathname();
  const toggleCommandPalette = useAppStore((state) => state.toggleCommandPalette);
  
  const paths = pathname?.split('/').filter(Boolean) || [];
  
  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-2 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 transition-all">
      <div className="flex items-center gap-2">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mr-2 h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            {paths.map((path, index) => {
              const isLast = index === paths.length - 1;
              const formattedPath = path.charAt(0).toUpperCase() + path.slice(1).replace(/-/g, ' ');
              
              return (
                <React.Fragment key={path}>
                  <BreadcrumbItem className="hidden md:block">
                    {isLast ? (
                      <BreadcrumbPage>{formattedPath}</BreadcrumbPage>
                    ) : (
                      <span className="text-muted-foreground">{formattedPath}</span>
                    )}
                  </BreadcrumbItem>
                  {!isLast && <BreadcrumbSeparator className="hidden md:block" />}
                </React.Fragment>
              );
            })}
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      
      <div className="ml-auto flex items-center gap-2">
        <Button 
          variant="outline" 
          className="w-full justify-start text-sm text-muted-foreground sm:pr-12 md:w-40 lg:w-64"
          onClick={toggleCommandPalette}
        >
          <span className="hidden lg:inline-flex">Search docs & incidents...</span>
          <span className="inline-flex lg:hidden">Search...</span>
          <kbd className="pointer-events-none absolute right-[0.3rem] top-[0.3rem] hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="size-4" />
          <span className="absolute top-1.5 right-1.5 size-2 rounded-full bg-destructive" />
        </Button>
      </div>
    </header>
  );
}
