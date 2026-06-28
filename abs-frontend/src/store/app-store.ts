import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { TenantTier } from '@/types';

interface AppState {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  tenantId: string | null;
  apiKey: string | null;
  tenantName: string | null;
  tenantEmail: string | null;
  tenantTier: TenantTier | null;
  setCredentials: (tenantId: string, apiKey: string, tenantName: string, tenantEmail: string, tenantTier: TenantTier) => void;
  clearCredentials: () => void;
  isAuthenticated: () => boolean;
  activeJobId: string | null;
  setActiveJobId: (jobId: string | null) => void;
  clearActiveJobId: () => void;
  commandPaletteOpen: boolean;
  toggleCommandPalette: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      sidebarOpen: true,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      tenantId: null,
      apiKey: null,
      tenantName: null,
      tenantEmail: null,
      tenantTier: null,
      setCredentials: (tenantId, apiKey, tenantName, tenantEmail, tenantTier) => 
        set({ tenantId, apiKey, tenantName, tenantEmail, tenantTier }),
      clearCredentials: () => 
        set({ tenantId: null, apiKey: null, tenantName: null, tenantEmail: null, tenantTier: null, activeJobId: null }),
      isAuthenticated: () => get().apiKey !== null,
      activeJobId: null,
      setActiveJobId: (jobId) => set({ activeJobId: jobId }),
      clearActiveJobId: () => set({ activeJobId: null }),
      commandPaletteOpen: false,
      toggleCommandPalette: () => set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
    }),
    {
      name: 'abs-app-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        tenantId: state.tenantId, 
        apiKey: state.apiKey,
        tenantName: state.tenantName,
        tenantEmail: state.tenantEmail,
        tenantTier: state.tenantTier
      }),
    }
  )
);
