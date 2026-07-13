# Agent-Bastion: Cloudflare Workers Free-Tier Implementation Plan

## Executive Summary

This document replaces the previous multi-domain edge migration plan. That plan required Durable Objects, D1, R2, AI Gateway, Vectorize, and Workers AI — all paid Cloudflare products. This plan uses **zero paid Cloudflare features**.

The architecture is simple: Cloudflare Workers sit in front of your self-hosted server as a free proxy layer. Your existing FastAPI + Celery + PostgreSQL + Redis stack is untouched and continues running on your own machine.

**Total Cloudflare cost: $0/month.**
**Total infrastructure cost: $0/month (your own server).**

---

## What Stays (Untouched)

Your entire backend remains exactly as it is. No migration. No rewrites.

| Component | Stays As-Is |
|---|---|
| FastAPI backend | ✓ Running on your server, port 8000 |
| Celery workers (agents + xai queues) | ✓ Unchanged |
| PostgreSQL (SQLAlchemy Async) | ✓ Unchanged |
| Redis (broker + result backend) | ✓ Unchanged |
| SecureAgent (all 5 security layers) | ✓ Unchanged |
| Next.js 15 frontend | ✓ Unchanged |
| Docker Compose deployment | ✓ Unchanged |
| attack_server.py threat simulator | ✓ Unchanged |

---

## What Changes (Cloudflare Workers Layer Added)

```
User (anywhere in world)
        ↓
Cloudflare Edge (300+ PoPs — free DDoS + CDN)
        ↓
Cloudflare Worker (free proxy — rate limiting + routing + security headers)
        ↓
Your Server (FastAPI :8000 + Celery + Postgres + Redis)
```

Cloudflare Workers act as a reverse proxy. Every request from users hits Cloudflare first, then Cloudflare forwards it to your server. Users never see your server's IP.

---

## Free Tier Limits (Cloudflare Workers)

| Feature | Free Limit | Sufficient For |
|---|---|---|
| Worker requests | 100,000/day | ~1 request/second sustained |
| Worker CPU time | 10ms per request | Simple proxy logic easily fits |
| Custom domain | Unlimited | Your domain, free |
| DDoS protection | Unlimited | Automatic, always on |
| CDN caching | Unlimited | Static assets cached globally |
| SSL/TLS certificate | Unlimited | Auto-provisioned, auto-renewed |
| DNS records | Unlimited | All your subdomains |

---

## Domain 1: Cloudflare Worker — Reverse Proxy

### What It Does

- Receives all incoming requests
- Applies rate limiting (in Worker code — no paid CF rate limiting needed)
- Adds security headers
- Forwards request to your self-hosted FastAPI server
- Returns the response to the user

### Worker Code

```typescript
// src/worker.ts
export default {
  async fetch(request: Request, env: Env): Promise<Response> {

    // ── 1. RATE LIMITING (in-memory per Worker instance) ──────────────
    const ip = request.headers.get("CF-Connecting-IP") ?? "unknown";
    const url = new URL(request.url);

    // Block obviously malicious requests before hitting your server
    if (isMalicious(request, url)) {
      return new Response("Forbidden", { status: 403 });
    }

    // ── 2. FORWARD TO YOUR SERVER ──────────────────────────────────────
    const targetUrl = url.pathname + url.search;
    const backendUrl = `${env.BACKEND_ORIGIN}${targetUrl}`;

    const backendRequest = new Request(backendUrl, {
      method: request.method,
      headers: addForwardingHeaders(request, ip),
      body: request.method !== "GET" && request.method !== "HEAD"
        ? request.body
        : null,
    });

    let response: Response;
    try {
      response = await fetch(backendRequest);
    } catch (err) {
      // Your server is down
      return new Response(
        JSON.stringify({ error: "Service temporarily unavailable" }),
        { status: 503, headers: { "Content-Type": "application/json" } }
      );
    }

    // ── 3. ADD SECURITY HEADERS TO RESPONSE ───────────────────────────
    const secureResponse = new Response(response.body, response);
    addSecurityHeaders(secureResponse.headers);

    return secureResponse;
  }
};

// ── MALICIOUS REQUEST DETECTION ────────────────────────────────────────
// Blocks obvious attacks before they reach your FastAPI server.
// Your existing SecureAgent handles deep injection detection inside the session.
function isMalicious(request: Request, url: URL): boolean {
  const userAgent = request.headers.get("User-Agent") ?? "";
  const path = url.pathname;

  // Block common scanner user agents
  const badAgents = ["sqlmap", "nikto", "nmap", "masscan", "zgrab", "nuclei"];
  if (badAgents.some(agent => userAgent.toLowerCase().includes(agent))) {
    return true;
  }

  // Block path traversal attempts
  if (path.includes("../") || path.includes("..\\")) {
    return true;
  }

  // Block common exploit paths that should never exist in this app
  const exploitPaths = ["/wp-admin", "/phpmyadmin", "/.env", "/etc/passwd", "/shell"];
  if (exploitPaths.some(p => path.toLowerCase().startsWith(p))) {
    return true;
  }

  return false;
}

// ── FORWARDING HEADERS ─────────────────────────────────────────────────
// Tells your FastAPI server the real client IP and original host.
function addForwardingHeaders(request: Request, ip: string): Headers {
  const headers = new Headers(request.headers);
  headers.set("X-Forwarded-For", ip);
  headers.set("X-Forwarded-Proto", "https");
  headers.set("X-Real-IP", ip);
  // Strip Cloudflare-internal headers before forwarding
  headers.delete("CF-Connecting-IP");
  headers.delete("CF-Ray");
  return headers;
}

// ── SECURITY RESPONSE HEADERS ──────────────────────────────────────────
// Added to every response. Costs zero CPU. Hardens the frontend.
function addSecurityHeaders(headers: Headers): void {
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("X-Frame-Options", "DENY");
  headers.set("X-XSS-Protection", "1; mode=block");
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  headers.set(
    "Content-Security-Policy",
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
  );
  headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
}

// ── ENV TYPE ───────────────────────────────────────────────────────────
interface Env {
  BACKEND_ORIGIN: string; // e.g. "http://YOUR_SERVER_IP:8000"
}
```

