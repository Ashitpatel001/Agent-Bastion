#!/usr/bin/env python3
"""
start_saas.py — Enterprise SaaS Unified Launcher
Launches the FastAPI Zero-Trust Backend Gateway (Port 8000) and the Next.js SaaS Frontend (Port 3000) concurrently.
Ensures database seeding, real-time XAI explainability, DLP proxy rules, and SOC engineer profiles are initialized.
"""

import os
import sys
import subprocess
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

def stream_logs(process, prefix, color_code="\033[36m"):
    reset_code = "\033[0m" if os.name != 'nt' else ""
    for line in iter(process.stdout.readline, ''):
        print(f"{color_code}{prefix}{reset_code} {line}", end='', flush=True)

def main():
    print("=" * 70)
    print(" ABSs v2.0 — CLOUDFLARE / STRIPE-LEVEL ZERO-TRUST SaaS PLATFORM")
    print("=" * 70)
    print(" Verifying database schema and seeding SOC real-time telemetry...")
    
    # Run database initialization synchronously first
    init_cmd = [sys.executable, "-c", "import sys; sys.path.insert(0, 'src'); import asyncio; from db.database import init_db; asyncio.run(init_db())"]
    subprocess.run(init_cmd, check=True)
    print(" Database verified and active firewall proxy matrix loaded.\n")

    processes = []
    try:
        # 1. Launch FastAPI Backend API Gateway on Port 8000
        print(" Starting FastAPI Backend Gateway on http://localhost:8000 ...")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
        
        api_cmd = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        api_process = subprocess.Popen(api_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        processes.append(api_process)
        threading.Thread(target=stream_logs, args=(api_process, "[BACKEND API]  |", "\033[32m"), daemon=True).start()

        # Wait a moment for API to bind
        time.sleep(2)

        # 2. Launch Next.js SaaS Frontend on Port 3000
        print(" Starting Next.js SaaS Frontend on http://localhost:3000 ...")
        frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "abs-frontend")
        
        npm_cmd = "npm run dev" if os.name != 'nt' else "npm.cmd run dev"
        fe_process = subprocess.Popen(npm_cmd, cwd=frontend_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, shell=(os.name=='nt'))
        processes.append(fe_process)
        threading.Thread(target=stream_logs, args=(fe_process, "[FRONTEND UI]  |", "\033[36m"), daemon=True).start()

        print("\n" + "=" * 70)
        print(" PLATFORM ONLINE AND LINED UP FOR REAL-TIME TELEMETRY")
        print(" Frontend UI : http://localhost:3000")
        print(" API Gateway : http://localhost:8000/docs")
        print(" SOC Login   : admin@abss.internal | Password: Admin123!")
        print("=" * 70)
        print(" Press Ctrl+C to terminate all services safely.\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n Shutting down SaaS Platform processes...")
        for p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        sys.exit(0)

if __name__ == "__main__":
    main()
