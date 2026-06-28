import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AbsApiClient } from '@/services/api';
import { useAppStore } from '@/store/app-store';
import { AgentSessionCreateRequest, PolicyUpdateRequest, TenantCreateRequest } from '@/types';

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
