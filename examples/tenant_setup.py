"""
examples/tenant_setup.py — Multi-Tenant Organization Registration & Quota Configuration

Demonstrates onboarding a new tenant organization (`client.create_tenant`), inspecting assigned
rate-limiting tiers (`FREE`, `PRO`, `ENTERPRISE`), and verifying multi-tenant isolation boundaries.
"""

import sys
import json
from agent_bastion import Client, AgentBastionError, TenantIsolationError


def main():
    print("\033[34m[Agent-Bastion Tenant Onboarding]\033[0m Provisioning enterprise tenant account...")

    with Client() as client:
        try:
            # 1. Register new organization
            tenant_info = client.create_tenant(
                name="Acme Corporation AI Labs",
                tier="ENTERPRISE",
                contact_email="security@acme-corp.internal",
            )
            print("\n\033[32m✔ Tenant Organization Created Successfully:\033[0m")
            print(json.dumps(tenant_info, indent=2, default=str))

            tenant_id = tenant_info.get("id")
            initial_key = tenant_info.get("api_key")

            print(f"\nProvisioned Tenant ID: \033[36m{tenant_id}\033[0m")
            if initial_key:
                print(f"Admin API Key: \033[33m{initial_key}\033[0m")

            # 2. Verify tenant-isolated client instance
            if initial_key:
                print("\nVerifying isolated client connection using newly generated tenant credentials...")
                with Client(api_key=initial_key) as tenant_client:
                    health = tenant_client.check_health()
                    print(f"✔ Isolated tenant connection verified: {health.get('status')}")

        except TenantIsolationError:
            print("\033[31mTenant isolation boundary violation detected.\033[0m", file=sys.stderr)
        except AgentBastionError as exc:
            print(f"\033[31mOnboarding failed: {exc.message}\033[0m", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