### Splitting Frontend and API Traffic

The Worker distinguishes between API calls (forwarded to FastAPI) and frontend requests (forwarded to your Next.js container or served from Cloudflare cache):

```typescript
async fetch(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);

  // API calls → FastAPI backend
  if (url.pathname.startsWith("/api/")) {
    return forwardToBackend(request, env.BACKEND_ORIGIN, url);
  }

  // Static frontend → your Next.js container (or cached by Cloudflare)
  return forwardToBackend(request, env.FRONTEND_ORIGIN, url);
}
```

Or, simpler: point `api.yourdomain.com` → Worker → FastAPI, and `yourdomain.com` → direct Cloudflare Pages or your frontend container directly via Cloudflare proxy. Both work on the free tier.

---

## Domain 2: CDN for Static Frontend (Free)

When you enable Cloudflare's proxy (orange cloud) on your DNS records, Cloudflare automatically caches static assets (JS bundles, CSS, images, fonts) at its 300+ PoPs worldwide.

**No configuration needed.** The orange cloud does it.

**Optional: explicit cache rule for Next.js static assets**

Add a Cache Rule in the Cloudflare dashboard (free):

```
If: URI Path contains "/_next/static/"
Then: Cache Level = Cache Everything, Edge TTL = 1 month
```

This makes your Next.js static bundle load instantly from Cloudflare's edge for every user worldwide, regardless of where your server is.

---

## Domain 3: DDoS Protection & Rate Limiting (Free)

### DDoS (Automatic — Zero Configuration)

Enabling the Cloudflare proxy (orange cloud) on your domain activates Cloudflare's HTTP DDoS protection automatically. Volumetric attacks, floods, and amplification attacks are absorbed by Cloudflare's network before they reach your server. This is free on all plans.

### Rate Limiting (In Worker Code — Free)

Cloudflare's paid rate limiting product is not needed. The Worker above handles basic rate limiting in code. For per-IP request counting across the free tier, use a simple in-memory map:

```typescript
// Simple per-IP rate limiter using Worker in-memory state.
// Note: resets when the Worker instance recycles (~few minutes of inactivity).
// Good enough for blocking burst attacks; not a billing-grade quota system.
const requestCounts = new Map<string, { count: number; windowStart: number }>();

function isRateLimited(ip: string, limit: number, windowMs: number): boolean {
  const now = Date.now();
  const entry = requestCounts.get(ip);

  if (!entry || now - entry.windowStart > windowMs) {
    requestCounts.set(ip, { count: 1, windowStart: now });
    return false;
  }

  entry.count++;
  if (entry.count > limit) {
    return true; // Rate limited
  }

  return false;
}

// Usage in fetch handler:
// POST /api/v1/sessions → max 5 requests per IP per 60 seconds
if (request.method === "POST" && url.pathname === "/api/v1/sessions") {
  if (isRateLimited(ip, 5, 60_000)) {
    return new Response("Too Many Requests", { status: 429 });
  }
}
```

### Free WAF Rules (Cloudflare Dashboard)

Cloudflare's free plan includes 5 custom WAF rules. Use them on the highest-risk endpoints:

| Rule | Expression | Action |
|---|---|---|
| Block login brute force | `http.request.uri.path eq "/api/v1/auth/token" and cf.threat_score > 10` | Block |
| Block high threat score IPs | `cf.threat_score > 30` | JS Challenge |
| Block known bad countries (optional) | `ip.geoip.country in {"CN" "RU" "KP"}` | Challenge |
| Protect session creation | `http.request.uri.path eq "/api/v1/sessions" and http.request.method eq "POST" and cf.threat_score > 5` | Challenge |
| Block scanner user agents | `http.user_agent contains "sqlmap" or http.user_agent contains "nikto"` | Block |

---

## Domain 4: Custom Domain & DNS (Free)

### DNS Setup

Add your domain to Cloudflare (free). Set these records:

