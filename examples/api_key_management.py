"""
examples/api_key_management.py — Cryptographic API Key Lifecycle & Rotation Management

Demonstrates generating secondary API keys (`client.generate_api_key`), auditing active
keys across a tenant organization, and enforcing principle of least privilege.
"""

import sys
import json
from agent_bastion import Client, AgentBastionError


def main():
    print("\033[34m[Agent-Bastion API Key Manager]\033[0m Managing cryptographic credentials...")

    with Client() as client:
        try:
            # 1. Generate specialized key for production automation workers
            print("\nGenerating specialized worker API key with dedicated rate limits...")
            key_res = client.generate_api_key(
                name="prod-browser-automation-worker-01",
            )
            print("\n\033[32m✔ New API Key Provisioned:\033[0m")
            print(json.dumps(key_res, indent=2, default=str))

            key_id = key_res.get("id")
            plaintext_key = key_res.get("api_key")

            print(f"\nKey ID: {key_id}")
            if plaintext_key:
                print(f"Plaintext Key (Store Securely!): \033[33m{plaintext_key}\033[0m")

            # 2. Test authenticating with the new key
            if plaintext_key:
                print("\nValidating cryptographic key challenge...")
                with Client(api_key=plaintext_key) as worker_client:
                    metrics = worker_client.metrics()
                    print("✔ Authentication successful using newly provisioned key!")

        except AgentBastionError as exc:
            print(f"\033[31mKey management error: {exc.message}\033[0m", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
