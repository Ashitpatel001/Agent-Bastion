import { RiskLevel } from '@/types';
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function formatDate(isoString: string): string {
  try {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(date);
  } catch (error) {
    return isoString;
  }
}

export function formatRelativeTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`;
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 30) return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    
    return formatDate(isoString);
  } catch (error) {
    return isoString;
  }
}

export function truncateUrl(url: string, maxLength: number): string {
  if (!url || url.length <= maxLength) return url;
  
  try {
    const parsedUrl = new URL(url);
    const domain = parsedUrl.hostname;
    
    if (domain.length + 8 > maxLength) { // +8 for https://
      return `${url.substring(0, maxLength - 3)}...`;
    }
    
    const remainingLength = maxLength - domain.length - 8 - 3; // -3 for ...
    const path = parsedUrl.pathname + parsedUrl.search;
    
    if (remainingLength <= 0) {
      return `${parsedUrl.protocol}//${domain}...`;
    }
    
    return `${parsedUrl.protocol}//${domain}${path.substring(0, remainingLength)}...`;
  } catch (e) {
    return `${url.substring(0, maxLength - 3)}...`;
  }
}

export function extractDomain(url: string): string {
  if (!url) return '';
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.hostname;
  } catch (e) {
    return url;
  }
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-US').format(n);
}

export function formatPercentage(value: number, total: number): string {
  if (total === 0) return '0%';
  return `${((value / total) * 100).toFixed(1)}%`;
}

export function getRiskLevelFromScore(score: number): RiskLevel {
  if (score <= 20) return RiskLevel.SAFE;
  if (score <= 40) return RiskLevel.LOW;
  if (score <= 60) return RiskLevel.MEDIUM;
  if (score <= 80) return RiskLevel.HIGH;
  return RiskLevel.CRITICAL;
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Deprecated: use cn instead
export function classNames(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}
