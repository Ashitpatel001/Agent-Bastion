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
    refetchInterval: 1000,
  });
}

export function useSecurityStats() {
  const apiKey = useAppStore((state) => state.apiKey);
  
  return useQuery({
    queryKey: ['securityStats'],
    queryFn: () => AbsApiClient.create(apiKey!).getSecurityStats(),
    enabled: !!apiKey,
    refetchInterval: 1000,
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
  return useMutation({
    mutationFn: (data: AgentSessionCreateRequest) => {
      const apiKey = useAppStore.getState().apiKey;
      return AbsApiClient.create(apiKey || undefined).submitAgentTask(data);
    },
  });
}

export function useCancelAgentTask() {
  return useMutation({
    mutationFn: (jobId: string) => {
      const apiKey = useAppStore.getState().apiKey;
      return AbsApiClient.create(apiKey || undefined).cancelAgentTask(jobId);
    },
  });
}

export function useRetryAgentTask() {
  return useMutation({
    mutationFn: (jobId: string) => {
      const apiKey = useAppStore.getState().apiKey;
      return AbsApiClient.create(apiKey || undefined).retryAgentTask(jobId);
    },
  });
}

export function useDxQuickstart() {
  const apiKey = useAppStore((state) => state.apiKey);
  return useQuery({
    queryKey: ['dxQuickstart', apiKey],
    queryFn: () => {
      const currentKey = useAppStore.getState().apiKey;
      return AbsApiClient.create(currentKey || undefined).getDxQuickstart();
    },
    enabled: !!apiKey,
    refetchInterval: 10000,
  });
}

export function useDxOverview() {
  const apiKey = useAppStore((state) => state.apiKey);
  return useQuery({
    queryKey: ['dxOverview', apiKey],
    queryFn: () => {
      const currentKey = useAppStore.getState().apiKey;
      return AbsApiClient.create(currentKey || undefined).getDxOverview();
    },
    enabled: !!apiKey,
    refetchInterval: 5000,
  });
}

export function useAgentStatus(jobId: string | null) {
  const apiKey = useAppStore((state) => state.apiKey);

  return useQuery({
    queryKey: ['agentStatus', jobId],
    queryFn: () => {
      const currentKey = useAppStore.getState().apiKey;
      return AbsApiClient.create(currentKey || undefined).getAgentStatus(jobId!);
    },
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
    refetchInterval: 1000,
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
    refetchInterval: 1000,
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

export function useTenantSettings() {
  const apiKey = useAppStore((state) => state.apiKey);
  
  return useQuery({
    queryKey: ['tenantSettings'],
    queryFn: () => AbsApiClient.create(apiKey!).getSettings(),
    enabled: !!apiKey,
  });
}

export function useLlmStatus() {
  const apiKey = useAppStore((state) => state.apiKey);
  
  return useQuery({
    queryKey: ['llmStatus'],
    queryFn: () => AbsApiClient.create(apiKey!).getLlmStatus(),
    enabled: !!apiKey,
    refetchInterval: 5000,
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
    queryFn: () => AbsApiClient.create(apiKey!).getAnalyticsTimeSeries(days),
    enabled: !!apiKey,
    refetchInterval: 1000,
  });
}

export function useXaiLogs(page: number = 1, pageSize: number = 20, pendingOnly: boolean = false) {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['xaiLogs', page, pageSize, pendingOnly],
    queryFn: () => AbsApiClient.create(apiKey!).getXaiLogs(page, pageSize, pendingOnly),
    enabled: !!apiKey,
    refetchInterval: 1000,
  });
}

export function useReputationCheck() {
  const { apiKey } = useAppStore();
  return useMutation({
    mutationFn: (url: string) => AbsApiClient.create(apiKey || undefined).checkReputation(url),
  });
}

export function useSystemHealth() {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['systemHealth'],
    queryFn: () => AbsApiClient.create(apiKey!).getSystemHealth(),
    enabled: !!apiKey,
    refetchInterval: 1000,
  });
}

export function useSecurityEvents(page: number = 1, pageSize: number = 50) {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['securityEvents', page, pageSize],
    queryFn: () => AbsApiClient.create(apiKey!).getSecurityEvents(page, pageSize),
    enabled: !!apiKey,
    refetchInterval: 1000,
  });
}

export function useSimulateTraffic() {
  const { apiKey } = useAppStore();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => AbsApiClient.create(apiKey!).simulateTraffic(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['securityStats'] });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['securityLogs'] });
      queryClient.invalidateQueries({ queryKey: ['analyticsTimeSeries'] });
    }
  });
}

