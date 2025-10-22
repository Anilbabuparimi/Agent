update current_system also
import streamlit as st
from shared_header import (
    render_header,
    render_admin_panel,
    save_feedback_to_admin_session,
    render_unified_business_inputs,
    get_shared_data,
    ACCOUNTS,
    INDUSTRIES,
    ACCOUNT_INDUSTRY_MAP,
    _safe_rerun
)
import requests
import json
import os
import re
import pandas as pd
from datetime import datetime


# =========================================
# 🧭 PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="Current System Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================
# ⚙️ SESSION INITIALIZATION - AGENT-SPECIFIC FEEDBACK
# =========================================
session_defaults = {
    'dark_mode': False,
    'saved_account': "Select Account",
    'saved_industry': "Select Industry",
    'saved_problem': "",
    'current_system_extracted': False,
    'current_system_data': "",
    # AGENT-SPECIFIC FEEDBACK TRACKING
    'current_system_feedback_submitted': False,  # Unique to this agent
    # ADMIN STATES
    'admin_access_requested': False,
    'admin_authenticated': False,
    'current_page': '',
    'show_admin_panel': False,
    'admin_view_selected': False,
}
for key, val in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# =========================================
# 🌐 API CONFIGURATION
# =========================================
TENANT_ID = "talos"
AUTH_TOKEN = None
HEADERS_BASE = {"Content-Type": "application/json"}

CURRENT_SYSTEM_API_URL = (
    "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api"
    "?society_id=1757657318406&agency_id=1758549095254&level=1"
)

API_CONFIGS = [
    {
        "name": "current_system",
        "url": CURRENT_SYSTEM_API_URL,
        "multiround_convo": 2,
        "description": "Current System in Place",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\n"
            f"Context from vocabulary:\n{outputs.get('vocabulary', '')}\n\n"
            "Describe the current system, inputs, outputs, and pain points in detail with clear sections."
        )
    }
]

# =========================================
# 📁 FILE CONFIG
# =========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

# =========================================
# 🧹 HELPER FUNCTIONS
# =========================================
def json_to_text(data):
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("result", "output", "content", "text"):
            if key in data and data[key]:
                return json_to_text(data[key])
        if "data" in data:
            return json_to_text(data["data"])
        return "\n".join(f"{k}: {json_to_text(v)}" for k, v in data.items() if v)
    if isinstance(data, list):
        return "\n".join(json_to_text(x) for x in data if x)
    return str(data)


def sanitize_text(text):
    """Remove markdown artifacts and clean up text"""
    if not text:
        return ""

    # Fix the "s" character issue - remove stray 's' characters at the beginning
    text = re.sub(r'^\s*s\s+', '', text.strip())
    text = re.sub(r'\n\s*s\s+', '\n', text)

    # Remove --- lines
    text = re.sub(r'^---\s*$', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'Q\d+\s*Answer\s*Explanation\s*:',
                  '', text, flags=re.IGNORECASE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'<\/?[^>]+>', '', text)
    text = re.sub(r'&', '&', text)
    text = re.sub(r'& Key Takeaway:', 'Key Takeaway:', text)

    return text.strip()


