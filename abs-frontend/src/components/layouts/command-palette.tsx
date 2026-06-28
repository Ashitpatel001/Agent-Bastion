'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { useAppStore } from '@/store/app-store';
import { NAVIGATION_ITEMS } from '@/lib/constants';
import { LayoutDashboard, FileCode2, ShieldAlert, Terminal, Settings, KeyRound } from 'lucide-react';

const ICON_MAP: Record<string, React.ElementType> = {
  LayoutDashboard,
  Terminal,
  ShieldAlert,
  FileCode2,
  KeyRound,
  Settings,
};

export function CommandPalette() {
  const router = useRouter();
  const { commandPaletteOpen, setCommandPaletteOpen } = useAppStore();

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setCommandPaletteOpen(!commandPaletteOpen);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  const runCommand = React.useCallback(
    (command: () => unknown) => {
      setCommandPaletteOpen(false);
      command();
    },
    [setCommandPaletteOpen]
  );

  return (
    <CommandDialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          {NAVIGATION_ITEMS.map((item) => {
            const Icon = ICON_MAP[item.icon] || LayoutDashboard;
            return (
              <CommandItem
                key={item.href}
                value={item.title}
                onSelect={() => runCommand(() => router.push(item.href))}
              >
                <Icon className="mr-2 h-4 w-4" />
                <span>{item.title}</span>
              </CommandItem>
            );
          })}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Actions">
          <CommandItem onSelect={() => runCommand(() => router.push('/dashboard/sandbox'))}>
            <Terminal className="mr-2 h-4 w-4" />
            <span>New Sandbox Session</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => router.push('/dashboard/policies'))}>
            <FileCode2 className="mr-2 h-4 w-4" />
            <span>Update Security Policy</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
