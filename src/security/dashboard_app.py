
import json
import time
import os
import shutil
import streamlit as st
from pathlib import Path
from datetime import datetime
import pandas as pd

# Title and Config
st.set_page_config(page_title=" SecureAgent Live Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Dark grid/glassmorphism aesthetics */
    .stApp {
        background-color: #0e1117;
        background-image: 
            linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 30px 30px;
        color: #c9d1d9;
    }
    
    /* Gradient text for headers */
    h1, h2, h3 {
        background: -webkit-linear-gradient(45deg, #00f2fe, #4facfe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    /* Sleek card backgrounds for metrics */
    div[data-testid="stMetricValue"] {
        color: #ffffff;
    }
    div[data-testid="stMetric"] {
        background: rgba(30, 30, 35, 0.6);
        border: 1px solid #3d4450;
        border-radius: 12px;
        padding: 20px;
        backdrop-filter: blur(12px);
    }
    
    /* Hover animations on metrics (scale and glowing borders) */
    div[data-testid="stMetric"]:hover {
        transform: scale(1.04);
        box-shadow: 0 0 20px rgba(79, 172, 254, 0.4);
        border-color: #4facfe;
    }
    
    /* Button scale animations */
    .stButton>button {
        background: linear-gradient(135deg, rgba(40,40,45,0.9), rgba(30,30,35,0.9)) !important;
        border: 1px solid #4a5360 !important;
        color: #e6edf3 !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        border-radius: 8px;
    }
    .stButton>button:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 4px 12px rgba(0, 242, 254, 0.2) !important;
        border-color: #00f2fe !important;
    }

    /* DataFrame styling for sleek event blocks */
    div[data-testid="stDataFrame"] {
        background: rgba(20, 22, 26, 0.7);
        border-radius: 8px;
        border: 1px solid #3d4450;
        backdrop-filter: blur(8px);
    }

    /* Event feed containers (Task Cards simulation) */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background: linear-gradient(145deg, rgba(25,27,33,0.8) 0%, rgba(18,20,25,0.8) 100%) !important;
        border: 1px solid rgba(80, 200, 255, 0.15) !important;
        border-radius: 14px !important;
        padding: 18px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
    }
    div[data-testid="stVerticalBlock"] > div[style*="border"]:hover {
        transform: translateX(8px) !important;
        border-left: 4px solid #00f2fe !important;
        box-shadow: 0 10px 25px rgba(0, 242, 254, 0.2) !important;
    }
    
    /* Removed Entry Animation to prevent React unmount ghosting */
</style>
""", unsafe_allow_html=True)

# Paths
BASE_DIR = Path(__file__).parent.resolve()
DASHBOARD_DIR = BASE_DIR / "dashboard"
LOG_FILE = DASHBOARD_DIR / "security_events.jsonl"
SCREENSHOTS_DIR = DASHBOARD_DIR / "screenshots"
KILL_FLAG = DASHBOARD_DIR / "kill.flag"
PIDS_FILE = DASHBOARD_DIR / "pids.json"

def add_pid(pid):
    pids = []
    if PIDS_FILE.exists():
        try:
            with open(PIDS_FILE, "r", encoding="utf-8") as f:
                pids = json.load(f)
        except Exception:
            pass
    if pid not in pids:
        pids.append(pid)
    with open(PIDS_FILE, "w", encoding="utf-8") as f:
        json.dump(pids, f)

# Initialize Session State
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False

# Sidebar
st.sidebar.title(" Zero-Trust Security")
page = st.sidebar.radio("Navigation", ["Live Feed", "Risk Analysis", "XAI Explanations", "DOM Diff Visualizer", "Agent Console", "Policy Engine", "About the Project"])

st.sidebar.markdown("---")
st.sidebar.header("Monitor Controls")

if LOG_FILE.exists():
    st.sidebar.caption(f" Log file active")
else:
    st.sidebar.caption(f" Log file missing")

auto_refresh = st.sidebar.checkbox("Auto-Refresh (2s)", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("� Emergency Controls")

if KILL_FLAG.exists():
    st.sidebar.error("SYSTEM HALTED. Agent execution locked.")
    if st.sidebar.button(" Reset System"):
        os.remove(KILL_FLAG)
        st.rerun()
else:
    if st.sidebar.button(" ENGAGE KILL SWITCH", type="primary", width='stretch'):
        with open(KILL_FLAG, "w") as f:
            f.write("HALT")
        
        import subprocess
        if PIDS_FILE.exists():
            try:
                with open(PIDS_FILE, "r", encoding="utf-8") as f:
                    pids = json.load(f)
                for pid in pids:
                    try:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False)
                    except Exception:
                        pass
                with open(PIDS_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception as e:
                st.sidebar.error(f"Error killing processes: {e}")

        st.toast("Kill signal sent to Agent & processes terminated!")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("�🚫 Danger Zone")

if st.sidebar.button(" Clear Logs & Evidence"):
    st.session_state.confirm_delete = True

if st.session_state.confirm_delete:
    st.sidebar.warning("Do you really wanna clear logs and delete screenshots?")
    col_confirm1, col_confirm2 = st.sidebar.columns(2)
    if col_confirm1.button("Yes, Delete"):
        if LOG_FILE.exists():
            os.remove(LOG_FILE)
        if SCREENSHOTS_DIR.exists():
            try:
                shutil.rmtree(SCREENSHOTS_DIR)
                os.makedirs(SCREENSHOTS_DIR)
            except Exception as e:
                st.sidebar.error(f"Error deleting screenshots: {e}")
        st.session_state.confirm_delete = False
        st.sidebar.success("All data wiped.")
        time.sleep(1)
        st.rerun()
    if col_confirm2.button("Cancel"):
        st.session_state.confirm_delete = False
        st.rerun()

# Load Data
events = []
if LOG_FILE.exists():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
    except Exception as e:
        st.error(f"Error reading logs: {e}")

# Helper to format timestamp
def get_formatted_time(timestamp):
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return ""

# Common Metrics
total_events = len(events)
injections_blocked = sum(1 for e in events if e.get('event_type') == 'INJECTION_ATTEMPT')
critical_threats = sum(1 for e in events if e.get('risk_level') == 'CRITICAL')
hostile_domains = len(set(e.get('url') for e in events if e.get('risk_level') in ['HIGH', 'CRITICAL']))
avg_risk = sum(e.get('risk_score', 0) for e in events) / max(total_events, 1)

# --- PAGE: LIVE FEED ---
if page == "Live Feed":
    st.title(" Real-time Security Feed")

    # Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Events", total_events)
    col2.metric("Injections Blocked", injections_blocked, delta_color="normal")
    col3.metric("Critical Threats", critical_threats, delta_color="inverse")
    col4.metric("Hostile Domains", hostile_domains)
    col5.metric("Avg Risk Score", f"{avg_risk:.0f}/100")

    st.divider()

    # Display Events (Latest First)
    for idx, event in enumerate(reversed(events)):
        # Skip risk assessment events in live feed (too noisy)
        if event.get('event_type') == 'RISK_ASSESSMENT' and event.get('risk_level') == 'LOW':
            continue

        color = "gray"
        lvl = event.get('risk_level', 'SAFE')
        if lvl == 'CRITICAL': color = "red"
        elif lvl == 'HIGH': color = "orange"
        elif lvl == 'MEDIUM': color = "yellow"
        elif lvl == 'SAFE': color = "green"

        risk_score = event.get('risk_score', 0)

        with st.container(border=True, key=f"live_feed_{idx}"):
            cols = st.columns([1.5, 2, 4, 1.5, 1.5])

            timestamp_val = event.get('timestamp')
            display_time = get_formatted_time(timestamp_val) if timestamp_val else event.get('time_str', 'N/A')

            cols[0].caption(f" {display_time}")
            cols[1].markdown(f"**:{color}[{event.get('event_type')}]**")
            cols[2].write(f"{event.get('details')} \n\n  `{event.get('url', 'N/A')}`")
            
            # Action badge
            action_color = "gray"
            if event.get('action') in ['BLOCKED', 'SANITIZED', 'BLOCK_AND_ESCALATE']: action_color = "red"
            elif event.get('action') == 'WARNED': action_color = "orange"
            elif event.get('action') == 'ALLOWED': action_color = "green"
            
            cols[3].markdown(f"Action: **:{action_color}[{event.get('action')}]**")

            # Progressive Risk Bar
            if risk_score > 0:
                prog_color = "" if risk_score <= 30 else "" if risk_score <= 70 else ""
                cols[4].markdown(f"**Risk: {prog_color} {risk_score}/100**")
                cols[4].progress(risk_score / 100.0)
            else:
                cols[4].markdown(f"**Risk:  0/100**")

            # XAI Explanation
            explanation = event.get('explanation')
            if explanation:
                st.info(f" **AI Explanation:** {explanation}")

            if event.get('screenshot'):
                try:
                    raw_path = event['screenshot']
                    filename = raw_path.replace('\\', '/').split('/')[-1]
                    local_path = SCREENSHOTS_DIR / filename
                    if local_path.exists():
                        st.image(str(local_path), caption="Evidence Snapshot", width=400)
                except Exception:
                    pass

# --- PAGE: RISK ANALYSIS ---
elif page == "Risk Analysis":
    st.title(" Risk Score Analysis")

    if total_events == 0:
        st.info("No data available yet. Run the agent to generate traffic.")
    else:
        df = pd.DataFrame(events)
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')

        # Stats Overview
        st.header(" Activity Overview")
        unique_sites = df['url'].nunique() if 'url' in df.columns else 0
        malicious_count = df[df['risk_level'].isin(['HIGH', 'CRITICAL'])]['url'].nunique() if 'risk_level' in df.columns else 0
        blocked_count = df[df['action'].isin(['BLOCKED', 'SANITIZED', 'WARNED', 'BLOCK_AND_ESCALATE'])]['url'].count() if 'action' in df.columns else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(" Unique Sites", unique_sites)
        m2.metric(" Malicious Domains", malicious_count, delta_color="inverse")
        m3.metric(" Interventions", blocked_count)
        m4.metric(" Avg Risk", f"{avg_risk:.0f}/100")

        st.divider()

        with st.container(key="risk_analysis_charts_view"):
            # Risk Score Timeline
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Risk Score Timeline")
                if 'risk_score' in df.columns and 'datetime' in df.columns:
                    risk_df = df[df['risk_score'] > 0][['datetime', 'risk_score']].set_index('datetime')
                    if not risk_df.empty:
                        st.line_chart(risk_df, color="#ff4b4b")
                    else:
                        st.info("No risk scores yet.")
    
            with g2:
                st.subheader("Threat Severity Distribution")
                if 'risk_level' in df.columns:
                    risk_counts = df['risk_level'].value_counts()
                    st.bar_chart(risk_counts, color="#ff4b4b")
    
            st.divider()
    
            # Risk Score Distribution
            st.subheader("Risk Score Distribution")
            if 'risk_score' in df.columns:
                risk_scores = df[df['risk_score'] > 0]['risk_score']
                if not risk_scores.empty:
                    col_low, col_med, col_high = st.columns(3)
                    col_low.metric(" Low (0-30)", len(risk_scores[risk_scores <= 30]))
                    col_med.metric(" Medium (31-70)", len(risk_scores[(risk_scores > 30) & (risk_scores <= 70)]))
                    col_high.metric(" High (71-100)", len(risk_scores[risk_scores > 70]))
    
            st.divider()
    
            # Event Types
            st.subheader("Event Types")
            if 'event_type' in df.columns:
                type_counts = df['event_type'].value_counts()
                st.bar_chart(type_counts, horizontal=True)

        st.divider()

        # Detailed Tables
        st.subheader("� Threat Event Timeline")
        # Ensure we only work with available columns and avoid KeyErrors
        display_cols = []
        for c in ['datetime', 'risk_score', 'event_type', 'action', 'url', 'details']:
            if c in df.columns:
                display_cols.append(c)
                
        if display_cols:
            display_df = df.copy()
            # Sort by datetime if it exists
            if 'datetime' in df.columns:
                display_df = display_df.sort_values(by='datetime', ascending=False)
            
            # Format the output for the dataframe viewer gracefully
            st.dataframe(
                display_df[display_cols].style.highlight_max(axis=0, subset=['risk_score'] if 'risk_score' in display_cols else []),
                hide_index=True 
            )

# --- PAGE: XAI EXPLANATIONS ---
elif page == "XAI Explanations":
    st.title(" Explainable AI — Security Decisions")
    st.caption("LLM-generated explanations for every blocked or flagged action")

    explanation_events = [e for e in events if e.get('explanation')]
    
    if not explanation_events:
        st.info("No XAI explanations yet. Explanations are generated when actions are blocked.")
    else:
        for idx, event in enumerate(reversed(explanation_events)):
            risk_score = event.get('risk_score', 0)
            
            with st.container(border=True, key=f"xai_expl_{idx}"):
                cols = st.columns([1, 5])
                
                # Risk gauge
                if risk_score >= 71:
                    cols[0].markdown(f"### :red[{risk_score}/100]")
                    cols[0].caption(" HIGH RISK")
                elif risk_score >= 31:
                    cols[0].markdown(f"### :orange[{risk_score}/100]")
                    cols[0].caption(" MEDIUM")
                else:
                    cols[0].markdown(f"### :green[{risk_score}/100]")
                    cols[0].caption(" LOW")

                timestamp_val = event.get('timestamp')
                display_time = get_formatted_time(timestamp_val) if timestamp_val else ''
                
                cols[1].markdown(f"**{event.get('event_type', 'UNKNOWN')}** — {display_time}")
                cols[1].markdown(f"> {event.get('explanation', 'No explanation available.')}")
                cols[1].caption(f" {event.get('url', 'N/A')} | Action: {event.get('action', 'N/A')}")

                if event.get('screenshot'):
                    try:
                        raw_path = event['screenshot']
                        filename = raw_path.replace('\\', '/').split('/')[-1]
                        local_path = SCREENSHOTS_DIR / filename
                        if local_path.exists():
                            st.image(str(local_path), caption="Evidence Snapshot", width=400)
                    except Exception:
                        pass

# --- PAGE: DOM DIFF VISUALIZER ---
elif page == "DOM Diff Visualizer":
    colA, colB = st.columns([4, 1])
    with colA:
        st.title("DOM Diff Visualizer")
        st.markdown("Displays a historical timeline of all intercepted DOM modifications.")
    with colB:
        st.write("")
        st.write("")
        if st.button("🗑️ Clear Diffs", type="primary", use_container_width=True):
            diff_dir = DASHBOARD_DIR / "diffs"
            if diff_dir.exists():
                import shutil
                shutil.rmtree(diff_dir)
                diff_dir.mkdir(exist_ok=True)
            st.toast("Diff history cleared!", icon="✅")
            st.rerun()

    import difflib
    
    diff_dir = DASHBOARD_DIR / "diffs"
    
    if diff_dir.exists():
        # Find all raw files and sort latest first
        raw_files = sorted(list(diff_dir.glob("*_raw.txt")), reverse=True)
        
        # Fallback to latest_raw if it exists from older runs
        if not raw_files and (diff_dir / "latest_raw.txt").exists():
            raw_files = [diff_dir / "latest_raw.txt"]
            
        if not raw_files:
            st.info("No DOM modifications detected or agent hasn't run yet.")
        else:
            for idx, raw_path in enumerate(raw_files):
                # Try to find corresponding sanitized file
                if raw_path.name == "latest_raw.txt":
                    sanitized_path = diff_dir / "latest_sanitized.txt"
                    header_title = "Legacy Latest DOM Diff"
                else:
                    ts_str = raw_path.name.replace("diff_", "").replace("_raw.txt", "")
                    sanitized_path = diff_dir / f"diff_{ts_str}_sanitized.txt"
                    try:
                        dt = datetime.fromtimestamp(int(ts_str) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                        header_title = f"DOM Intercept at {dt}"
                    except:
                        header_title = f"DOM Intercept ({ts_str})"
                
                if sanitized_path.exists():
                    with st.expander(f"🔍 {header_title}", expanded=(idx == 0)):
                        with open(raw_path, "r", encoding="utf-8") as f:
                            raw_text = f.readlines()
                        with open(sanitized_path, "r", encoding="utf-8") as f:
                            sanitized_text = f.readlines()
                            
                        diff_html = difflib.HtmlDiff(wrapcolumn=90).make_table(
                            raw_text, sanitized_text,
                            context=True,
                            numlines=5,
                            fromdesc="Raw Source DOM",
                            todesc="Sanitized DOM (Agent View)"
                        )
                        
                        st.components.v1.html(f'''
                            <style>
                            table.diff {{font-family: Courier, monospace; border: 1px solid #ddd; width: 100%}}
                            .diff_header {{background-color: #e0e0e0; padding: 2px 5px;}}
                            td.diff_header {{text-align:right}}
                            .diff_next {{background-color: #c0c0c0;}}
                            .diff_add {{background-color: #aaffaa;}}
                            .diff_chg {{background-color: #ffff77;}}
                            .diff_sub {{background-color: #ffaaaa;}}
                            </style>
                            <div style="background-color: #ffffff; color: #000000; padding: 20px; border-radius: 8px; overflow-x: auto;">
                                {diff_html}
                            </div>
                        ''', height=500, scrolling=True)
    else:
        st.info("No DOM modifications detected or agent hasn't run yet.")

# --- PAGE: AGENT CONSOLE ---
elif page == "Agent Console":
    st.title(" Secure Agent Control Center")
    st.markdown("Command your AI Agent safely locally. When testing custom sites, the agent will verify domains, sanitize DOMs, and protect data automatically.")
    
    st.subheader("1. General Web Automation (Real World)")
    user_prompt_real = st.text_area("Your Command:", placeholder="e.g. Go to amazon.com, search for laptops, and summarize the top 3 results without adding anything to cart.", height=100, key="real_world_prompt")

    if st.button(" Execute on Real Web", type="primary"):
        if user_prompt_real:
            st.toast("Agent launching! Switch to 'Live Feed' to watch its security operations.")
            import subprocess
            import sys
            proc = subprocess.Popen([sys.executable, "main_secure.py", user_prompt_real])
            add_pid(proc.pid)
        else:
            st.warning("Please type a command first!")
    
    st.divider()

    st.subheader("2. Debug / Hackathon Evaluation Server")
    st.caption("Use these scenarios to demonstrate the agent deflecting specific attack vectors.")
    
    colA, colB = st.columns([3, 1])
    with colA:
        st.info("The local test server must be running (`http://127.0.0.1:5001`) to evaluate Vector Logic.")
    with colB:
        if st.button(" Start Local Attack Server", width='stretch'):
            import subprocess
            import sys
            proc = subprocess.Popen([sys.executable, "attack_server.py"])
            add_pid(proc.pid)
            st.toast("Server initialized!")

    # Dynamically find all vector_*.html files
    project_root = BASE_DIR.parent.parent
    vector_files = sorted(project_root.glob("vector_*.html"))
    
    scenarios = ["Select Scenario..."]
    prompt_mapping = {}
    
    for vf in vector_files:
        filename = vf.name
        # Format name, e.g., vector_1_prompt_injection.html -> Test Vector 1: Prompt Injection
        parts = filename.replace('.html', '').split('_', 2)
        if len(parts) >= 3:
            display_name = f"Test Vector {parts[1]}: {parts[2].replace('_', ' ').title()}"
        else:
            display_name = f"Test Vector: {filename}"
            
        scenarios.append(display_name)
        prompt_mapping[display_name] = f"Go to http://127.0.0.1:5001/{filename} and interact with the page."

    preset = st.selectbox("Quick Select Attack Scenario:", scenarios)
    
    default_text = prompt_mapping.get(preset, "")
    
    user_prompt_test = st.text_area("Test Instructions:", value=default_text, height=100, key="test_world_prompt", disabled=True if not default_text else False)
    
    if st.button(" Launch Hackathon Test", type="secondary"):
        if user_prompt_test:
            st.toast("Evaluation initialized! Switch to 'Live Feed'.")
            import subprocess
            import sys
            proc = subprocess.Popen([sys.executable, "main_secure.py", user_prompt_test])
            add_pid(proc.pid)
        else:
            st.warning("Please select a scenario!")

# --- PAGE: POLICY ENGINE ---
elif page == "Policy Engine":
    st.title(" EnterprisePolicy Engine (RBAC)")
    st.markdown("Configure hard constraints for the AI Agent. Policies are applied instantly across all live sessions.")
    
    import json
    
    POLICIES_JSON = DASHBOARD_DIR / "policies.json"
    
    # Load current policies
    if POLICIES_JSON.exists():
        with open(POLICIES_JSON, "r") as f:
            current_policies = json.load(f)
    else:
        current_policies = {
            "block_domains": ["*.ru", "*.cn", "bit.ly", "tinyurl.com", "pastebin.com"],
            "block_input_patterns": ["password", "ssn", "credit_card", "secret_key"],
            "max_risk_tolerance": 75,
            "require_human_approval": False,
            "blocked_actions": []
        }

    with st.form("policy_form"):
        st.subheader(" Network Constraints")
        domains_val = st.text_area("Blocked Domains (comma separated, wildcards allowed)", 
                                   value=", ".join(current_policies.get("block_domains", [])))

        st.subheader(" Data Loss Prevention (DLP)")
        inputs_val = st.text_area("Blocked Input Patterns / Regex (comma separated)", 
                                  value=", ".join(current_policies.get("block_input_patterns", [])))

        st.subheader(" Action Sandbox")
        actions_val = st.text_area("Blocked Actions (Blacklist, comma separated)", 
                                   value=", ".join(current_policies.get("blocked_actions", [])))

        st.subheader(" Risk Overrides")
        risk_tolerance = st.slider("Absolute Maximum Risk Tolerance (Auto-Block over this score)", 
                                   min_value=0, max_value=100, 
                                   value=current_policies.get("max_risk_tolerance", 75))

        human_approval = st.checkbox("Require HITL Approval for all High-Risk Actions (Coming Soon)", 
                                     value=current_policies.get("require_human_approval", False))

        submitted = st.form_submit_button(" Save Policies", type="primary")
        if submitted:
            # Process inputs
            new_policies = {
                "block_domains": [d.strip() for d in domains_val.split(",") if d.strip()],
                "block_input_patterns": [p.strip() for p in inputs_val.split(",") if p.strip()],
                "blocked_actions": [a.strip() for a in actions_val.split(",") if a.strip()],
                "max_risk_tolerance": risk_tolerance,
                "require_human_approval": human_approval
            }
            
            with open(POLICIES_JSON, "w") as f:
                json.dump(new_policies, f, indent=4)
            st.success("Enterprise Policies successfully updated and deployed to all active agents.")
            time.sleep(1)
            st.rerun()

# --- PAGE:About the Project ---
elif page == "About the Project":
    st.title("About the Project")
    st.markdown("The SecureAgent Browser Security Suite is a **zero-trust proxy** designed to monitor, control, and audit autonomous AI agents interacting with the web. It ensures the primary agent only operates within defined bounds and prevents malicious prompt injections or data exfiltration.")
    
    st.write("---")
    
    st.subheader("Architecture Flow")
    st.markdown("The system implements a **Supervisor-Actor architecture** where the primary agent performs actions, and a secondary guardrail LLM evaluates the safety and intent before execution.")
    
    # Mermaid Diagram rendering natively with components
    st.components.v1.html("""
        <div class="mermaid" style="display: flex; justify-content: center; background-color: transparent;">
            graph TD
                A[Autonomous Agent] -->|Playwright Action| B(Zero-Trust Proxy)
                B --> C{Policy Engine}
                C -->|Allowed by Static Rules| D[Target Website]
                C -->|Suspicious / Dynamic| E[Guardrail Supervisor LLM]
                E -->|Classified Malicious| F[Blocked & Explained via XAI]
                E -->|Classified Safe| D
                
                style A fill:#2D3748,stroke:#4A5568,color:#fff
                style B fill:#2b6cb0,stroke:#2c5282,color:#fff
                style C fill:#4A5568,stroke:#2D3748,color:#fff
                style D fill:#38a169,stroke:#276749,color:#fff
                style E fill:#805ad5,stroke:#553c9a,color:#fff
                style F fill:#e53e3e,stroke:#9b2c2c,color:#fff
        </div>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({ startOnLoad: true, theme: 'dark' });
        </script>
    """, height=650, scrolling=True)
    
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Key Components")
        st.markdown("""
        - **Intent Authorization:** Checks Enterprise Policies & RBAC constraints on LLM actions via the Policy Engine.
        - **Data Loss Prevention (DLP):** Monitors outbound network traffic for cross-origin forms and stolen data tokens.
        - **DOM Sanitization:** Strips visual obfuscation and prompt injections from the DOM before the Agent sees it.
        """)
    with col2:
        st.subheader("Explainable AI (XAI)")
        st.markdown("""
        - **Real-time Auditing:** Uses a secondary Gemini model to evaluate interactions and score risk out of 100.
        - **Transparent Decisions:** Every blocked action logs a detailed explanation of *why* the proxy intervened directly into the dashboard.
        """)

if auto_refresh:
    time.sleep(2)
    st.rerun()
