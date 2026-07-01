import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AbsApiClient, apiClient } from '@/services/api';
import { useAppStore } from '@/store/app-store';
import { AgentSessionCreateRequest, PolicyUpdateRequest, TenantCreateRequest, LoginRequest, RegisterRequest, TenantSettings } from '@/types';


export function useSecurityLogs(page: number = 1, pageSize: number = 50) {
  const apiKey = useAppStore((state) => state.apiKey);
  
  return useQuery({
    queryKey: ['securityLogs', page, pageSize],
    queryFn: () => AbsApiClient.create(apiKey!).getSecurityLogs(page, pageSize),
    enabled: !!apiKey,
    refetchInterval: 10000,
  });
}

export function useSecurityStats() {
  const apiKey = useAppStore((state) => state.apiKey);
  
  return useQuery({
    queryKey: ['securityStats'],
    queryFn: () => AbsApiClient.create(apiKey!).getSecurityStats(),
    enabled: !!apiKey,
    refetchInterval: 15000,
  });
}

export function useActivePolicy() {
  const apiKey = useAppStore((state) => state.apiKey);
  
  return useQuery({
    queryKey: ['activePolicy'],
    queryFn: () => AbsApiClient.create(apiKey!).getActivePolicy(),
    enabled: !!apiKey,
  });
}

export function useUpdatePolicy() {
  const queryClient = useQueryClient();
  const apiKey = useAppStore((state) => state.apiKey);

  return useMutation({
    mutationFn: (data: PolicyUpdateRequest) => AbsApiClient.create(apiKey!).updatePolicy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activePolicy'] });
    },
  });
}

export function useSubmitAgentTask() {
  const apiKey = useAppStore((state) => state.apiKey);

  return useMutation({
    mutationFn: (data: AgentSessionCreateRequest) => AbsApiClient.create(apiKey!).submitAgentTask(data),
  });
}

export function useCancelAgentTask() {
  const apiKey = useAppStore((state) => state.apiKey);

  return useMutation({
    mutationFn: (jobId: string) => AbsApiClient.create(apiKey!).cancelAgentTask(jobId),
  });
}

export function useAgentStatus(jobId: string | null) {
  const apiKey = useAppStore((state) => state.apiKey);

  return useQuery({
    queryKey: ['agentStatus', jobId],
    queryFn: () => AbsApiClient.create(apiKey!).getAgentStatus(jobId!),
    enabled: !!apiKey && !!jobId,
    refetchInterval: (query) => {
        const data = query.state.data;
        if (data && (data.status === 'COMPLETED' || data.status === 'FAILED' || data.status === 'CANCELLED')) {
            return false;
        }
        return 3000;
    },
  });
}

export function useRegisterTenant() {
  return useMutation({
    mutationFn: (data: TenantCreateRequest) => AbsApiClient.create().registerTenant(data),
  });
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ['healthCheck'],
    queryFn: () => AbsApiClient.create().healthCheck(),
    refetchInterval: 30000,
  });
}

export function useLogin() {
  return useMutation({
    mutationFn: (data: LoginRequest) => AbsApiClient.create().login(data),
  });
}

export function useRegisterV1() {
  return useMutation({
    mutationFn: (data: RegisterRequest) => AbsApiClient.create().registerV1(data),
  });
}

export function useIncidents(page: number = 1, pageSize: number = 50) {
  const apiKey = useAppStore((state) => state.apiKey);
  return useQuery({
    queryKey: ['incidents', page, pageSize],
    queryFn: () => AbsApiClient.create(apiKey!).getIncidents(page, pageSize),
    enabled: !!apiKey,
    refetchInterval: 15000,
  });
}

export function useSettings() {
  const apiKey = useAppStore((state) => state.apiKey);
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => AbsApiClient.create(apiKey!).getSettings(),
    enabled: !!apiKey,
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  const apiKey = useAppStore((state) => state.apiKey);
  return useMutation({
    mutationFn: (data: Partial<TenantSettings>) => AbsApiClient.create(apiKey!).updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });
}

export function useAnalyticsTimeSeries(days: number = 30) {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['analyticsTimeSeries', days],
    queryFn: () => apiClient.getAnalyticsTimeSeries(days),
    enabled: !!apiKey,
    refetchInterval: 30000,
  });
}

export function useXaiLogs(page: number = 1, pageSize: number = 20, pendingOnly: boolean = false) {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['xaiLogs', page, pageSize, pendingOnly],
    queryFn: () => apiClient.getXaiLogs(page, pageSize, pendingOnly),
    enabled: !!apiKey,
    refetchInterval: 10000,
  });
}

export function useReputationCheck() {
  return useMutation({
    mutationFn: (url: string) => apiClient.checkReputation(url),
  });
}

export function useSystemHealth() {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['systemHealth'],
    queryFn: () => apiClient.getSystemHealth(),
    enabled: !!apiKey,
    refetchInterval: 30000,
  });
}

export function useSecurityEvents(page: number = 1, pageSize: number = 50) {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['securityEvents', page, pageSize],
    queryFn: () => apiClient.getSecurityEvents(page, pageSize),
    enabled: !!apiKey,
    refetchInterval: 5000,
  });
}