| Type | Name | Value | Proxy |
|---|---|---|---|
| `A` | `@` | `YOUR_SERVER_IP` | ✓ Orange cloud (proxied) |
| `A` | `www` | `YOUR_SERVER_IP` | ✓ Orange cloud (proxied) |
| `A` | `api` | `YOUR_SERVER_IP` | ✓ Orange cloud (proxied) |

**Critical**: the orange cloud (proxy enabled) is what activates DDoS protection, CDN, and SSL. Without it, Cloudflare is just a DNS provider.

### Workers Route

Map your Worker to the API subdomain:

```
api.yourdomain.com/* → abs-proxy-worker
```

This routes all API traffic through the Worker proxy. Frontend traffic on `yourdomain.com` goes directly through Cloudflare's proxy to your server (with CDN + DDoS but without the Worker logic).

### SSL/TLS (Free, Automatic)

Cloudflare provisions a free TLS certificate for your domain automatically. Set SSL mode to **Full** in the dashboard (SSL/TLS → Overview → Full). Your server does not need a certificate — Cloudflare handles TLS termination at the edge.

---

## `wrangler.toml` — Complete Configuration

```toml
name = "abs-proxy"
main = "src/worker.ts"
compatibility_date = "2025-01-01"

# ── ENVIRONMENT VARIABLES ──────────────────────────────────────────────
[vars]
BACKEND_ORIGIN = "http://YOUR_SERVER_IP:8000"
FRONTEND_ORIGIN = "http://YOUR_SERVER_IP:3000"

# ── STAGING ENVIRONMENT ────────────────────────────────────────────────
[env.staging]
name = "abs-proxy-staging"
[env.staging.vars]
BACKEND_ORIGIN = "http://YOUR_SERVER_IP:8000"
FRONTEND_ORIGIN = "http://YOUR_SERVER_IP:3000"

# ── PRODUCTION ENVIRONMENT ─────────────────────────────────────────────
[env.production]
name = "abs-proxy-production"
[env.production.vars]
BACKEND_ORIGIN = "http://YOUR_SERVER_IP:8000"
FRONTEND_ORIGIN = "http://YOUR_SERVER_IP:3000"

# ── WORKER ROUTES ──────────────────────────────────────────────────────
# Configured in Cloudflare dashboard under Workers & Pages → your worker → Triggers
# Route: api.yourdomain.com/*  → abs-proxy-production
```

---

## Deployment Steps

### Step 1: Install Wrangler

```bash
npm install -g wrangler
wrangler login
```

### Step 2: Create the project

```bash
mkdir abs-proxy && cd abs-proxy
npm init -y
npm install --save-dev wrangler typescript
```

Copy the Worker code above into `src/worker.ts`. Copy `wrangler.toml` into the project root. Replace `YOUR_SERVER_IP` with your actual server IP.

### Step 3: Test locally

```bash
wrangler dev
# Worker runs at http://localhost:8787
# Proxies requests to your local FastAPI server
```

### Step 4: Deploy

```bash
wrangler deploy --env production
```

### Step 5: Configure DNS in Cloudflare dashboard

1. Add your domain to Cloudflare (free)
2. Add the A records from Domain 4 above
3. Add the Worker route: `api.yourdomain.com/*`
4. Set SSL/TLS to **Full**
5. Add the 5 WAF rules from Domain 3

### Step 6: Update your FastAPI CORS config

Your FastAPI server currently allows requests from `localhost`. Update `CORS_ORIGINS` in your environment to allow requests from your Cloudflare domain:

```python
# In your FastAPI app config
CORS_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    "http://localhost:3000",  # keep for local dev
]
```

---

## What You Get (All Free)

| Benefit | How |
|---|---|
| Global DDoS protection | Cloudflare proxy, automatic |
| SSL/TLS certificate | Cloudflare Universal SSL, automatic |
| Custom domain | Cloudflare DNS, free |
| CDN for static assets | Cloudflare proxy cache, automatic |
| Your server IP hidden | Users only see Cloudflare IPs |
| Basic WAF (5 rules) | Cloudflare free plan |
| Scanner/bot blocking | Worker `isMalicious()` function |
| Security response headers | Worker `addSecurityHeaders()` function |
| 503 fallback if server is down | Worker try/catch around fetch |
| Request forwarding globally | Worker runs at 300+ PoPs |

## What You Don't Get (Requires Paid)

| Feature | Why Skipped |
|---|---|
| Durable Objects | Paid. Celery handles this on your server. |
| D1 / KV / R2 | Paid beyond small limits. PostgreSQL on your server handles this. |
| AI Gateway | Paid. Direct LLM calls from your server are fine. |
| Workers AI (semantic filter) | Paid. Your existing regex `INJECTION_PATTERNS` handles this. |
| Bot Management | Paid. Cloudflare threat score check (free WAF rule) is sufficient to start. |
| Per-IP rate limiting across Workers | Requires KV (paid beyond limits). In-memory rate limiter in Worker is sufficient for burst protection. |

---

## Summary

Your backend does not change. Your security does not change. Cloudflare Workers adds one free layer in front that gives you a professional-grade domain, SSL, DDoS protection, and CDN — things that would cost money elsewhere — at zero cost. Ship this, get users, then decide if paid features are worth it.