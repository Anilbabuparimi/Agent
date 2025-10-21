import streamlit as st
import streamlit.components.v1 as components
import os
import re
import json
from datetime import datetime
import pandas as pd
import requests
from shared_header import (
    render_header,
    render_admin_panel,
    save_feedback_to_admin_session,
    ACCOUNTS,
    INDUSTRIES,
    ACCOUNT_INDUSTRY_MAP,
    get_shared_data,
    render_unified_business_inputs,
)

# --- Page Config ---
st.set_page_config(
    page_title="Volatility Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialize session state ---
if 'volatile_outputs' not in st.session_state:
    st.session_state.volatile_outputs = {}
if 'show_volatility' not in st.session_state:
    st.session_state.show_volatility = False
if 'feedback_submitted' not in st.session_state:
    st.session_state.feedback_submitted = False
if 'feedback_option' not in st.session_state:
    st.session_state.feedback_option = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'validation_attempted' not in st.session_state:
    st.session_state.validation_attempted = False

# --- Render Header ---
render_header(
    agent_name="Volatility Agent",
    agent_subtitle="Analyzing volatility and variability factors in your business problem."
)

# --- Check for Admin Mode ---
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

# ===============================
# API Configuration for Volatility
# ===============================

# Constants
TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}

# Volatility APIs (replace with your actual API URLs)
API_CONFIGS = [
    {
        "name": "Q1",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758555344231&level=1",
        "multiround_convo": 2,
        "description": "What is the frequency and pace of change in the key inputs driving the business?",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\n"
            "What is the frequency and pace of change in the key inputs driving the business? "
            "Provide detailed analysis, score 0–5, and justification."
        )
    },
    {
        "name": "Q2", 
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758549615986&level=1",
        "multiround_convo": 2,
        "description": "To what extent are these changes cyclical and predictable versus sporadic and unpredictable?",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\n"
            "To what extent are these changes cyclical and predictable versus sporadic and unpredictable? "
            "Provide detailed analysis, score 0–5, and justification."
        )
    },
    {
        "name": "Q3",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758614550482&level=1",
        "multiround_convo": 2,
        "description": "How resilient is the current system in absorbing these changes without requiring significant rework or disruption?",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\n"
            "How resilient is the current system in absorbing these changes without requiring significant rework or disruption? "
            "Provide detailed analysis, score 0–5, and justification."
        )
    }
]

# Global feedback file path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

# Initialize feedback file if not present
try:
    if not os.path.exists(FEEDBACK_FILE):
        df = pd.DataFrame(columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType",
                          "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])
        df.to_csv(FEEDBACK_FILE, index=False)
except (PermissionError, OSError) as e:
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = pd.DataFrame(
            columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType", "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])

# Token initialization
def _init_auth_token():
    token = os.environ.get("AUTH_TOKEN", "")
    try:
        if not token:
            token = st.secrets.get("AUTH_TOKEN", "")
    except Exception:
        pass
    return token or ""

if 'auth_token' not in st.session_state:
    st.session_state.auth_token = _init_auth_token()

# ===============================
# Utility Functions
# ===============================

def json_to_text(data):
    """Extract text from JSON response"""
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("result", "output", "content", "text", "answer", "response"):
            if key in data and data[key]:
                return json_to_text(data[key])
        if "data" in data:
            return json_to_text(data["data"])
        # Try to extract any string values
        for value in data.values():
            if isinstance(value, str) and len(value) > 10:
                return value
        return "\n".join(f"{k}: {json_to_text(v)}" for k, v in data.items() if v)
    if isinstance(data, list):
        return "\n".join(json_to_text(x) for x in data if x)
    return str(data)

def sanitize_text(text):
    """Remove markdown artifacts and clean up text"""
    if not text:
        return ""

    # Fix the "s" character issue
    text = re.sub(r'^\s*s\s+', '', text.strip())
    text = re.sub(r'\n\s*s\s+', '\n', text)

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
    text = re.sub(r'& Key Takeaway:', 'Key Takeaway:', text)

    return text.strip()

