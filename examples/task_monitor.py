"""
examples/task_monitor.py — Continuous Task Lifecycle, Cancellation & Retry Workflow

Demonstrates how to monitor long-running tasks, gracefully revoke/cancel execution
upon user intervention or timeouts, and retry failed tasks using `client.retry()`.
"""

import time
import sys
from agent_bastion import Client, AgentBastionError, RateLimitError


def main():
    print("\033[34m[Agent-Bastion Task Monitor]\033[0m Starting resilient execution monitoring...")

    with Client() as client:
        try:
            # 1. Enqueue complex browser task
            session = client.create_agent_session(
                task_prompt="Audit web application navigation and test all interactive links.",
                target_url="https://example.com",
                priority=3,  # High priority routing
                max_retries=5,
            )
            session_id = session["session_id"]
            print(f"✔ Enqueued session \033[36m{session_id}\033[0m with high priority.")

            # 2. Simulate cancellation scenario if task takes over 15 seconds
            start_time = time.time()
            cancelled = False

            while True:
                time.sleep(3.0)
                status = client.get_status(session_id)
                state = status.get("status")
                elapsed = round(time.time() - start_time, 1)

                print(f"  [{elapsed}s] State: {state} | Step: {status.get('step_count', 0)}")

                if state in ("COMPLETED", "FAILED", "CANCELLED"):
                    print(f"\n✔ Terminal state reached: {state}")
                    break

                # If running longer than 15s, demonstrate clean cancellation
                if elapsed > 15.0 and not cancelled:
                    print("\n\033[33m! Execution exceeding SLA threshold. Sending cancellation request...\033[0m")
                    client.cancel(session_id)
                    cancelled = True

            # 3. If the task failed, demonstrate automated retry execution
            if state == "FAILED":
                print("\nInitiating automated task retry workflow...")
                retry_res = client.retry(session_id)
                print(f"✔ Task re-enqueued: {retry_res.get('status')}")

        except RateLimitError as exc:
            print(f"\033[33m! Rate limit triggered. Please retry after {exc.retry_after}s\033[0m")
        except AgentBastionError as exc:
            print(f"\033[31mError: {exc.message}\033[0m", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