export function useObservabilityTasks() {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['observabilityTasks'],
    queryFn: () => AbsApiClient.create(apiKey!).getTaskObservability(),
    enabled: !!apiKey,
    refetchInterval: 3000,
  });
}

export function useObservabilityWorkers() {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['observabilityWorkers'],
    queryFn: () => AbsApiClient.create(apiKey!).getWorkerObservability(),
    enabled: !!apiKey,
    refetchInterval: 3000,
  });
}

export function useObservabilitySecurity(days: number = 7) {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['observabilitySecurity', days],
    queryFn: () => AbsApiClient.create(apiKey!).getSecurityObservability(days),
    enabled: !!apiKey,
    refetchInterval: 5000,
  });
}

export function useObservabilityTenants() {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['observabilityTenants'],
    queryFn: () => AbsApiClient.create(apiKey!).getTenantObservability(),
    enabled: !!apiKey,
    refetchInterval: 5000,
  });
}

export function useObservabilityAuditTrail(page: number = 1, pageSize: number = 50) {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['observabilityAuditTrail', page, pageSize],
    queryFn: () => AbsApiClient.create(apiKey!).getAuditTrail(page, pageSize),
    enabled: !!apiKey,
    refetchInterval: 5000,
  });
}

export const useAuditTrail = useObservabilityAuditTrail;


export function useObservabilityMetrics() {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['observabilityMetrics'],
    queryFn: () => AbsApiClient.create(apiKey!).getObservabilityMetrics(),
    enabled: !!apiKey,
    refetchInterval: 3000,
  });
}

export function useObservabilityHealth() {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['observabilityHealth'],
    queryFn: () => AbsApiClient.create(apiKey!).getObservabilityHealth(),
    enabled: !!apiKey,
    refetchInterval: 3000,
  });
}

export function useInfrastructureStatus() {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['infrastructureStatus'],
    queryFn: () => AbsApiClient.create(apiKey!).getInfrastructureStatus(),
    enabled: !!apiKey,
    refetchInterval: 3000,
  });
}

export function useApiKeys(skip: number = 0, limit: number = 100) {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['apiKeys', skip, limit],
    queryFn: () => AbsApiClient.create(apiKey!).getApiKeys(skip, limit),
    enabled: !!apiKey,
    refetchInterval: 5000,
  });
}

export function useCreateApiKey() {
  const queryClient = useQueryClient();
  const { apiKey } = useAppStore();
  return useMutation({
    mutationFn: (data: { name: string; scopes?: string[] }) => AbsApiClient.create(apiKey!).createApiKey(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
      queryClient.invalidateQueries({ queryKey: ['dxQuickstart'] });
    },
  });
}

export function useRotateApiKey() {
  const queryClient = useQueryClient();
  const { apiKey } = useAppStore();
  return useMutation({
    mutationFn: (keyId: string) => AbsApiClient.create(apiKey!).rotateApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
    },
  });
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient();
  const { apiKey } = useAppStore();
  return useMutation({
    mutationFn: (keyId: string) => AbsApiClient.create(apiKey!).revokeApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] });
      queryClient.invalidateQueries({ queryKey: ['dxQuickstart'] });
    },
  });
}

export function useOrganizations(skip: number = 0, limit: number = 100) {
  const { apiKey } = useAppStore();
  return useQuery({
    queryKey: ['organizations', skip, limit],
    queryFn: () => AbsApiClient.create(apiKey!).getOrganizations(skip, limit),
    enabled: !!apiKey,
    refetchInterval: 5000,
  });
}

export function useCreateOrganization() {
  const queryClient = useQueryClient();
  const { apiKey } = useAppStore();
  return useMutation({
    mutationFn: (data: { name: string; slug?: string; description?: string; email?: string }) => AbsApiClient.create(apiKey!).createOrganization(data),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
    },
  });
}

export function useChangePassword() {
  const { apiKey } = useAppStore();
  return useMutation({
    mutationFn: (data: { current_password?: string; old_password?: string; new_password: string }) => AbsApiClient.create(apiKey!).changePassword(data),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (email: string) => AbsApiClient.create().resetPassword(email),
  });
}

export function useLogout() {
  const { apiKey } = useAppStore();
  return useMutation({
    mutationFn: () => AbsApiClient.create(apiKey!).logout(),
  });
}