def format_volatility_with_bold(text, extra_phrases=None):
    """Format volatility text with bold styling and remove Q1/Answer labels"""
    if not text:
        return "No volatility data available"

    clean_text = sanitize_text(text)
    
    # Remove Q1/Answer labels and prefixes
    clean_text = re.sub(r'^\s*Q\d+\s*:', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
    clean_text = re.sub(r'^\s*Answer\s*:', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
    clean_text = re.sub(r'^\s*Question\s*\d+\s*:', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
    clean_text = re.sub(r'\bQ\d+\b\s*:', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\bAnswer\b\s*:', '', clean_text, flags=re.IGNORECASE)
    
    clean_text = clean_text.replace(" - ", " : ")
    clean_text = re.sub(r'(?m)^\s*[-*]\s+', '• ', clean_text)

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

        # Skip any lines that are just Q1/Answer labels
        if re.match(r'^\s*(Q\d+|Answer|Question\s*\d+)\s*$', ln, re.IGNORECASE):
            i += 1
            continue

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

        # Section headers (but not Q1/Answer)
        if re.match(r'^\s*(Analysis|Score|Justification|Key\s+Takeaway|Frequency|Pace|Change|Cyclical|Predictable|Sporadic|Unpredictable|Resilient|System|Rework|Disruption)', ln, flags=re.IGNORECASE):
            paragraph_html.append(f"<strong>{ln.strip()}</strong>")
            i += 1
            continue

        m_num_colon = re.match(r'^\s*(\d+\.\s+[^:]+):\s*(.*)$', ln)
        if m_num_colon:
            heading = m_num_colon.group(1).strip()
            remainder = m_num_colon.group(2).strip()
            paragraph_html.append(
                f"<strong>{heading}:</strong> {remainder}" if remainder else f"<strong>{heading}:</strong>")
            i += 1
            continue

        m_bullet_heading = re.match(r'^\s*(?:•|\d+\.)\s*([^:]+):\s*(.*)$', ln)
        if m_bullet_heading:
            heading = m_bullet_heading.group(1).strip()
            remainder = m_bullet_heading.group(2).strip()
            paragraph_html.append(
                f"• <strong>{heading}:</strong> {remainder}" if remainder else f"• <strong>{heading}:</strong>")
            i += 1
            continue

        m_side = re.match(r'^\s*([^:]+):\s*(.*)$', ln)
        if m_side and len(m_side.group(1).split()) <= 8:
            left = m_side.group(1).strip()
            right = m_side.group(2).strip()
            paragraph_html.append(
                f"<strong>{left}:</strong> {right}" if right else f"<strong>{left}:</strong>")
            i += 1
            continue

        paragraph_html.append(ln)
        i += 1

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
        f"<p style='margin:6px 0; line-height:1.45; font-size:0.98rem;'>{p}</p>" for p in final_paragraphs
    ]
    final_html = "\n".join(para_wrapped)

    formatted_output = f"""
    <div class="volatility-display">
        {final_html}
    </div>
    """
    formatted_output = re.sub(r'(<br>\s*){3,}', '<br><br>', formatted_output)
    return formatted_output

def submit_feedback(feedback_type, name="", email="", off_definitions="", suggestions="", additional_feedback=""):
    """Submit feedback to CSV file and admin session storage"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get context data from session state
    account = st.session_state.get("current_account", "")
    industry = st.session_state.get("current_industry", "")
    problem_statement = st.session_state.get("current_problem", "")

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
    save_feedback_to_admin_session(feedback_data, "Volatility Agent")

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

        st.session_state.feedback_submitted = True
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        return False

def reset_app_state():
    """Completely reset session state to initial values"""
    # Clear volatility-related state
    keys_to_clear = ['volatile_outputs', 'show_volatility', 'feedback_submitted',
                     'feedback_option', 'analysis_complete', 'validation_attempted']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    st.success("✅ Application reset successfully! You can start a new analysis.")

# ===============================
# Main Content
# ===============================

# Retrieve data from shared header
shared = get_shared_data()
account = shared.get("account") or ""
industry = shared.get("industry") or ""
problem = shared.get("problem") or ""

# Store current context in session state
st.session_state.current_account = account
st.session_state.current_industry = industry
st.session_state.current_problem = problem

# Normalize display values
def _norm_display(val, fallback):
    if not val or val in ("Select Account", "Select Industry", "Select Problem"):
        return fallback
    return val

display_account = _norm_display(account, "Unknown Company")
display_industry = _norm_display(industry, "Unknown Industry")

# Use the unified inputs (Welcome-style) so Volatility page matches all others
account, industry, problem = render_unified_business_inputs(
    page_key_prefix="volatility",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="✅ Save Problem Details",
)

st.markdown("---")

# ===============================
# Volatility Analysis Section
# ===============================

# Validation checks (without warnings)
has_account = account and account != "Select Account"
has_industry = industry and industry != "Select Industry"
has_problem = bool(problem.strip())

# Analyze Volatility Button
analyze_btn = st.button("🔍 Analyze Volatility", type="primary", use_container_width=True,
                        disabled=not (has_account and has_industry and has_problem))

if analyze_btn:
    # Set validation attempted flag
    st.session_state.validation_attempted = True

    # Final validation before processing
    if not has_account:
        st.error("❌ Please select an account before proceeding.")
        st.stop()

    if not has_industry:
        st.error("❌ Please select an industry before proceeding.")
        st.stop()

    if not has_problem:
        st.error("❌ Please enter a business problem description.")
        st.stop()

    # Build context
    full_context = f"""
    Business Problem:
    {problem.strip()}

    Context:
    Account: {account}
    Industry: {industry}
    """.strip()

    # Prepare headers with authentication
    headers = HEADERS_BASE.copy()
    headers.update({
        "Tenant-ID": TENANT_ID,
        "X-Tenant-ID": TENANT_ID
    })

    if st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

    with st.spinner("🔍 Analyzing volatility and variability factors..."):
        progress = st.progress(0)
        st.session_state.volatile_outputs = {}

        try:
            with requests.Session() as session:
                total_apis = len(API_CONFIGS)
                
                for i, api_cfg in enumerate(API_CONFIGS):
                    progress.progress(i / total_apis)
                    
                    try:
                        goal = api_cfg["prompt"](full_context, {})
                        
                        # Make API request with timeout
                        response = session.post(
                            api_cfg["url"],
                            headers=headers,
                            json={"agency_goal": goal},
                            timeout=60
                        )

                        if response.status_code == 200:
                            # Process successful response
                            result_data = response.json()
                            text_output = json_to_text(result_data)
                            cleaned_text = sanitize_text(text_output)
                            
                            st.session_state.volatile_outputs[api_cfg["name"]] = cleaned_text
                        else:
                            error_msg = f"API Error {response.status_code}: {response.text[:200]}"
                            st.session_state.volatile_outputs[api_cfg["name"]] = error_msg

                    except requests.exceptions.Timeout:
                        st.session_state.volatile_outputs[api_cfg["name"]] = "Request timeout: The API took too long to respond."
                    except Exception as e:
                        st.session_state.volatile_outputs[api_cfg["name"]] = f"Error: {str(e)}"

                progress.progress(1.0)
                st.session_state.show_volatility = True
                st.session_state.analysis_complete = True
                st.success("✅ Volatility analysis complete!")

        except Exception as e:
            st.error(f"An unexpected error occurred during analysis: {str(e)}")

# ===============================
# Display Volatility Results (Final Polished and Fixed)
# ===============================

def clean_volatility_output(text):
    """Clean volatility output by removing Q1/Q2/Q3 prefixes, HTML tags, and fixing formatting"""
    if not text:
        return "No volatility data available"

    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'^(Q\d+\.?\s*)', '', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'\n(Q\d+\.?\s*)', '\n', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'^(Question\s*\d+\.?\s*)', '', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'\n(Question\s*\d+\.?\s*)', '\n', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'^(Answer|Analysis)\s*:\s*', '', clean_text, flags=re.MULTILINE | re.IGNORECASE)
    clean_text = re.sub(r'Score\s*\(0[-–]5\)\s*:', 'Score:', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'^\s+', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'\n\s+', '\n', clean_text)
    clean_text = re.sub(r' {2,}', ' ', clean_text)
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    return clean_text.strip()


if st.session_state.get("show_volatility") and st.session_state.get("volatile_outputs"):
    st.markdown("---")

    display_account = globals().get("display_account") or st.session_state.get("saved_account", "Unknown Company")
    display_industry = globals().get("display_industry") or st.session_state.get("saved_industry", "Unknown Industry")

    # Section header
    st.markdown(
        f"""
        <div style="margin: 20px 0;">
            <div class="section-title-box" style="padding: 1rem 1.5rem;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="margin-bottom:8px; color:white; font-weight:800; font-size:1.4rem; line-height:1.2;">
                        Volatility Analysis
                    </h3>
                    <p style="font-size:0.95rem; color:white; margin:0; line-height:1.5; text-align:center; max-width: 800px;">
                        This is an <strong>AI-generated Volatility Analysis</strong> for 
                        <strong>{display_account}</strong> in the <strong>{display_industry}</strong> industry, 
                        based on your problem statement.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Loop through volatility results
    for i, (api_name, api_output) in enumerate(st.session_state["volatile_outputs"].items()):
        question_description = ""
        for cfg in API_CONFIGS:
            if cfg.get("name") == api_name:
                question_description = cfg.get("description", "")
                break

        clean_question = re.sub(r'^Q\d+\.?\s*', '', question_description or "").strip() or api_name.replace("_", " ").title()
        cleaned_output = clean_volatility_output(api_output)

        # Replace company/industry names
        if display_account and display_account != "Unknown Company":
            cleaned_output = re.sub(r'\bthe company\b', display_account, cleaned_output, flags=re.IGNORECASE)
        if display_industry and display_industry != "Unknown Industry":
            cleaned_output = re.sub(r'\bthe industry\b', display_industry, cleaned_output, flags=re.IGNORECASE)

        # --- FIXED DISPLAY WITH PROPER LIST FORMATTING + BOLD LABELS + LEFT ALIGNMENT ---
        formatted_output = cleaned_output

        # Convert numbered and dash lists to bullets
        formatted_output = re.sub(r'(?m)^\s*(?:\d+\.|-)\s+(.*)', r'• \1', formatted_output)

        # Ensure bullets always start on a new line (even if inline after colon)
        formatted_output = re.sub(r':\s*•', ':\n•', formatted_output)

        # Handle sentences ending with ":" followed by bullet text
        formatted_output = re.sub(r'(:)\s+(?=•)', r'\1\n', formatted_output)

        # Add newline before bullets (to separate from paragraphs)
        formatted_output = re.sub(r'(?<!\n)\s*•', r'\n•', formatted_output)

        # Bold text before colon, including bullets
        formatted_output = re.sub(
            r'(^|[\n])\s*(•\s*)?([^:\n]{2,80}):',
            lambda m: f"{m.group(1)}{m.group(2) or ''}<strong>{m.group(3).strip()}:</strong>",
            formatted_output
        )

        # Remove extra blank lines
        formatted_output = re.sub(r'\n{2,}', '\n', formatted_output)

        # Convert newlines to <br>
        html_body = formatted_output.replace('\n', '<br>')

        # Render clean formatted HTML block
        st.markdown(
            f"""
            <div style="
                background: var(--bg-card);
                border: 2px solid rgba(139,30,30,0.15);
                border-radius: 16px;
                padding: 1.6rem;
                margin-bottom: 1.6rem;
                box-shadow: 0 3px 10px rgba(0,0,0,0.08);
            ">
                <h4 style="
                    color: var(--musigma-red);
                    font-weight: 700;
                    font-size: 1.15rem;
                    margin: 0 0 1rem 0;
                    border-bottom: 1px solid rgba(139,30,30,0.15);
                    padding-bottom: 0.5rem;
                    text-align: left;
                ">
                    {clean_question}
                </h4>
                <div style="
                    color: var(--text-primary);
                    line-height: 1.45;
                    font-size: 1rem;
                    text-align: left;
                    white-space: normal;
                ">
                    {html_body}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )



    # ===============================
    # User Feedback Section
    # ===============================

    st.markdown("---")
    st.markdown('<div class="section-title-box" style="text-align:center;"><h3>💬 User Feedback</h3></div>',
                unsafe_allow_html=True)
    st.markdown(
        "Please share your thoughts or suggestions after reviewing the volatility analysis.")

    # Show feedback section if not submitted
    if not st.session_state.get('feedback_submitted', False):
        fb_choice = st.radio(
            "Select your feedback type:",
            options=[
                "I have read it, found it useful, thanks.",
                "I have read it, found some analyses to be off.",
                "The widget seems interesting, but I have some suggestions on the features.",
            ],
            index=None,
            key="feedback_radio",
        )

        if fb_choice:
            st.session_state.feedback_option = fb_choice

        # Feedback form 1: Positive feedback
        if fb_choice == "I have read it, found it useful, thanks.":
            with st.form("feedback_form_positive", clear_on_submit=True):
                st.info(
                    "Thank you for your positive feedback! Optional: Share your name and email.")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input(
                        "Account", value=display_account, disabled=True)
                with col2:
                    st.text_input(
                        "Industry", value=display_industry, disabled=True)
                name = st.text_input("Your Name (optional)")
                email = st.text_input("Your Email (optional)")
                submitted = st.form_submit_button("📨 Submit Positive Feedback")
                if submitted:
                    if submit_feedback(fb_choice, name=name, email=email):
                        st.success(
                            "✅ Thank you! Your positive feedback has been recorded.")

        # Feedback form 2: Analyses off
        elif fb_choice == "I have read it, found some analyses to be off.":
            with st.form("feedback_form_analyses", clear_on_submit=True):
                st.markdown(
                    "**Please select which volatility analyses seem off:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input(
                        "Account", value=display_account, disabled=True)
                with col2:
                    st.text_input(
                        "Industry", value=display_industry, disabled=True)
                name = st.text_input("Your Name")
                email = st.text_input("Your Email (optional)")

                # Show checkboxes for each volatility question
                st.markdown("### Select problematic analyses:")
                selected_issues = {}
                
                for api_name in st.session_state.volatile_outputs.keys():
                    selected = st.checkbox(
                        f"**{api_name}** - {API_CONFIGS[next(i for i, cfg in enumerate(API_CONFIGS) if cfg['name'] == api_name)]['description']}",
                        key=f"volatile_issue_{api_name}",
                        help=f"Select if {api_name} analysis seems incorrect"
                    )
                    if selected:
                        selected_issues[api_name] = True

                additional_feedback = st.text_area(
                    "Additional comments:",
                    placeholder="Please provide more details about the analysis issues you found..."
                )

                submitted = st.form_submit_button("📨 Submit Feedback")
                if submitted:
                    if not selected_issues:
                        st.warning(
                            "⚠️ Please select at least one analysis that seems off.")
                    else:
                        issues_list = list(selected_issues.keys())
                        off_defs_text = " | ".join(issues_list)
                        if submit_feedback(fb_choice, name=name, email=email, off_definitions=off_defs_text, additional_feedback=additional_feedback):
                            st.success(
                                "✅ Thank you! Your feedback has been submitted.")

        # Feedback form 3: Suggestions
        elif fb_choice == "The widget seems interesting, but I have some suggestions on the features.":
            with st.form("feedback_form_suggestions", clear_on_submit=True):
                st.markdown(
                    "**Please share your suggestions for improvement:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input(
                        "Account", value=display_account, disabled=True)
                with col2:
                    st.text_input(
                        "Industry", value=display_industry, disabled=True)
                name = st.text_input("Your Name")
                email = st.text_input("Your Email (optional)")
                suggestions = st.text_area(
                    "Your suggestions:",
                    placeholder="What features would you like to see improved or added?"
                )
                submitted = st.form_submit_button("📨 Submit Feedback")
                if submitted:
                    if not suggestions.strip():
                        st.warning("⚠️ Please provide your suggestions.")
                    else:
                        if submit_feedback(fb_choice, name=name, email=email, suggestions=suggestions):
                            st.success(
                                "✅ Thank you! Your feedback has been submitted.")
    else:
        # Feedback already submitted
        st.success("✅ Thank you! Your feedback has been recorded.")
        if st.button("📝 Submit Additional Feedback", key="reopen_feedback_btn"):
            st.session_state.feedback_submitted = False
            st.rerun()

# ===============================
# Download Section - Only show if feedback submitted
# ===============================

if st.session_state.get('feedback_submitted', False):
    st.markdown("---")
    st.markdown(
        """
        <div style="margin: 10px 0;">
            <div class="section-title-box" style="padding: 0.5rem 1rem;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="margin:0; color:white; font-weight:700; font-size:1.2rem; line-height:1.2;">
                        📥 Download Volatility Analysis
                    </h3>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Combine all volatility outputs for download
    combined_output = ""
    for api_name, api_output in st.session_state.volatile_outputs.items():
        if api_output and not api_output.startswith("API Error") and not api_output.startswith("Error:"):
            combined_output += f"=== {api_name} ===\n{api_output}\n\n"

    if combined_output:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"volatility_analysis_{display_account.replace(' ', '_')}_{ts}.txt"
        download_content = f"""Volatility Analysis Export
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {display_account}
Industry: {display_industry}

{combined_output}
---
Generated by Volatility Analysis Tool
"""
        st.download_button(
            "⬇️ Download Volatility Analysis as Text File",
            data=download_content,
            file_name=filename,
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.info(
            "No volatility analysis available for download. Please complete the analysis first.")

# =========================================
# ⬅️ BACK BUTTON
# =========================================
st.markdown("---")
if st.button("⬅️ Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")