def format_current_system_with_bold(text, extra_phrases=None):
    """
    Format Current System output with bold styling.
    Formats current system text with bold patterns and proper structure.
    """
    if not text:
        return "No current system data available"

    # Sanitize text
    try:
        clean_text = sanitize_text(text)
    except NameError:
        clean_text = text

    # Remove numbered sections like "2." and "3." etc.
    clean_text = re.sub(r'^\s*\d+\.\s*', '', clean_text, flags=re.MULTILINE)
    
    # Basic normalization
    clean_text = clean_text.replace(" - ", " : ")
    clean_text = re.sub(r'(?m)^\s*[-*]\s+', '• ', clean_text)

    # Prepare extra phrase patterns
    extra_patterns = []
    if extra_phrases:
        for p in extra_phrases:
            if any(ch in p for ch in r".^$*+?{}[]\|()"):
                extra_patterns.append(p)
            else:
                extra_patterns.append(re.escape(p))

    lines = clean_text.splitlines()
    n = len(lines)
    i = 0
    paragraph_html = []

    def collect_continuation(start_idx):
        """Collect continuation lines for block-style headings."""
        block_lines = [lines[start_idx].rstrip()]
        j = start_idx + 1
        while j < n:
            next_line = lines[j]
            if not next_line.strip():
                break
            if re.match(r'^\s+', next_line) or re.match(r'^\s*[a-z]', next_line):
                block_lines.append(next_line.rstrip())
                j += 1
                continue
            if re.match(r'^\s*(?:•|-|\d+\.)\s+', next_line):
                break
            break
        return block_lines, j

    while i < n:
        ln = lines[i].rstrip()
        if not ln.strip():
            paragraph_html.append('')
            i += 1
            continue

        # Extra phrases
        if extra_patterns:
            new_ln = ln
            for pat in extra_patterns:
                try:
                    new_ln = re.sub(
                        pat, lambda m: f"<strong>{m.group(0)}</strong>", new_ln, flags=re.IGNORECASE)
                except re.error:
                    new_ln = re.sub(re.escape(
                        pat), lambda m: f"<strong>{m.group(0)}</strong>", new_ln, flags=re.IGNORECASE)
            if new_ln != ln:
                paragraph_html.append(new_ln)
                i += 1
                continue

        # Section headers (Current System, Inputs, Outputs, Pain Points)
        if re.match(r'^\s*(Current\s+System|Inputs?|Outputs?|Pain\s+Points?|System\s+Description)', ln, flags=re.IGNORECASE):
            paragraph_html.append(
                f"<strong style='font-size:1.1rem; color: var(--text-primary);'>{ln.strip()}</strong>")
            i += 1
            continue

        # Numbered heading WITH colon
        m_num_colon = re.match(r'^\s*(\d+\.\s+[^:]+):\s*(.*)$', ln)
        if m_num_colon:
            heading = m_num_colon.group(1).strip()
            remainder = m_num_colon.group(2).strip()
            if remainder:
                paragraph_html.append(
                    f"<strong style='color: var(--text-primary);'>{heading}:</strong> {remainder}")
            else:
                paragraph_html.append(f"<strong style='color: var(--text-primary);'>{heading}:</strong>")
            i += 1
            continue

        # Numbered heading WITHOUT colon
        m_num_no_colon = re.match(r'^\s*(\d+\.\s+.+)$', ln)
        if m_num_no_colon:
            block, j = collect_continuation(i)
            block_text = "<br>".join([b.strip() for b in block])
            paragraph_html.append(f"<strong style='color: var(--text-primary);'>{block_text}</strong>")
            i = j
            continue

        # Bullet with colon
        m_bullet_heading = re.match(r'^\s*(?:•|\d+\.)\s*([^:]+):\s*(.*)$', ln)
        if m_bullet_heading:
            heading = m_bullet_heading.group(1).strip()
            remainder = m_bullet_heading.group(2).strip()
            if remainder:
                paragraph_html.append(
                    f"• <strong style='color: var(--text-primary);'>{heading}:</strong> {remainder}")
            else:
                paragraph_html.append(f"• <strong style='color: var(--text-primary);'>{heading}:</strong>")
            i += 1
            continue

        # Generic inline heading "LeftOfColon: rest" - FIXED THIS PART
        m_side = re.match(r'^\s*([^:]+):\s*(.*)$', ln)
        if m_side and len(m_side.group(1).split()) <= 12:  # Increased word limit
            left = m_side.group(1).strip()
            right = m_side.group(2).strip()
            
            # Skip if it's a section header we already processed
            if not re.match(r'^\s*(Current\s+System|Inputs?|Outputs?|Pain\s+Points?|System\s+Description)', left, flags=re.IGNORECASE):
                paragraph_html.append(
                    f"<strong style='color: var(--text-primary);'>{left}:</strong> {right}" if right else f"<strong style='color: var(--text-primary);'>{left}:</strong>")
                i += 1
                continue

        # Handle bullet points with colons that might have been missed
        if ':' in ln and not ln.startswith('•'):
            parts = ln.split(':', 1)
            if len(parts) == 2 and len(parts[0].split()) <= 8:
                left = parts[0].strip()
                right = parts[1].strip()
                paragraph_html.append(f"<strong style='color: var(--text-primary);'>{left}:</strong> {right}")
                i += 1
                continue

        # Default
        paragraph_html.append(f"<span style='color: var(--text-primary);'>{ln}</span>")
        i += 1

    # Group into paragraphs
    final_paragraphs = []
    temp_lines = []
    for entry in paragraph_html:
        if entry == '':
            if temp_lines:
                final_paragraphs.append("<br>".join(temp_lines))
                temp_lines = []
        else:
            temp_lines.append(entry)
    if temp_lines:
        final_paragraphs.append("<br>".join(temp_lines))

    para_wrapped = [
        f"<p style='margin:6px 0; line-height:1.45; font-size:0.98rem; color: var(--text-primary);'>{p}</p>" for p in final_paragraphs]
    final_html = "\n".join(para_wrapped)

    return final_html


