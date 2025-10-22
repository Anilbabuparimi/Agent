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
    initialize_scoring_system,
    all_agents_completed,
    get_overall_hardness_score,
    get_agent_progress,
    get_all_question_scores,
    DIMENSION_QUESTIONS
)

# --- Page Config ---
st.set_page_config(
    page_title="Hardness Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialize session state ---
if 'hardness_outputs' not in st.session_state:
    st.session_state.hardness_outputs = {}
if 'show_hardness' not in st.session_state:
    st.session_state.show_hardness = False
if 'hardness_feedback_submitted' not in st.session_state:  # AGENT-SPECIFIC
    st.session_state.hardness_feedback_submitted = False
if 'feedback_option' not in st.session_state:
    st.session_state.feedback_option = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'validation_attempted' not in st.session_state:
    st.session_state.validation_attempted = False

# Initialize scoring system
initialize_scoring_system()

# --- Render Header ---
render_header(
    agent_name="Hardness Agent",
    agent_subtitle="Comprehensive problem difficulty assessment and hardness classification."
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
# API Configuration for Hardness
# ===============================

# Constants
TENANT_ID = "talos"
HEADERS_BASE = {"Content-Type": "application/json"}

# Hardness API
API_CONFIGS = [
    {
        "name": "hardness_summary",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758619658634&level=1",
        "multiround_convo": 2,
        "description": "Hardness Level, Summary & Key Takeaways",
        "prompt": lambda problem, outputs: (
            f"Problem statement - {problem}\n\n"
            "Based on the comprehensive analysis of the business problem, provide a hardness assessment with the following sections IN THIS EXACT FORMAT:\n\n"
            
            "Overall Difficulty Score\n"
            "[Provide a single numerical score between 0-5 based on your assessment of the problem complexity]\n\n"
            "Hardness Level\n"
            "[Easy: 0-3.0, Moderate: 3.1-4.0, or Hard: 4.1-5.0]\n\n"
            "SME Justification\n"
            "[Provide detailed justification analyzing the problem across multiple dimensions - complexity, ambiguity, interconnectedness, and uncertainty]\n\n"
            "Summary\n"
            "[Provide a concise summary of the overall assessment in 2-3 sentences]\n\n"
            "Key Takeaways\n"
            "[Provide 3-5 bullet points with actionable insights]\n\n"
            "IMPORTANT: Make sure each section is clearly labeled with its header as shown above. Provide actual scores and analysis, not placeholders."
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

def extract_hardness_score(text):
    """Extract the hardness score from the API response"""
    if not text:
        return None
    
    # Look for score patterns in the Overall Difficulty Score section
    score_patterns = [
        r'Overall Difficulty Score\s*[:\-]?\s*(\d+\.?\d*)',
        r'Score\s*[:\-]?\s*(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*\/\s*5',
        r'(\d+\.?\d*)\s*out of\s*5',
        r'Hardness Level.*?(\d+\.?\d*)',
    ]
    
    for pattern in score_patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            try:
                score = float(matches.group(1))
                if 0 <= score <= 5:
                    return score
            except ValueError:
                continue
    
    # If no specific score found, look for any number between 0-5
    numbers = re.findall(r'\b(\d+\.?\d*)\b', text)
    for num in numbers:
        try:
            score = float(num)
            if 0 <= score <= 5:
                return score
        except ValueError:
            continue
    
    return None

def extract_hardness_classification(text):
    """Extract hardness classification from text"""
    if not text:
        return "UNKNOWN"
    
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['hard', 'difficult', 'complex', 'challenging', '4.1', '4.2', '4.3', '4.4', '4.5', '4.6', '4.7', '4.8', '4.9', '5.0']):
        return "HARD"
    elif any(word in text_lower for word in ['moderate', 'medium', 'average', '3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '4.0']):
        return "MODERATE"
    elif any(word in text_lower for word in ['easy', 'simple', 'straightforward', '0.', '1.', '2.', '3.0']):
        return "NOT HARD"
    else:
        # Fallback: use score if available
        score = extract_hardness_score(text)
        if score is not None:
            if score >= 4.0:
                return "HARD"
            else:
                return "NOT HARD"
        return "UNKNOWN"

def format_hardness_output(text):
    """Format hardness output by removing everything before SME Justification and cleaning up"""
    if not text:
        return "No hardness data available"

    # Remove everything before "SME Justification"
    clean_text = re.sub(r'^.*?(?=SME Justification)', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # If SME Justification wasn't found, use the original text
    if not clean_text.strip():
        clean_text = text
    
    # Remove calculation sections that might still be present
    clean_text = re.sub(r'Calculation:.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'Score Calculation:.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'Calculation Process:.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'How.*?calculated:.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove mathematical expressions
    clean_text = re.sub(r'\(\s*\d+\.?\d*\s*[+-]\s*\d+\.?\d*\s*[+-]\s*\d+\.?\d*\s*[+-]\s*\d+\.?\d*\s*\)\s*\/\s*4', '', clean_text)
    clean_text = re.sub(r'\d+\.?\d*\s*[+-]\s*\d+\.?\d*\s*[+-]\s*\d+\.?\d*\s*[+-]\s*\d+\.?\d*\s*=\s*\d+\.?\d*', '', clean_text)
    
    # Remove dimension scores and individual question scores if they appear after SME Justification
    clean_text = re.sub(r'Individual Question Scores.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'Dimension Averages.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'DIMENSION SCORES:.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'OVERALL CLASSIFICATION:.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'COMPREHENSIVE ASSESSMENT:.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'HARDNESS SUMMARY.*?(?=\n\n|\n[A-Z]|$)', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    
    # Clean up remaining text
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    clean_text = re.sub(r'^\s+', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'\n\s+', '\n', clean_text)
    clean_text = re.sub(r' {2,}', ' ', clean_text)
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    
    return clean_text.strip()

def submit_feedback_wrapper(feedback_type, user_id="", off_definitions="", suggestions="", additional_feedback=""):
    """Wrapper for submit_feedback to handle the parameter mismatch"""
    return submit_feedback(
        feedback_type=feedback_type,
        name=user_id,
        email="",
        off_definitions=off_definitions,
        suggestions=suggestions,
        additional_feedback=additional_feedback
    )

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
    save_feedback_to_admin_session(feedback_data, "Hardness Agent")

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

        st.session_state.hardness_feedback_submitted = True  # AGENT-SPECIFIC
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        return False

# ===============================
# Main Content
# ===============================

# Display agent progress in sidebar
progress_data = get_agent_progress()
st.sidebar.markdown("### 📊 Agent Progress")
st.sidebar.progress(progress_data['progress'])
st.sidebar.write(f"**{progress_data['completed']}/{progress_data['total']}** dimensions completed")

# Show completion status and navigation
if progress_data['all_completed']:
    st.sidebar.success("🎉 All dimensions completed!")
else:
    st.sidebar.info("🔍 Complete all dimension agents for comprehensive analysis")

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

# Use the unified inputs (Welcome-style) so Hardness page matches all others
account, industry, problem = render_unified_business_inputs(
    page_key_prefix="hardness",
    show_titles=True,
    title_account_industry="Account & Industry",
    title_problem="Business Problem Description",
    save_button_label="✅ Save Problem Details",
)

st.markdown("---")

# ===============================
# Hardness Analysis Section
# ===============================

# Validation checks (without warnings)
has_account = account and account != "Select Account"
has_industry = industry and industry != "Select Industry"
has_problem = bool(problem.strip())

# Check if all agents are completed for comprehensive analysis
all_completed = all_agents_completed()

# Analyze Hardness Button
analyze_btn = st.button("🔍 Analyze Hardness", type="primary", use_container_width=True,
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

    # Build enhanced context with dimension scores if available
    dimension_scores_text = ""
    if all_completed:
        dimension_scores = progress_data['scores']
        dimension_scores_text = "\n\nDimension Scores:\n"
        for dimension, score in dimension_scores.items():
            if score is not None:
                dimension_scores_text += f"{dimension.title()}: {score:.2f}/5\n"
    
    full_context = f"""
    Business Problem:
    {problem.strip()}

    Context:
    Account: {account}
    Industry: {industry}
    {dimension_scores_text}
    """.strip()

    # Prepare headers with authentication
    headers = HEADERS_BASE.copy()
    headers.update({
        "Tenant-ID": TENANT_ID,
        "X-Tenant-ID": TENANT_ID
    })

    if st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

    with st.spinner("🔍 Analyzing problem hardness and difficulty..."):
        progress = st.progress(0)
        st.session_state.hardness_outputs = {}

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
                            
                            st.session_state.hardness_outputs[api_cfg["name"]] = cleaned_text
                        else:
                            error_msg = f"API Error {response.status_code}: {response.text[:200]}"
                            st.session_state.hardness_outputs[api_cfg["name"]] = error_msg

                    except requests.exceptions.Timeout:
                        st.session_state.hardness_outputs[api_cfg["name"]] = "Request timeout: The API took too long to respond."
                    except Exception as e:
                        st.session_state.hardness_outputs[api_cfg["name"]] = f"Error: {str(e)}"

                progress.progress(1.0)
                st.session_state.show_hardness = True
                st.session_state.analysis_complete = True
                st.success("✅ Hardness analysis complete!")

        except Exception as e:
            st.error(f"An unexpected error occurred during analysis: {str(e)}")

# ===============================
# Display Hardness Results
# ===============================

if st.session_state.get("show_hardness") and st.session_state.get("hardness_outputs"):
    st.markdown("---")

    display_account = globals().get("display_account") or st.session_state.get("saved_account", "Unknown Company")
    display_industry = globals().get("display_industry") or st.session_state.get("saved_industry", "Unknown Industry")

    # Section header - Updated to match Vocabulary style
    st.markdown(
        f"""
        <div style="margin: 20px 0;">
            <div class="section-title-box" style="padding: 1rem 1.5rem;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="margin-bottom:8px; color:white; font-weight:800; font-size:1.4rem; line-height:1.2;">
                        Hardness Assessment
                    </h3>
                    <p style="font-size:0.95rem; color:white; margin:0; line-height:1.5; text-align:center; max-width: 800px;">
                        Please note that it is an <strong>AI-generated Hardness Assessment</strong>, derived from 
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

    # Get the hardness output
    hardness_output = st.session_state.hardness_outputs.get("hardness_summary", "")
    
    # Extract score and classification
    hardness_score = extract_hardness_score(hardness_output)
    hardness_classification = extract_hardness_classification(hardness_output)
    
    # Calculate overall score from dimensions if available
    overall_dimension_score = get_overall_hardness_score()
    
    # Create two-column layout with equal dimensions
    col1, col2 = st.columns(2)

    with col1:
        # Overall Classification Box
        if hardness_classification == "HARD":
            classification_html = """
                <div style="
                    background: linear-gradient(135deg, #ff6b6b, #ee5a52);
                    border-radius: 16px;
                    padding: 2rem;
                    text-align: center;
                    color: white;
                    box-shadow: 0 8px 25px rgba(255, 107, 107, 0.3);
                    border: 2px solid #8b1e1e;
                    height: 220px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                ">
                    <h2 style="margin: 0 0 1rem 0; font-size: 2.5rem; font-weight: 800;">
                        🔴 HARD
                    </h2>
                    <p style="margin: 0; font-size: 1.1rem; opacity: 0.9;">
                        This problem requires significant expertise and resources
                    </p>
                </div>
            """
        elif hardness_classification == "MODERATE":
            classification_html = """
                <div style="
                    background: linear-gradient(135deg, #ffa502, #ff7e00);
                    border-radius: 16px;
                    padding: 2rem;
                    text-align: center;
                    color: white;
                    box-shadow: 0 8px 25px rgba(255, 165, 2, 0.3);
                    border: 2px solid #8b1e1e;
                    height: 220px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                ">
                    <h2 style="margin: 0 0 1rem 0; font-size: 2.5rem; font-weight: 800;">
                        🟡 MODERATE
                    </h2>
                    <p style="margin: 0; font-size: 1.1rem; opacity: 0.9;">
                        This problem requires careful planning and execution
                    </p>
                </div>
            """
        else:
            classification_html = """
                <div style="
                    background: linear-gradient(135deg, #51cf66, #40c057);
                    border-radius: 16px;
                    padding: 2rem;
                    text-align: center;
                    color: white;
                    box-shadow: 0 8px 25px rgba(76, 175, 80, 0.3);
                    border: 2px solid #8b1e1e;
                    height: 220px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                ">
                    <h2 style="margin: 0 0 1rem 0; font-size: 2.5rem; font-weight: 800;">
                        🟢 NOT HARD
                    </h2>
                    <p style="margin: 0; font-size: 1.1rem; opacity: 0.9;">
                        This problem can be addressed with standard approaches
                    </p>
                </div>
            """
        
        st.markdown(classification_html, unsafe_allow_html=True)

    with col2:
        # Overall Hardness Score Box
        display_score = hardness_score if hardness_score is not None else overall_dimension_score
        
        if display_score is not None:
            if display_score >= 4.0:
                score_color = "#ff6b6b"
                score_emoji = "🔴"
            elif display_score >= 3.1:
                score_color = "#ffa502"
                score_emoji = "🟡"
            else:
                score_color = "#51cf66"
                score_emoji = "🟢"
            
            score_source = "AI Assessment" if hardness_score is not None else "Dimension Average"
            
            st.markdown(
                f"""
                <div style="
                    background: white;
                    border-radius: 16px;
                    padding: 2rem;
                    text-align: center;
                    border: 2px solid #8b1e1e;
                    box-shadow: 0 3px 10px rgba(139,30,30,0.15);
                    height: 220px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                ">
                    <h3 style="margin: 0 0 0.5rem 0; color: #333; font-size: 1.3rem; font-weight: 600;">
                        Overall Hardness Score
                    </h3>
                    <p style="margin: 0 0 1rem 0; color: #666; font-size: 0.9rem;">
                        {score_source}
                    </p>
                    <div style="
                        font-size: 3rem;
                        font-weight: 800;
                        color: {score_color};
                        margin: 0.5rem 0;
                    ">
                        {score_emoji} {display_score:.1f}/5
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="
                    background: white;
                    border-radius: 16px;
                    padding: 2rem;
                    text-align: center;
                    border: 2px solid #8b1e1e;
                    box-shadow: 0 3px 10px rgba(139,30,30,0.15);
                    height: 220px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                ">
                    <h3 style="margin: 0 0 1rem 0; color: #333; font-size: 1.3rem; font-weight: 600;">
                        Overall Hardness Score
                    </h3>
                    <div style="
                        font-size: 2.5rem;
                        font-weight: 800;
                        color: #ffa502;
                        margin: 0.5rem 0;
                    ">
                        ⚡ Calculating...
                    </div>
                    <p style="margin: 0; color: #666; font-size: 1rem;">
                        Score analysis in progress
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Display Dimension Scores if available
    if all_completed:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="margin: 20px 0;">
                <div class="section-title-box" style="padding: 1rem 1.5rem;">
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                        <h3 style="margin-bottom:8px; color:white; font-weight:800; font-size:1.4rem; line-height:1.2;">
                            📊 Dimension Scores Summary
                        </h3>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Create 4 columns for dimension scores
        dim_cols = st.columns(4)
        dimension_scores = progress_data['scores']
        
        for i, (dimension, score) in enumerate(dimension_scores.items()):
            with dim_cols[i]:
                if score is not None:
                    if score >= 4.0:
                        dim_color = "#ff6b6b"
                        dim_emoji = "🔴"
                    elif score >= 3.1:
                        dim_color = "#ffa502" 
                        dim_emoji = "🟡"
                    else:
                        dim_color = "#51cf66"
                        dim_emoji = "🟢"
                    
                    st.markdown(
                        f"""
                        <div style="
                            background: white;
                            border-radius: 12px;
                            padding: 1.5rem;
                            text-align: center;
                            border: 2px solid #8b1e1e;
                            box-shadow: 0 3px 10px rgba(139,30,30,0.1);
                        ">
                            <h4 style="margin: 0 0 0.5rem 0; color: #333; font-size: 1rem; font-weight: 600;">
                                {dimension.title()}
                            </h4>
                            <div style="
                                font-size: 2rem;
                                font-weight: 800;
                                color: {dim_color};
                                margin: 0.5rem 0;
                            ">
                                {dim_emoji} {score:.1f}
                            </div>
                            <p style="margin: 0; color: #666; font-size: 0.8rem;">
                                /5
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    # Continue with the rest of your existing display code for detailed analysis...
    # [Keep your existing detailed analysis display code here]

# ===============================
# User Feedback Section - UPDATED
# ===============================

if st.session_state.get("show_hardness") and st.session_state.get("hardness_outputs"):
    st.markdown("---")
    st.markdown('<div class="section-title-box" style="text-align:center;"><h3>💬 User Feedback</h3></div>',
                unsafe_allow_html=True)
    st.markdown(
        "Please share your thoughts or suggestions after reviewing the hardness assessment.")

    # Get user ID function
    def get_user_id():
        if 'employee_id' in st.session_state and st.session_state.employee_id:
            return st.session_state.employee_id
        
        possible_keys = ['user_id', 'userID', 'user', 'username', 'email', 'employee_id', 'employeeID']
        for key in possible_keys:
            if key in st.session_state and st.session_state[key]:
                return st.session_state[key]
        
        try:
            shared_data = get_shared_data()
            if shared_data and 'user_id' in shared_data:
                return shared_data['user_id']
            if shared_data and 'employee_id' in shared_data:
                return shared_data['employee_id']
        except:
            pass
        
        return 'Not Available'

    user_id = get_user_id()

    # Show feedback section if not submitted - USING AGENT-SPECIFIC STATE
    if not st.session_state.get('hardness_feedback_submitted', False):
        fb_choice = st.radio(
            "Select your feedback type:",
            options=[
                "I have read it, found it useful, thanks.",
                "I have read it, found the assessment to be off.",
                "The widget seems interesting, but I have some suggestions on the features.",
            ],
            index=None,
            key="hardness_feedback_radio",
        )

        if fb_choice:
            st.session_state.feedback_option = fb_choice

        # Feedback form 1: Positive feedback
        if fb_choice == "I have read it, found it useful, thanks.":
            with st.form("hardness_feedback_form_positive", clear_on_submit=True):
                st.info("Thank you for your positive feedback!")
                st.markdown(f'**Employee ID:** {user_id}')
                submitted = st.form_submit_button("📨 Submit Positive Feedback")
                if submitted:
                    if submit_feedback_wrapper(fb_choice, user_id=user_id):
                        st.rerun()

        # Feedback form 2: Assessment off
        elif fb_choice == "I have read it, found the assessment to be off.":
            with st.form("hardness_feedback_form_assessment", clear_on_submit=True):
                st.markdown("**Please provide details about the assessment issues:**")
                st.markdown(f'**Employee ID:** {user_id}')
                
                assessment_issues = st.text_area(
                    "What aspects of the hardness assessment seem off?",
                    placeholder="Please describe which parts of the assessment (score, classification, justification) seem inaccurate and why...",
                    key="hardness_assessment_issues"
                )
                
                submitted = st.form_submit_button("📨 Submit Feedback")
                if submitted:
                    if not assessment_issues.strip():
                        st.warning("⚠️ Please provide details about the assessment issues.")
                    else:
                        if submit_feedback_wrapper(fb_choice, user_id=user_id, additional_feedback=assessment_issues):
                            st.rerun()

        # Feedback form 3: Suggestions
        elif fb_choice == "The widget seems interesting, but I have some suggestions on the features.":
            with st.form("hardness_feedback_form_suggestions", clear_on_submit=True):
                st.markdown("**Please share your suggestions for improvement:**")
                st.markdown(f'**Employee ID:** {user_id}')
                
                suggestions = st.text_area(
                    "Your suggestions:",
                    placeholder="What features would you like to see improved or added to the hardness assessment?",
                    key="hardness_suggestions"
                )
                
                submitted = st.form_submit_button("📨 Submit Feedback")
                if submitted:
                    if not suggestions.strip():
                        st.warning("⚠️ Please provide your suggestions.")
                    else:
                        if submit_feedback_wrapper(fb_choice, user_id=user_id, suggestions=suggestions):
                            st.rerun()
    
    else:
        # Feedback already submitted - show success and option for another submission
        st.markdown('<div class="feedback-success">✅ Thank you! Your feedback has been recorded.</div>', unsafe_allow_html=True)
        if st.button("📝 Submit Another Feedback", key="hardness_reopen_feedback_btn", use_container_width=True):
            st.session_state.hardness_feedback_submitted = False
            st.rerun()

# =========================================
# ⬅️ BACK BUTTON
# =========================================
st.markdown("---")
if st.button("⬅️ Back to Main Page", use_container_width=True):
    st.switch_page("Welcome_Agent.py")
