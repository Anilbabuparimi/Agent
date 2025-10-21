import streamlit as st
import streamlit.components.v1 as components
import os
import re
import json
from shared_header import render_header
# REMOVE THIS: render_header() - Don't call it here, call it after imports
from datetime import datetime
import pandas as pd
import requests
from shared_header import (
    render_header,
    render_admin_panel,
    save_feedback_to_admin_session,  # ADD THIS
    ACCOUNTS,
    INDUSTRIES,
    ACCOUNT_INDUSTRY_MAP,
    get_shared_data,
    render_unified_business_inputs,
)

# --- Page Config ---
st.set_page_config(
    page_title="Vocabulary Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialize session state ---
if 'vocab_output' not in st.session_state:
    st.session_state.vocab_output = ""
if 'show_vocabulary' not in st.session_state:
    st.session_state.show_vocabulary = False
if 'feedback_submitted' not in st.session_state:
    st.session_state.feedback_submitted = False
if 'feedback_option' not in st.session_state:
    st.session_state.feedback_option = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'validation_attempted' not in st.session_state:
    st.session_state.validation_attempted = False

# --- Render Header ---
render_header(  # CALL IT HERE INSTEAD
    agent_name="Vocabulary Agent",
    agent_subtitle="Reviewing the business problem statement."
)

# --- Check for Admin Mode ---
# Check if admin panel should be shown via query params
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
# API Configuration
# ===============================

# Constants
TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}
VOCAB_API_URL = "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758548233201&level=1"

