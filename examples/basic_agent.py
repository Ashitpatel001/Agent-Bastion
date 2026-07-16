"""
examples/basic_agent.py — Basic Agent Submission & Lifecycle Monitoring

Demonstrates how to initialize the Agent-Bastion Python Client, submit an autonomous
browser agent task, and inspect execution progression.

Usage:
    export AGENT_BASTION_API_KEY="your-api-key"
    python examples/basic_agent.py
"""

import time
import sys
from agent_bastion import Client, AgentBastionError


def main():
    print("\033[34m[Agent-Bastion SDK Example]\033[0m Initializing client...")
    
    # Client automatically reads AGENT_BASTION_API_KEY or defaults to localhost:8000
    with Client() as client:
        try:
            # 1. Check health
            health = client.check_health()
            print(f"✔ Cluster status: {health.get('status')} (v{health.get('version', '2.0.0')})")

            # 2. Submit task
            prompt = "Navigate to Hacker News, extract the top 3 story headlines, and return them as JSON."
            target_url = "https://news.ycombinator.com"
            print(f"\nSubmitting task: '{prompt}' on {target_url}...")

            session = client.create_agent_session(
                task_prompt=prompt,
                target_url=target_url,
                queue_name="agents",
                priority=5,
            )
            session_id = session.get("session_id")
            print(f"✔ Task Enqueued! Session ID: \033[36m{session_id}\033[0m (Queue: {session.get('queue_name')})")

            # 3. Poll for status (up to 10 iterations for demonstration)
            print("\nMonitoring progression...")
            for i in range(10):
                time.sleep(2.0)
                status = client.get_status(session_id)
                current_state = status.get("status")
                step_count = status.get("step_count", 0)
                url = status.get("current_url", "N/A")
                print(f"  [{i+1}/10] Status: {current_state} | Steps: {step_count} | Active URL: {url}")

                if current_state in ("COMPLETED", "FAILED", "CANCELLED"):
                    print(f"\n✔ Session Finished with status: \033[32m{current_state}\033[0m")
                    if status.get("result"):
                        print(f"Result:\n{status.get('result')}")
                    break

        except AgentBastionError as exc:
            print(f"\033[31mSDK Error ({exc.status_code}): {exc.message}\033[0m", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
