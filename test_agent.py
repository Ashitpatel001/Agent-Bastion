import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from db.database import init_db, get_db_context
from db import crud
from workers.agent_tasks import run_agent_task
import sqlalchemy as sa
from db.models import Tenant

async def main():
    await init_db()
    async with get_db_context() as db:
        tenant = (await db.execute(sa.select(Tenant).limit(1))).scalar()
        tenant_id = tenant.id
        session = await crud.create_session(
            db, 
            tenant_id=tenant_id, 
            task_prompt="Navigate to Amazon India",
            target_url="https://www.amazon.in"
        )
        print(f"Created session: {session.id}")
        session_id = session.id
        
    print("Running task...")
    try:
        from workers.dispatch import dispatch_task
        t = dispatch_task(run_agent_task, session_id, tenant_id)
        if hasattr(t, "join"):
            t.join() # Wait for the background thread to finish if running locally
        print("Task completed!")
    except Exception as e:
        print(f"Task failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
