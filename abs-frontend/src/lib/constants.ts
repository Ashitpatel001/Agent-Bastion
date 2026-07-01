import { RiskLevel, ActionTaken, SessionStatus, UserRole, NavigationItem } from '@/types';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const APP_NAME = 'ABSs';
export const APP_DESCRIPTION = 'Zero-Trust Security Proxy for Autonomous AI Agents';

export const RISK_LEVEL_COLORS: Record<RiskLevel, string> = {
  [RiskLevel.SAFE]: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20',
  [RiskLevel.LOW]: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  [RiskLevel.MEDIUM]: 'text-amber-500 bg-amber-500/10 border-amber-500/20',
  [RiskLevel.HIGH]: 'text-orange-500 bg-orange-500/10 border-orange-500/20',
  [RiskLevel.CRITICAL]: 'text-red-500 bg-red-500/10 border-red-500/20',
};

export const ACTION_TAKEN_COLORS: Record<ActionTaken, string> = {
  [ActionTaken.ALLOWED]: 'text-emerald-500',
  [ActionTaken.MONITOR]: 'text-blue-500',
  [ActionTaken.WARNED]: 'text-amber-500',
  [ActionTaken.SANITIZED]: 'text-purple-500',
  [ActionTaken.BLOCKED]: 'text-red-500',
  [ActionTaken.BLOCK_AND_ESCALATE]: 'text-red-600 font-bold',
  [ActionTaken.EXPLAINED]: 'text-blue-400',
};

export const SESSION_STATUS_COLORS: Record<SessionStatus, string> = {
  [SessionStatus.QUEUED]: 'text-zinc-400',
  [SessionStatus.RUNNING]: 'text-blue-400',
  [SessionStatus.COMPLETED]: 'text-emerald-500',
  [SessionStatus.FAILED]: 'text-red-500',
  [SessionStatus.CANCELLED]: 'text-amber-500',
};

export const MITRE_ATTACK_MAP: Record<string, { id: string; name: string; url: string }> = {
  'prompt_injection': { id: 'T1566', name: 'Phishing', url: 'https://attack.mitre.org/techniques/T1566/' },
  'data_exfiltration': { id: 'T1048', name: 'Exfiltration Over Alternative Protocol', url: 'https://attack.mitre.org/techniques/T1048/' },
  'credential_access': { id: 'T1003', name: 'OS Credential Dumping', url: 'https://attack.mitre.org/techniques/T1003/' },
  'malicious_link': { id: 'T1190', name: 'Exploit Public-Facing Application', url: 'https://attack.mitre.org/techniques/T1190/' },
};

export const PRICING_TIERS = [
  {
    name: 'Developer',
    price: 'Free',
    features: ['Up to 1,000 API requests/mo', 'Basic threat detection', 'Community support', '1 concurrent session'],
    highlighted: false,
    cta: 'Get Started',
  },
  {
    name: 'Secure Scale',
    price: '$199/mo',
    features: ['Up to 100,000 API requests/mo', 'Advanced XAI insights', 'Priority email support', '10 concurrent sessions', 'Custom policies'],
    highlighted: true,
    cta: 'Start Free Trial',
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    features: ['Unlimited API requests', 'Dedicated SOC team', '24/7 phone support', 'Unlimited sessions', 'On-premise deployment'],
    highlighted: false,
    cta: 'Contact Sales',
  },
];

export const FAQ_ITEMS = [
  {
    question: 'How does ABSs affect my agent\'s latency?',
    answer: 'ABSs is designed for extreme performance. Our proxy engine processes requests in under 10ms on average, ensuring your autonomous agents remain highly responsive.',
  },
  {
    question: 'Can I self-host ABSs?',
    answer: 'Yes, the Enterprise tier includes options for on-premise deployment using Docker and Kubernetes, keeping your data entirely within your infrastructure.',
  },
  {
    question: 'Is ABSs compatible with LangChain or CrewAI?',
    answer: 'Absolutely. ABSs acts as an invisible proxy layer, meaning it is universally compatible with any framework or agent that makes HTTP requests or uses standard browser automation tools.',
  },
];

export const NAVIGATION_ITEMS: NavigationItem[] = [
  {
    title: 'Overview',
    href: '/dashboard/overview',
    icon: 'LayoutDashboard',
    roles: [UserRole.OWNER, UserRole.ADMIN, UserRole.SECURITY_ANALYST, UserRole.DEVELOPER, UserRole.VIEWER],
  },
  {
    title: 'Sandbox',
    href: '/dashboard/sandbox',
    icon: 'Terminal',
    roles: [UserRole.OWNER, UserRole.ADMIN, UserRole.DEVELOPER],
  },
  {
    title: 'Incidents',
    href: '/dashboard/incidents',
    icon: 'ShieldAlert',
    badge: '3',
    roles: [UserRole.OWNER, UserRole.ADMIN, UserRole.SECURITY_ANALYST],
  },
  {
    title: 'Live Feed',
    url: '/dashboard/live-feed',
    href: '/dashboard/live-feed',
    icon: 'Activity',
    roles: [UserRole.OWNER, UserRole.ADMIN, UserRole.SECURITY_ANALYST, UserRole.DEVELOPER, UserRole.VIEWER],
  },
  {
    title: 'XAI Explanations',
    url: '/dashboard/xai',
    href: '/dashboard/xai',
    icon: 'BrainCircuit',
    roles: [UserRole.OWNER, UserRole.ADMIN, UserRole.SECURITY_ANALYST, UserRole.DEVELOPER, UserRole.VIEWER],
  },
  {
    title: 'Proxy Firewall',
    url: '/dashboard/firewall',
    href: '/dashboard/firewall',
    icon: 'ShieldCheck',
    roles: [UserRole.OWNER, UserRole.ADMIN, UserRole.SECURITY_ANALYST, UserRole.DEVELOPER, UserRole.VIEWER],
  },
  {
    title: 'Policies',
    href: '/dashboard/policies',
    icon: 'FileCode2',
    roles: [UserRole.OWNER, UserRole.ADMIN],
  },
  {
    title: 'API Keys',
    href: '/dashboard/keys',
    icon: 'KeyRound',
    roles: [UserRole.OWNER, UserRole.ADMIN],
  },
  {
    title: 'Settings',
    href: '/dashboard/settings',
    icon: 'Settings',
    roles: [UserRole.OWNER, UserRole.ADMIN, UserRole.SECURITY_ANALYST, UserRole.DEVELOPER, UserRole.VIEWER],
  },
];
