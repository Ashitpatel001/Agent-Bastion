import os
import sys
import subprocess
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("=" * 60)
    print("     SECURE AGENT BROWSER SECURITY SUITE  ")
    print("=" * 60)
    print("      Hackathon Submission - Easy Launcher")
    print("=" * 60)

def stream_logs(process, prefix):
    """Read output from a subprocess and print it with a prefix."""
    for line in iter(process.stdout.readline, ''):
        print(f"{prefix} {line}", end='')

def launch_all_in_one():
    """Runs Server, Dashboard, and Agent concurrently in a single terminal using threads."""
    clear_screen()
    print_header()
    print("\n Launching FULL Hackathon Demo (Unified Terminal)...")
    
    try:
        # Start Attack Server
        server_cmd = [sys.executable, "attack_server.py"]
        server_process = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        threading.Thread(target=stream_logs, args=(server_process, "  [SERVER]   | "), daemon=True).start()
        
        # Start Dashboard
        dash_cmd = [sys.executable, "-m", "streamlit", "run", "src/security/dashboard_app.py", "--server.headless", "true"]
        dash_process = subprocess.Popen(dash_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        threading.Thread(target=stream_logs, args=(dash_process, " [DASHBOARD]| "), daemon=True).start()
        
        # Give them a second to initialize
        time.sleep(3)
        
        # Start Secure Agent
        print("\n" + "=" * 60)
        print(" [AGENT]    | Initializing Secure Agent Execution...")
        agent_cmd = [sys.executable, os.path.join("examples", "demo_standalone.py")]
        agent_process = subprocess.Popen(agent_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        threading.Thread(target=stream_logs, args=(agent_process, " [AGENT]    | "), daemon=True).start()
        
        # Block until agent finishes
        agent_process.wait()
        print("\n Task Complete! Press Ctrl+C to terminate Server and Dashboard.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n Shutting down all processes...")
        if 'server_process' in locals(): server_process.kill()
        if 'dash_process' in locals(): dash_process.kill()
        if 'agent_process' in locals(): agent_process.kill()
        sys.exit(0)

def install_dependencies():
    print("\n📦 Installing dependencies from requirements.txt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\n📦 Installing explicitly: langchain-google-genai...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain-google-genai"])
        print("\n Dependencies installed successfully!")
        time.sleep(2)
    except subprocess.CalledProcessError:
        print("\n Error installing dependencies.")
        input("Press Enter to continue...")

def start_attack_server():
    print("\n Starting Attack Server (Port 5001)...")
    print("   (This runs in a new window/process)")
    try:
        if os.name == 'nt':
            # Use specific quoting to handle paths with spaces
            cmd = f'"{sys.executable}" attack_server.py'
            subprocess.Popen(f'start cmd /k "{cmd}"', shell=True)
        else:
            subprocess.Popen([sys.executable, "attack_server.py"]) 
            print("   Running in background...")
    except Exception as e:
        print(f" Failed to start server: {e}")

def start_dashboard():
    print("\n Starting Security Dashboard...")
    print("   (Opening Streamlit app)")
    try:
        cmd = f'"{sys.executable}" -m streamlit run src/security/dashboard_app.py'
        if os.name == 'nt':
             # Use specific quoting to handle paths with spaces
            subprocess.Popen(f'start cmd /k "{cmd}"', shell=True)
        else:
            subprocess.Popen([sys.executable, "-m", "streamlit", "run", "src/security/dashboard_app.py"])
    except Exception as e:
        print(f" Failed to start dashboard: {e}")

def run_secure_agent_default():
    print("\n🕵️  Running Secure Agent (Default Task)...")
    try:
        subprocess.run([sys.executable, os.path.join("examples", "demo_standalone.py")])
    except Exception as e:
        print(f" Error running agent: {e}")
    input("\nPress Enter to return to menu...")

def run_secure_agent_custom():
    print("\n🕵️  Running Secure Agent (Custom Task)...")
    task = input("   👉 Enter your custom prompt/task: ")
    if not task.strip():
        print("    No task entered. Returning...")
        return
    
    try:
        subprocess.run([sys.executable, os.path.join("examples", "demo_standalone.py"), task])
    except Exception as e:
        print(f" Error running agent: {e}")
    input("\nPress Enter to return to menu...")

def launch_saas_platform():
    print("\n 🚀 Enterprise SaaS platform is managed via Docker Compose:")
    print("   👉 Run: docker compose up --build -d")
    input("\nPress Enter to return to menu...")

def main_menu():
    while True:
        clear_screen()
        print_header()
        print("\n   [1] 📦 Install/Update Dependencies")
        print("   [2]   Start Attack Server (Simulation Env)")
        print("   [3]  Start Legacy Security Dashboard (Streamlit)")
        print("   [4]  Run Secure Agent (Default Validation)")
        print("   [5]  Run Secure Agent (Custom Prompt)")
        print("   [6]  Launch FULL Hackathon Demo (All-in-One Threaded)")
        print("   [7] 🚀 Launch Cloudflare/Stripe-Level SaaS Platform (FastAPI + Next.js UI)")
        print("\n   [0] 🚪 Exit")
        print("-" * 60)
        
        choice = input("   Select an option: ")
        
        if choice == '1':
            install_dependencies()
        elif choice == '2':
            start_attack_server()
        elif choice == '3':
            start_dashboard()
        elif choice == '4':
            run_secure_agent_default()
        elif choice == '5':
            run_secure_agent_custom()
        elif choice == '6':
            launch_all_in_one()
        elif choice == '7':
            launch_saas_platform()
        elif choice == '0':
            print("\n👋 Exiting. Goodbye!")
            sys.exit(0)
        else:
            input("    Invalid choice. Press Enter...")

if __name__ == "__main__":
    main_menu()