# API config with simplified prompt
API_CONFIGS = [
    {
        "name": "vocabulary",
        "url": VOCAB_API_URL,
        "multiround_convo": 3,
        "description": "vocabulary",
        "prompt": lambda problem, outputs: (
            f"{problem}\n\nExtract the vocabulary from this problem statement."
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

def format_vocabulary_with_bold(text, extra_phrases=None):
    """Format vocabulary text with bold styling"""
    if not text:
        return "No vocabulary data available"

    clean_text = sanitize_text(text)
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

        if re.search(r'(Step\s*\d+\s*:)', ln, flags=re.IGNORECASE):
            block, j = collect_continuation(i)
            block_text = "<br>".join([b.strip() for b in block])
            paragraph_html.append(f"<strong>{block_text}</strong>")
            i = j
            continue

        m_num_colon = re.match(r'^\s*(\d+\.\s+[^:]+):\s*(.*)$', ln)
        if m_num_colon:
            heading = m_num_colon.group(1).strip()
            remainder = m_num_colon.group(2).strip()
            paragraph_html.append(
                f"<strong>{heading}:</strong> {remainder}" if remainder else f"<strong>{heading}:</strong>")
            i += 1
            continue

        m_num_no_colon = re.match(r'^\s*(\d+\.\s+.+)$', ln)
        if m_num_no_colon:
            block, j = collect_continuation(i)
            block_text = "<br>".join([b.strip() for b in block])
            paragraph_html.append(f"<strong>{block_text}</strong>")
            i = j
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

        if re.fullmatch(r'\s*Revenue\s+Growth\s+Rate\s*', ln, flags=re.IGNORECASE):
            paragraph_html.append(f"<strong>{ln.strip()}</strong>")
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
    <div class="vocab-display">
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
    save_feedback_to_admin_session(feedback_data, "Vocabulary Agent")

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
    # Clear vocabulary-related state
    keys_to_clear = ['vocab_output', 'show_vocabulary', 'feedback_submitted',
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

# Use the unified inputs (Welcome-style) so Vocabulary page matches all others
account, industry, problem = render_unified_business_inputs(
    page_key_prefix="vocab",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="✅ Save Problem Details",
)

st.markdown("---")

# ===============================
# Vocabulary Extraction Section
# ===============================

# Validation checks (without warnings)
has_account = account and account != "Select Account"
has_industry = industry and industry != "Select Industry"
has_problem = bool(problem.strip())

# Extract Vocabulary Button
extract_btn = st.button("🔍 Extract Vocabulary", type="primary", use_container_width=True,
                        disabled=not (has_account and has_industry and has_problem))

if extract_btn:
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

    with st.spinner("🔍 Extracting vocabulary and analyzing context..."):
        progress = st.progress(0)

        try:
            with requests.Session() as session:
                cfg = API_CONFIGS[0]
                goal = cfg["prompt"](full_context, {})

                # Make API request with timeout
                response = session.post(
                    cfg["url"],
                    headers=headers,
                    json={"agency_goal": goal},
                    timeout=60
                )

                progress.progress(0.5)

                if response.status_code == 200:
                    # Process successful response
                    result_data = response.json()
                    text_output = json_to_text(result_data)
                    cleaned_text = sanitize_text(text_output)

                    st.session_state.vocab_output = cleaned_text
                    st.session_state.show_vocabulary = True
                    st.session_state.analysis_complete = True

                    progress.progress(1.0)
                    st.success("✅ Vocabulary extraction complete!")

                else:
                    error_msg = f"API Error {response.status_code}: {response.text[:200]}"
                    st.session_state.vocab_output = error_msg
                    st.session_state.show_vocabulary = True
                    st.error(
                        f"API request failed with status {response.status_code}")

        except requests.exceptions.Timeout:
            error_msg = "Request timeout: The API took too long to respond."
            st.session_state.vocab_output = error_msg
            st.session_state.show_vocabulary = True
            st.error("Request timeout - please try again.")

        except requests.exceptions.ConnectionError:
            error_msg = "Connection error: Unable to connect to the API server."
            st.session_state.vocab_output = error_msg
            st.session_state.show_vocabulary = True
            st.error("Connection error - please check your network connection.")

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            st.session_state.vocab_output = error_msg
            st.session_state.show_vocabulary = True
            st.error(f"An unexpected error occurred: {str(e)}")

# ===============================
# Display Vocabulary Results
# ===============================

if st.session_state.get("show_vocabulary") and st.session_state.get("vocab_output"):
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
                        Vocabulary
                    </h3>
                    <p style="font-size:0.95rem; color:white; margin:0; line-height:1.5; text-align:center; max-width: 800px;">
                        Please note that it is an <strong>AI-generated Vocabulary</strong>, derived from 
                        the <em>company</em> <strong>{display_account}</strong> and 
                        the <em>industry</em> <strong>{display_industry}</strong> based on the 
                        <em>problem statement</em> you shared.<br>
                        In case you find something off, there's a provision to share feedback at the bottom 
                        we encourage you to use it.
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Format and display vocabulary with account/industry substitutions
    vocab_text = st.session_state.vocab_output
    formatted_vocab = format_vocabulary_with_bold(vocab_text)

    # Replace generic mentions in the formatted HTML
    if display_account and display_account != "Unknown Company":
        formatted_vocab = re.sub(
            r'\bthe company\b', display_account, formatted_vocab, flags=re.IGNORECASE)
    if display_industry and display_industry != "Unknown Industry":
        formatted_vocab = re.sub(
            r'\bthe industry\b', display_industry, formatted_vocab, flags=re.IGNORECASE)

    # Convert newlines to <br> for proper HTML display
    html_body = formatted_vocab.replace('\n', '<br>')

        # Single box for vocabulary with proper spacing and visible border
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
                Key Terminology
            </h4>
            <div style="
                color: var(--text-primary);
                line-height: 1.3;
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
    "Please share your thoughts or suggestions after reviewing the vocabulary results.")

# Extract sections and terms from vocabulary output
def parse_vocabulary_sections(vocab_text):
    sections = {}
    current_section = None
    current_items = []
    
    if not vocab_text:
        return sections
    
    lines = vocab_text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Detect section headers (Section X: Title)
        section_match = re.match(r'^Section\s+(\d+):\s*(.+)$', line)
        if section_match:
            # Save previous section if exists
            if current_section:
                sections[current_section] = current_items.copy()
            
            # Start new section
            section_num = section_match.group(1)
            section_title = section_match.group(2).strip()
            current_section = f"Section {section_num}: {section_title}"
            current_items = []
            continue
        
        # Detect numbered items within sections (1. Term: Definition)
        item_match = re.match(r'^(\d+)\.\s+(.+?):\s*(.+)$', line)
        if item_match and current_section:
            item_number = item_match.group(1)
            item_term = item_match.group(2).strip()
            item_definition = item_match.group(3).strip()
            
            # Store both term and full text for display
            display_text = f"{item_number}. {item_term}"
            current_items.append({
                'display': display_text,
                'full_text': f"{item_number}. {item_term}: {item_definition}"
            })
    
    # Don't forget to add the last section
    if current_section and current_items:
        sections[current_section] = current_items.copy()
    
    return sections

# Get vocabulary text from session state
vocab_text = st.session_state.get("vocab_output", "")
sections_data = parse_vocabulary_sections(vocab_text)

# Show feedback section if not submitted
if not st.session_state.get('feedback_submitted', False):
    fb_choice = st.radio(
        "Select your feedback type:",
        options=[
            "I have read it, found it useful, thanks.",
            "I have read it, found some definitions to be off.",
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
                "Thank you for your positive feedback!")
            
            # Auto-extracted user info (from login)
            user_id = st.session_state.get('user_id', 'N/A')
            
            st.markdown("**User Information:**")
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("User ID", value=user_id, disabled=True, key="user_id_display")
            with col2:
                st.text_input("Account", value=display_account, disabled=True, key="account_display")
            
            col3, col4 = st.columns(2)
            with col3:
                st.text_input("Industry", value=display_industry, disabled=True, key="industry_display")
            
            submitted = st.form_submit_button("📨 Submit Positive Feedback")
            if submitted:
                if submit_feedback(fb_choice, user_id=user_id):
                    st.success(
                        "✅ Thank you! Your positive feedback has been recorded.")

    # Feedback form 2: Definitions off
    elif fb_choice == "I have read it, found some definitions to be off.":
        with st.form("feedback_form_defs", clear_on_submit=True):
            st.markdown(
                "**Please select which sections and terms have definitions that seem off:**")
            
            # Auto-extracted user info (from login)
            user_id = st.session_state.get('user_id', 'N/A')
            
            st.markdown("**User Information:**")
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("User ID", value=user_id, disabled=True, key="user_id_defs")
            with col2:
                st.text_input("Account", value=display_account, disabled=True, key="account_defs")
            
            col3, col4 = st.columns(2)
            with col3:
                st.text_input("Industry", value=display_industry, disabled=True, key="industry_defs")

            selected_issues = {}
            
            # Create dropdowns for each section
            if sections_data:
                for section_name, items in sections_data.items():
                    if items:  # Only show sections that have items
                        st.markdown(f"### {section_name}")
                        
                        # Extract just the display text for multiselect options
                        options = [item['display'] for item in items]
                        
                        selected_items = st.multiselect(
                            f"Select problematic terms in {section_name}:",
                            options=options,
                            key=f"multiselect_{section_name}",
                            help=f"Select terms from {section_name} that have definition issues"
                        )
                        
                        if selected_items:
                            selected_issues[section_name] = selected_items
            else:
                # Fallback if no sections parsed
                st.warning("No vocabulary sections found to provide feedback on.")
                fallback_sections = {
                    "Section 1: Extract and Define Business Vocabulary Terms": [
                        "1. Managed Pros", "2. Account Support", "3. Growth Strategies", 
                        "4. Tailored Strategies", "5. Upselling", "6. Revenue Growth",
                        "7. Lifetime Value (LTV)", "8. Missed Opportunities", "9. Suboptimal"
                    ],
                    "Section 2: Identify KPIs and Metrics": [
                        "1. Customer Lifetime Value (LTV)", "2. Revenue Growth Rate", 
                        "3. Upsell Rate", "4. Customer Satisfaction Score (CSAT)"
                    ],
                    "Section 3: Identify Relevant Business Processes": [
                        "1. Account Management Process", "2. Sales Strategy Development", 
                        "3. Customer Feedback Loop"
                    ]
                }
                
                for section_name, options in fallback_sections.items():
                    st.markdown(f"### {section_name}")
                    selected_items = st.multiselect(
                        f"Select problematic terms in {section_name}:",
                        options=options,
                        key=f"fallback_{section_name}",
                        help=f"Select terms from {section_name} that have definition issues"
                    )
                    if selected_items:
                        selected_issues[section_name] = selected_items

            additional_feedback = st.text_area(
                "Additional comments:",
                placeholder="Please provide more details about the definition issues you found..."
            )

            submitted = st.form_submit_button("📨 Submit Feedback")
            if submitted:
                if not selected_issues:
                    st.warning(
                        "⚠️ Please select at least one term that has definition issues.")
                else:
                    # Format issues for submission
                    issues_list = []
                    for section, items in selected_issues.items():
                        for item in items:
                            issues_list.append(f"{section} - {item}")
                    
                    off_defs_text = " | ".join(issues_list)
                    if submit_feedback(fb_choice, user_id=user_id, off_definitions=off_defs_text, additional_feedback=additional_feedback):
                        st.success(
                            "✅ Thank you! Your feedback has been submitted.")

    # Feedback form 3: Suggestions
    elif fb_choice == "The widget seems interesting, but I have some suggestions on the features.":
        with st.form("feedback_form_suggestions", clear_on_submit=True):
            st.markdown(
                "**Please share your suggestions for improvement:**")
            
            # Auto-extracted user info (from login)
            user_id = st.session_state.get('user_id', 'N/A')
            
            st.markdown("**User Information:**")
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("User ID", value=user_id, disabled=True, key="user_id_suggestions")
            with col2:
                st.text_input("Account", value=display_account, disabled=True, key="account_suggestions")
            
            col3, col4 = st.columns(2)
            with col3:
                st.text_input("Industry", value=display_industry, disabled=True, key="industry_suggestions")
            
            suggestions = st.text_area(
                "Your suggestions:",
                placeholder="What features would you like to see improved or added?"
            )
            submitted = st.form_submit_button("📨 Submit Feedback")
            if submitted:
                if not suggestions.strip():
                    st.warning("⚠️ Please provide your suggestions.")
                else:
                    if submit_feedback(fb_choice, user_id=user_id, suggestions=suggestions):
                        st.success(
                            "✅ Thank you! Your feedback has been submitted.")
else:
    # Feedback already submitted
    st.success("✅ Thank you! Your feedback has been recorded.")
    if st.button("📝 Submit Additional Feedback", key="reopen_feedback_btn"):
        st.session_state.feedback_submitted = False
        st.rerun()

# Add custom CSS for dark mode styling
st.markdown("""
<style>
    /* Dark mode styling for disabled inputs */
    .stTextInput [data-baseweb="input"]:disabled {
        background-color: #2b2b2b !important;
        color: #ffffff !important;
        border-color: #555555 !important;
    }
    
    /* Multiselect dark mode improvements */
    .stMultiSelect [data-baseweb="select"] {
        background-color: #262730;
    }
    
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #4a4a4a;
        color: white;
    }
</style>
""", unsafe_allow_html=True)
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
                        📥 Download Vocabulary
                    </h3>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vocab_text = st.session_state.get("vocab_output", "")
    if vocab_text and not vocab_text.startswith("API Error") and not vocab_text.startswith("Error:"):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"vocabulary_{display_account.replace(' ', '_')}_{ts}.txt"
        download_content = f"""Vocabulary Export
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Company: {display_account}
Industry: {display_industry}

{vocab_text}

---
Generated by Vocabulary Analysis Tool
"""
        st.download_button(
            "⬇️ Download Vocabulary as Text File",
            data=download_content,
            file_name=filename,
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.info(
            "No vocabulary available for download. Please complete the analysis first.")
# =========================================
# ⬅️ BACK BUTTON
# =========================================
st.markdown("---")
if st.button("⬅️ Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")