def parse_current_system_sections(text):
    """Split extracted text into structured sections"""
    sections = {
        "core_problem": "",
        "current_system": "",
        "inputs": "",
        "outputs": "",
        "pain_points": ""
    }

    if not text:
        return {k: "No data available" for k in sections}

    patterns = {
        "core_problem": r"(?:Core Problem|Business Problem)[:\n]",
        "current_system": r"(?:Current System)[:\n]",
        "inputs": r"(?:Inputs?)[:\n]",
        "outputs": r"(?:Outputs?)[:\n]",
        "pain_points": r"(?:Pain Points?)[:\n]"
    }

    matches = {k: re.search(v, text, re.IGNORECASE) for k, v in patterns.items()}
    keys = list(matches.keys())

    for i, key in enumerate(keys):
        if matches[key]:
            start = matches[key].end()
            end = None
            for nxt_key in keys[i + 1:]:
                if matches[nxt_key]:
                    end = matches[nxt_key].start()
                    break
            sections[key] = text[start:end].strip() if end else text[start:].strip()

    for k in sections:
        if not sections[k].strip():
            sections[k] = "No data available"

    return sections


def call_api(agent_name, problem, context=""):
    """Call the Talos API using centralized API_CONFIGS"""
    config = next((a for a in API_CONFIGS if a["name"] == agent_name), None)
    if not config:
        st.error("Invalid API configuration.")
        return None

    prompt = config["prompt"](problem, {"vocabulary": context})
    payload = {"agency_goal": prompt}

    headers = HEADERS_BASE.copy()
    headers.update({"Tenant-ID": TENANT_ID, "X-Tenant-ID": TENANT_ID})
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    try:
        response = requests.post(config["url"], headers=headers, json=payload)
        if response.status_code == 200:
            return sanitize_text(json_to_text(response.json()))
        else:
            st.error(f"❌ API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"❌ API Call Failed: {str(e)}")
        return None

def submit_feedback(feedback_type, name="", email="", off_definitions="", suggestions="", additional_feedback="", 
                   account="", industry="", problem_statement=""):
    """Submit feedback to CSV file and admin session storage"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Use provided account/industry or get from session state
    account = account or st.session_state.get("current_account", "") or st.session_state.get("saved_account", "")
    industry = industry or st.session_state.get("current_industry", "") or st.session_state.get("saved_industry", "")
    problem_statement = problem_statement or st.session_state.get("current_problem", "") or st.session_state.get("saved_problem", "")

    # Create feedback data for admin session
    feedback_data = {
        "Name": name,
        "Email": email, 
        "Feedback": additional_feedback,
        "FeedbackType": feedback_type,
        "OffDefinitions": off_definitions,
        "Suggestions": suggestions,
        "Account": account,
        "Industry": industry,
        "ProblemStatement": problem_statement
    }

    # Save to admin session storage
    save_feedback_to_admin_session(feedback_data, "Current System Agent")

    # Also save to CSV file (original functionality)
    new_entry = pd.DataFrame([[
        timestamp, name, email, additional_feedback, feedback_type, off_definitions, suggestions, account, industry, problem_statement
    ]], columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType", "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])

    try:
        # Try file-based storage first
        if os.path.exists(FEEDBACK_FILE):
            existing = pd.read_csv(FEEDBACK_FILE)

            # Handle schema mismatch
            missing_cols = set(new_entry.columns) - set(existing.columns)
            for col in missing_cols:
                existing[col] = ''

            # Reorder existing columns to match the new entry's order
            existing = existing[new_entry.columns]

            updated = pd.concat([existing, new_entry], ignore_index=True)
        else:
            updated = new_entry

        try:
            updated.to_csv(FEEDBACK_FILE, index=False)
        except (PermissionError, OSError):
            # Fallback to session state on Streamlit Cloud
            if 'feedback_data' not in st.session_state:
                st.session_state.feedback_data = pd.DataFrame(
                    columns=new_entry.columns)
            st.session_state.feedback_data = pd.concat(
                [st.session_state.feedback_data, new_entry], ignore_index=True)
            st.info("📝 Feedback saved to session (cloud mode)")

        # Set AGENT-SPECIFIC feedback flag
        st.session_state.current_system_feedback_submitted = True
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        return False

# =========================================
# 🧩 UI COMPONENTS
# =========================================

# Check for admin mode first
try:
    if hasattr(st, 'query_params'):
        admin_toggled = 'adminPanelToggled' in st.query_params
    else:
        query_params = st.experimental_get_query_params()
        admin_toggled = 'adminPanelToggled' in query_params
except:
    admin_toggled = False

# If admin mode detected or session state shows admin, render admin section
if admin_toggled or st.session_state.get('current_page', '') == 'admin':
    st.session_state.current_page = 'admin'
    render_admin_panel()
    st.stop()  # Stop rendering the rest of the page

render_header(
    agent_name="Current System Agent",
    agent_subtitle="Analyze your current system, inputs, outputs, and pain points",
    enable_admin_access=True,
    header_height=100
)

# --- Unified business inputs (from shared_header)
account, industry, problem = render_unified_business_inputs(
    page_key_prefix="current_system",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="✅ Save Problem Details"
)

st.markdown(
    "<hr style='border: 0; height: 1px; background: var(--divider-color, rgba(0,0,0,0.1)); margin: 1.5rem 0;'>",
    unsafe_allow_html=True
)

# =========================================
# 🚀 API CALL BUTTON
# =========================================
if not st.session_state.current_system_extracted:
    if st.button(
        "🔍 Extract Current System • ⏱️ 60-90s", 
        type="primary", 
        use_container_width=True,
        help="Please be patient as this process may take 60-90 seconds to complete"
    ):
        if not st.session_state.saved_problem.strip():
            st.error("⚠️ Please save your business problem details first!")
        else:
            with st.spinner("🔍 Extracting current system analysis..."):
                api_output = call_api(
                    agent_name="current_system",
                    problem=st.session_state.saved_problem,
                    context=f"{st.session_state.saved_account}, {st.session_state.saved_industry}"
                )
                if api_output:
                    st.session_state.current_system_data = api_output
                    st.session_state.current_system_extracted = True
                    st.success("✅ Current System extracted successfully!")
                    _safe_rerun()

# =========================================
# 📊 DISPLAY RESULTS
# =========================================
if st.session_state.current_system_extracted:
    # Updated header to match Vocabulary style
    st.markdown(
        f"""
        <div style="margin: 20px 0;">
            <div class="section-title-box" style="padding: 1rem 1.5rem;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="margin-bottom:8px; color:white; font-weight:800; font-size:1.4rem; line-height:1.2;">
                        Current System Analysis
                    </h3>
                    <p style="font-size:0.95rem; color:white; margin:0; line-height:1.5; text-align:center; max-width: 800px;">
                        Please note that this is an <strong>AI-generated Current System Analysis</strong>, derived from 
                        the problem statement you shared.<br>
                        In case you find something off, there's a provision to share feedback at the bottom 
                        we encourage you to use it.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    sections = parse_current_system_sections(st.session_state.current_system_data)

    # Clean and format each section to remove numbers and extra whitespace
    def clean_section_content(content):
        """Remove numbered lists (1., 2., 3., etc.) and clean up formatting"""
        if not content:
            return content
        
        # Remove numbered lists (1., 2., 3., etc.)
        cleaned = re.sub(r'^\s*\d+\.\s*', '', content, flags=re.MULTILINE)
        
        # Remove any remaining "Box X:" patterns
        cleaned = re.sub(r'(?i)\b(box\s*\d+[:.]?\s*)', '', cleaned)
        
        # Remove extra whitespace and normalize line breaks
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        
        return cleaned.strip()

    # Display Core Business Problem with red border
    core_problem_clean = clean_section_content(sections["core_problem"])
    st.markdown(
        f"""
        <div style="
            background: var(--bg-card);
            border: 2px solid #8b1e1e;
            border-radius: 16px;
            padding: 1.6rem;
            margin-bottom: 1.6rem;
            box-shadow: 0 3px 10px rgba(139,30,30,0.15);
        ">
            <h4 style="
                color: #8b1e1e;
                font-weight: 700;
                font-size: 1.15rem;
                margin: 0 0 1rem 0;
                border-bottom: 2px solid #8b1e1e;
                padding-bottom: 0.5rem;
                text-align: left;
            ">
                Core Business Problem
            </h4>
            <div style="
                color: var(--text-primary);
                line-height: 1.45;
                font-size: 1rem;
                text-align: left;
                white-space: normal;
            ">
                {core_problem_clean}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Display Current System with red border
    current_system_clean = clean_section_content(sections["current_system"])
    st.markdown(
        f"""
        <div style="
            background: var(--bg-card);
            border: 2px solid #8b1e1e;
            border-radius: 16px;
            padding: 1.6rem;
            margin-bottom: 1.6rem;
            box-shadow: 0 3px 10px rgba(139,30,30,0.15);
        ">
            <h4 style="
                color: #8b1e1e;
                font-weight: 700;
                font-size: 1.15rem;
                margin: 0 0 1rem 0;
                border-bottom: 2px solid #8b1e1e;
                padding-bottom: 0.5rem;
                text-align: left;
            ">
                Current System
            </h4>
            <div style="
                color: var(--text-primary);
                line-height: 1.45;
                font-size: 1rem;
                text-align: left;
                white-space: normal;
            ">
                {current_system_clean}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Display Inputs and Outputs side by side with red borders
    col1, col2 = st.columns(2)
    
    with col1:
        inputs_clean = clean_section_content(sections["inputs"])
        st.markdown(
            f"""
            <div style="
                background: var(--bg-card);
                border: 2px solid #8b1e1e;
                border-radius: 16px;
                padding: 1.6rem;
                margin-bottom: 1.6rem;
                box-shadow: 0 3px 10px rgba(139,30,30,0.15);
                height: 100%;
            ">
                <h4 style="
                    color: #8b1e1e;
                    font-weight: 700;
                    font-size: 1.15rem;
                    margin: 0 0 1rem 0;
                    border-bottom: 2px solid #8b1e1e;
                    padding-bottom: 0.5rem;
                    text-align: left;
                ">
                    Inputs
                </h4>
                <div style="
                    color: var(--text-primary);
                    line-height: 1.45;
                    font-size: 1rem;
                    text-align: left;
                    white-space: normal;
                ">
                    {inputs_clean}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        outputs_clean = clean_section_content(sections["outputs"])
        st.markdown(
            f"""
            <div style="
                background: var(--bg-card);
                border: 2px solid #8b1e1e;
                border-radius: 16px;
                padding: 1.6rem;
                margin-bottom: 1.6rem;
                box-shadow: 0 3px 10px rgba(139,30,30,0.15);
                height: 100%;
            ">
                <h4 style="
                    color: #8b1e1e;
                    font-weight: 700;
                    font-size: 1.15rem;
                    margin: 0 0 1rem 0;
                    border-bottom: 2px solid #8b1e1e;
                    padding-bottom: 0.5rem;
                    text-align: left;
                ">
                    Outputs
                </h4>
                <div style="
                    color: var(--text-primary);
                    line-height: 1.45;
                    font-size: 1rem;
                    text-align: left;
                    white-space: normal;
                ">
                    {outputs_clean}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Display Pain Points with red border
    pain_points_clean = clean_section_content(sections["pain_points"])
    st.markdown(
        f"""
        <div style="
            background: var(--bg-card);
            border: 2px solid #8b1e1e;
            border-radius: 16px;
            padding: 1.6rem;
            margin-bottom: 1.6rem;
            box-shadow: 0 3px 10px rgba(139,30,30,0.15);
        ">
            <h4 style="
                color: #8b1e1e;
                font-weight: 700;
                font-size: 1.15rem;
                margin: 0 0 1rem 0;
                border-bottom: 2px solid #8b1e1e;
                padding-bottom: 0.5rem;
                text-align: left;
            ">
                Pain Points
            </h4>
            <div style="
                color: var(--text-primary);
                line-height: 1.45;
                font-size: 1rem;
                text-align: left;
                white-space: normal;
            ">
                {pain_points_clean}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ===============================
# User Feedback Section (Only show after extraction)
# ===============================

if st.session_state.current_system_extracted:
    st.markdown("---")
    st.markdown('<div class="section-title-box" style="text-align:center;"><h3>💬 User Feedback</h3></div>',
                unsafe_allow_html=True)
    
    # UPDATED MESSAGE - Agent-specific
    st.markdown("Please share your thoughts or suggestions after reviewing the **current system analysis**.")

    # Get account and industry from session state
    current_account = st.session_state.get("current_account", "") or st.session_state.get("saved_account", "")
    current_industry = st.session_state.get("current_industry", "") or st.session_state.get("saved_industry", "")
    current_problem = st.session_state.get("current_problem", "") or st.session_state.get("saved_problem", "")

    # Dark mode compatible CSS
    st.markdown("""
        <style>
        /* Mu Sigma red button styling */
        .stButton>button {
            background-color: #8B1E1E !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            border-radius: 4px !important;
            font-weight: 600 !important;
        }
        .stButton>button:hover {
            background-color: #6B1515 !important;
            color: white !important;
        }
        
        /* Dark mode compatibility for form elements */
        .stTextInput input, .stTextArea textarea {
            background-color: transparent !important;
            color: inherit !important;
        }
        
        /* Checkbox labels */
        .stCheckbox label {
            color: inherit !important;
        }
        
        /* Radio button labels */  
        .stRadio label {
            color: inherit !important;
        }
        
        /* Form container */
        .stForm {
            background-color: transparent !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Show feedback section if not submitted - USING AGENT-SPECIFIC FLAG
    if not st.session_state.get('current_system_feedback_submitted', False):
        fb_choice = st.radio(
            "Select your feedback type:",
            options=[
                "I have read it, found it useful, thanks.",
                "I have read it, found some definitions to be off.",
                "The widget seems interesting, but I have some suggestions on the features.",
            ],
            index=None,
            key="current_system_feedback_radio",  # Agent-specific key
        )

        if fb_choice:
            st.session_state.current_system_feedback_option = fb_choice

        # Feedback form 1: Positive feedback
        if fb_choice == "I have read it, found it useful, thanks.":
            with st.form("current_system_feedback_form_positive", clear_on_submit=True):
                st.info(
                    "Thank you for your positive feedback! Optional: Share your name and email.")
                
                name = st.text_input("Your Name (optional)", key="current_system_positive_name")
                email = st.text_input("Your Email (optional)", key="current_system_positive_email")
                
                submitted = st.form_submit_button("📨 Submit Positive Feedback", type="primary")
                if submitted:
                    if submit_feedback(fb_choice, name=name, email=email, 
                                     account=current_account, industry=current_industry, 
                                     problem_statement=current_problem):
                        st.session_state.current_system_feedback_submitted = True
                        st.success("✅ Thank you! Your feedback has been recorded.")
                        st.rerun()

        # Feedback form 2: Definitions off
        elif fb_choice == "I have read it, found some definitions to be off.":
            with st.form("current_system_feedback_form_defs", clear_on_submit=True):
                st.markdown(
                    "**Please select which sections have definitions that seem off:**")
                
                name = st.text_input("Your Name *", key="current_system_defs_name")
                email = st.text_input("Your Email (optional)", key="current_system_defs_email")

                # Section selection with better styling
                st.markdown("### Select problematic sections:")
                st.markdown("<div style='margin-bottom: 1rem;'>Select all that apply:</div>", unsafe_allow_html=True)
                
                sections_list = [
                    "Core Business Problem",
                    "Current System Overview", 
                    "Key Technologies/Tools",
                    "Roles/Stakeholders",
                    "Inputs",
                    "Outputs", 
                    "Pain Points"
                ]
                
                selected_issues = {}
                for i, section in enumerate(sections_list):
                    # Use a unique key for each checkbox
                    selected = st.checkbox(
                        section,
                        key=f"current_system_def_section_{i}",
                        help=f"Select if {section} has definition issues"
                    )
                    if selected:
                        selected_issues[section] = True

                additional_feedback = st.text_area(
                    "Additional comments:",
                    placeholder="Please provide more details about the definition issues you found...",
                    key="current_system_defs_additional"
                )

                submitted = st.form_submit_button("📨 Submit Feedback", type="primary")
                if submitted:
                    if not name.strip():
                        st.warning("⚠️ Please provide your name.")
                    elif not selected_issues:
                        st.warning(
                            "⚠️ Please select at least one section that has definition issues.")
                    else:
                        issues_list = list(selected_issues.keys())
                        off_defs_text = " | ".join(issues_list)
                        if submit_feedback(fb_choice, name=name, email=email, off_definitions=off_defs_text, 
                                         additional_feedback=additional_feedback, account=current_account, 
                                         industry=current_industry, problem_statement=current_problem):
                            st.session_state.current_system_feedback_submitted = True
                            st.success("✅ Thank you! Your feedback has been recorded.")
                            st.rerun()

        # Feedback form 3: Suggestions
        elif fb_choice == "The widget seems interesting, but I have some suggestions on the features.":
            with st.form("current_system_feedback_form_suggestions", clear_on_submit=True):
                st.markdown(
                    "**Please share your suggestions for improvement:**")
                
                name = st.text_input("Your Name *", key="current_system_suggestions_name")
                email = st.text_input("Your Email (optional)", key="current_system_suggestions_email")
                suggestions = st.text_area(
                    "Your suggestions:",
                    placeholder="What features would you like to see improved or added?",
                    key="current_system_suggestions_text"
                )
                submitted = st.form_submit_button("📨 Submit Feedback", type="primary")
                if submitted:
                    if not name.strip():
                        st.warning("⚠️ Please provide your name.")
                    elif not suggestions.strip():
                        st.warning("⚠️ Please provide your suggestions.")
                    else:
                        if submit_feedback(fb_choice, name=name, email=email, suggestions=suggestions,
                                         account=current_account, industry=current_industry, 
                                         problem_statement=current_problem):
                            st.session_state.current_system_feedback_submitted = True
                            st.success("✅ Thank you! Your feedback has been recorded.")
                            st.rerun()
    else:
        # Feedback already submitted - USING AGENT-SPECIFIC FLAG
        st.success("✅ Thank you! Your feedback has been recorded.")
        if st.button("📝 Submit Additional Feedback", key="current_system_reopen_feedback_btn", type="primary"):
            st.session_state.current_system_feedback_submitted = False
            st.rerun()

    # ===============================
    # Download Section (Only show after feedback submission - AGENT-SPECIFIC)
    # ===============================

    # USING AGENT-SPECIFIC FLAG for download section
    if st.session_state.get('current_system_feedback_submitted', False):
        st.markdown("---")
        st.markdown(
            """
            <div style="margin: 10px 0;">
                <div class="section-title-box" style="padding: 0.5rem 1rem;">
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                        <h3 style="margin:0; color:white; font-weight:700; font-size:1.2rem; line-height:1.2;">
                            📥 Download Current System Analysis
                        </h3>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        current_system_text = st.session_state.get("current_system_data", "")
        if current_system_text and not current_system_text.startswith("API Error") and not current_system_text.startswith("Error:"):
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"current_system_{st.session_state.saved_account.replace(' ', '_')}_{ts}.txt"
            download_content = f"""Current System Analysis
    Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Company: {st.session_state.saved_account}
    Industry: {st.session_state.saved_industry}
    Problem: {st.session_state.saved_problem}

    {current_system_text}

    ---
    Generated by Current System Analysis Tool
    """
            st.download_button(
                "⬇️ Download Current System Analysis as Text File",
                data=download_content,
                file_name=filename,
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info(
                "No current system analysis available for download. Please complete the analysis first.")

# =========================================
# ⬅️ BACK BUTTON
# =========================================
st.markdown("---")
if st.button("⬅️ Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")
