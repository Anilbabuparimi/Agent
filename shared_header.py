"""
Shared header component for all Streamlit agents.
Provides fixed header with logo, title, theme toggle, and admin access.
"""
import streamlit as st
import streamlit.components.v1 as components
import os
import pandas as pd
from urllib.parse import unquote
from datetime import datetime

# Logo URL for the header
LOGO_URL = "https://yt3.googleusercontent.com/ytc/AIdro_k-7HkbByPWjKpVPO3LCF8XYlKuQuwROO0vf3zo1cqgoaE=s900-c-k-c0x00ffffff-no-rj"

# Feedback file path for admin section
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

# ================================
# 🏢 Account & Industry Mapping
# ================================

ACCOUNT_INDUSTRY_MAP = {
    "Select Account": "Select Industry",
    "Abbott Ireland": "Pharma",
    "Abbott Laboratories": "Pharma",
    "Abbvie": "Pharma",
    "BMS Germany": "Pharma",
    "BMS Japan": "Pharma",
    "Bristol-Myers Squibb": "Pharma",
    "Envista": "Healthcare",
    "Gilead Sciences, Inc.": "Pharma",
    "J&J Inc": "Pharma",
    "J&J Japan": "Pharma",
    "J&J Singapore": "Pharma",
    "Novartis": "Pharma",
    "Sanofi": "Pharma",
    "Dell": "Technology",
    "Microsoft": "Technology",
    "RECURSION": "Technology",
    "Chevron India": "Energy",
    "CHEVRON U.S.A. INC.": "Energy",
    "OXY": "Energy",
    "SABIC": "Energy",
    "BMO": "Finance",
    "Citigroup": "Finance",
    "Coles": "Retail",
    "Home Depot": "Retail",
    "Nike": "Consumer Goods",
    "THD": "Retail",
    "Walmart": "Retail",
    "Walmart Mexico": "Retail",
    "ADM": "Food & Beverage",
    "Mars": "Consumer Goods",
    "MARS China": "Consumer Goods",
    "Southwest": "Airlines",
    "T Mobile": "Telecom",
    "NCLH": "Hospitality",
    "RTX": "Aerospace",
    "Itkan": "Technology",
    "Loyalty Pacific": "Services",
    "Skills Development": "Education",
    "Others": "Other"
}

# --- All accounts (alphabetically sorted, with Others at the end) ---
ALL_ACCOUNTS = [
    acc for acc in ACCOUNT_INDUSTRY_MAP.keys()
    if acc != "Select Account" and acc != "Others"
]
ALL_ACCOUNTS.sort()
ALL_ACCOUNTS.append("Others")

# --- Final ordered account list ---
ACCOUNTS = ["Select Account"] + ALL_ACCOUNTS

# --- Unique Industries ---
all_industries = list(set(ACCOUNT_INDUSTRY_MAP.values()))
INDUSTRIES = sorted([i for i in all_industries if i != "Select Industry"])
if "Other" not in INDUSTRIES:
    INDUSTRIES.append("Other")
INDUSTRIES = ["Select Industry"] + INDUSTRIES

# ================================
# 🔐 Admin Session Management
# ================================

def init_admin_session():
    """Initialize admin session state for all agents"""
    if 'admin_feedback_data' not in st.session_state:
        st.session_state.admin_feedback_data = pd.DataFrame(
            columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType", 
                    "OffDefinitions", "Suggestions", "Account", "Industry", 
                    "ProblemStatement", "Agent"]
        )
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'admin_access_requested' not in st.session_state:
        st.session_state.admin_access_requested = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = ''
    if 'show_admin_panel' not in st.session_state:
        st.session_state.show_admin_panel = False

def save_feedback_to_admin_session(feedback_data, agent_name="Vocabulary Agent"):
    """
    Save feedback data to admin session storage for all agents
    """
    init_admin_session()  # Ensure session is initialized
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add agent information to feedback data
    feedback_data_with_agent = feedback_data.copy()
    feedback_data_with_agent['Agent'] = agent_name
    feedback_data_with_agent['Timestamp'] = timestamp
    
    # Convert to DataFrame if not already
    if not isinstance(feedback_data_with_agent, pd.DataFrame):
        feedback_data_with_agent = pd.DataFrame([feedback_data_with_agent])
    
    # Append to admin session storage
    st.session_state.admin_feedback_data = pd.concat(
        [st.session_state.admin_feedback_data, feedback_data_with_agent], 
        ignore_index=True
    )
    
    # Also save to file for persistence
    save_feedback_to_file(feedback_data_with_agent)
    
    return True

def save_feedback_to_file(feedback_data):
    """
    Save feedback to CSV file with fallback to session state
    """
    try:
        # Ensure the feedback data has all required columns including 'Agent'
        required_columns = ["Timestamp", "Name", "Email", "Feedback", "FeedbackType", 
                           "OffDefinitions", "Suggestions", "Account", "Industry", 
                           "ProblemStatement", "Agent"]
        
        # Add missing columns with empty values
        for col in required_columns:
            if col not in feedback_data.columns:
                feedback_data[col] = ''
        
        if os.path.exists(FEEDBACK_FILE):
            existing = pd.read_csv(FEEDBACK_FILE)
            
            # Handle schema mismatch - ensure existing data also has all columns
            for col in required_columns:
                if col not in existing.columns:
                    existing[col] = ''
            
            # Reorder both dataframes to match required columns
            existing = existing[required_columns]
            feedback_data = feedback_data[required_columns]
            
            updated = pd.concat([existing, feedback_data], ignore_index=True)
        else:
            # Create new file with all required columns
            updated = feedback_data[required_columns]
        
        updated.to_csv(FEEDBACK_FILE, index=False)
        return True
        
    except (PermissionError, OSError) as e:
        # Fallback to session state on Streamlit Cloud
        if 'file_feedback_data' not in st.session_state:
            st.session_state.file_feedback_data = pd.DataFrame(columns=feedback_data.columns)
        
        st.session_state.file_feedback_data = pd.concat(
            [st.session_state.file_feedback_data, feedback_data], 
            ignore_index=True
        )
        return True
        
    except Exception as e:
        st.error(f"Error saving feedback to file: {str(e)}")
        return False

def get_all_feedback_data():
    """
    Get combined feedback data from both file and session state
    """
    file_data = pd.DataFrame()
    session_data = pd.DataFrame()
    
    # Try to load from file
    try:
        if os.path.exists(FEEDBACK_FILE):
            file_data = pd.read_csv(FEEDBACK_FILE)
            # Ensure the file data has Agent column
            if 'Agent' not in file_data.columns:
                file_data['Agent'] = 'Unknown Agent'
    except Exception as e:
        st.warning(f"Could not read feedback file: {e}")
    
    # Get from session state
    if 'admin_feedback_data' in st.session_state and not st.session_state.admin_feedback_data.empty:
        session_data = st.session_state.admin_feedback_data.copy()
    
    if 'file_feedback_data' in st.session_state and not st.session_state.file_feedback_data.empty:
        session_data = pd.concat([session_data, st.session_state.file_feedback_data], ignore_index=True)
    
    # Combine data, preferring session data for duplicates
    if not file_data.empty and not session_data.empty:
        combined = pd.concat([file_data, session_data], ignore_index=True).drop_duplicates()
        return combined
    elif not file_data.empty:
        return file_data
    elif not session_data.empty:
        return session_data
    else:
        return pd.DataFrame()

def _safe_rerun():
    """Safely rerun the app without causing errors."""
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            components.html(
                "<script>window.parent.location.reload();</script>",
                height=0
            )

def sync_theme_with_session():
    """Sync theme between localStorage and Streamlit session state"""
    # Initialize theme in session state if not present
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    # Try to get theme from localStorage via JavaScript
    try:
        # This component will read localStorage and set session state
        components.html("""
        <script>
        (function() {
            const savedTheme = localStorage.getItem('appTheme') || 'light';
            const isDark = savedTheme === 'dark';
            
            // Send to Streamlit
            if (window.parent.Streamlit) {
                window.parent.Streamlit.setComponentValue({
                    dark_mode: isDark,
                    theme: savedTheme
                });
            }
        })();
        </script>
        """, height=0)
    except:
        pass

def render_header(
    agent_name="Business Problem Analysis Platform",
    agent_subtitle="Specialized AI agents to extract, classify, and analyze key dimensions of your business challenges",
    enable_admin_access=True,
    header_height=85
):
    """
    Fixed header (shared across agents).
    - enable_admin_access: if True, clicking the logo toggles admin view via URL param.
    - header_height: header height in px (default 85).
    """
    # Initialize admin session
    init_admin_session()

    # Initialize session state
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = ''
    if 'show_admin_panel' not in st.session_state:
        st.session_state.show_admin_panel = False
    if 'admin_view_selected' not in st.session_state:
        st.session_state.admin_view_selected = False

    # Sync theme with session state
    sync_theme_with_session()

    # Check for admin panel URL parameter - CRITICAL: Do this BEFORE rendering
    try:
        qparams = st.query_params
        if 'adminPanelToggled' in qparams:
            param_val = qparams.get('adminPanelToggled')
            if isinstance(param_val, list):
                param_val = param_val[0] if param_val else ''
            
            if str(param_val).lower() in ('1', 't', 'true', 'show', 'yes'):
                # Set admin flags IMMEDIATELY
                st.session_state.current_page = 'admin'
                st.session_state.show_admin_panel = True
                st.session_state.admin_view_selected = True
                
                # Clear the parameter to prevent loops
                try:
                    components.html("""
                        <script>
                        (function(){
                            try {
                                const url = new URL(window.parent.location.href);
                                url.searchParams.delete('adminPanelToggled');
                                window.parent.history.replaceState(null, '', url.pathname + url.search + url.hash);
                            } catch(e) {}
                        })();
                        </script>
                    """, height=0)
                except Exception:
                    pass
    except Exception:
        pass

    # Admin badge (visible when admin session active)
    admin_badge_html = ""
    if st.session_state.get('current_page', '') == 'admin':
        admin_badge_html = '<span style="margin-left:8px;padding:4px 8px;background:rgba(255,255,255,0.95);color:#8b1e1e;font-weight:700;border-radius:12px;font-size:0.75rem;white-space:nowrap;">ADMIN</span>'

       # Apply comprehensive CSS with Mu Sigma colors and NO GAPS
    st.markdown(f"""
    <style>
    /* Reset Streamlit built-in header COMPLETELY */
    [data-testid="stHeader"], 
    header[data-testid="stHeader"],
    .stApp > header {{
        height: 0 !important;
        background: transparent !important;
        display: none !important;
        visibility: hidden !important;
        padding: 0 !important;
        margin: 0 !important;
    }}

    /* Fixed Header - ABSOLUTELY NO GAPS */
    .fixed-header {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: {header_height}px;
        background: linear-gradient(135deg, #8b1e1e 0%, #6b1515 100%);
        box-shadow: 0 2px 20px rgba(0,0,0,0.4);
        z-index: 999999;
        display: flex !important;
        align-items: center;
        justify-content: space-between;
        padding: 0 2rem;
        border-bottom: 3px solid #ff6b35;
    }}

    .header-logo {{
        display: flex;
        align-items: center;
        cursor: pointer;
        transition: transform 0.3s ease;
    }}

    .header-logo:hover {{
        transform: scale(1.05);
    }}

    .header-logo img {{
        width: 48px;
        height: 48px;
        border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.5);
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }}

    .header-title {{
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        text-align: center;
    }}

    .header-title h1 {{
        color: #ffffff !important;
        font-size: 1.7rem;
        font-weight: 800;
        margin: 0;
        line-height: 1.1;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        letter-spacing: -0.5px;
    }}

    .header-title p {{
        color: rgba(255,255,255,0.95);
        font-size: 0.85rem;
        font-weight: 500;
        margin: 3px 0 0 0;
        text-shadow: 0.5px 0.5px 1px rgba(0,0,0,0.2);
    }}

    /* CRITICAL: ABSOLUTELY NO GAP - Content starts RIGHT after header */
    .main .block-container {{
        padding-top: {header_height}px !important;
        padding-bottom: 0 !important;
        margin-top: 0 !important;
    }}

    .stApp {{
        margin-top: 0 !important;
        padding-top: 0 !important;
    }}

    /* Remove ALL gaps and margins */
    body, html, .stApp {{
        overflow-x: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow-y: auto !important;
    }}

    /* Remove any Streamlit default padding */
    [data-testid="stAppViewContainer"] {{
        padding: 0 !important;
        margin: 0 !important;
    }}

    .theme-toggle-capsule {{
        display: flex;
        background-color: rgba(255,255,255,0.15);
        border-radius: 25px;
        padding: 4px;
        gap: 4px;
        backdrop-filter: blur(10px);
        border: 2px solid rgba(255,255,255,0.3);
        align-items: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }}

    .theme-toggle-btn {{
        padding: 8px 18px;
        border: none;
        border-radius: 20px;
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.3s ease;
        background-color: transparent;
        color: rgba(255,255,255,0.8);
        font-weight: 600;
    }}

    .theme-toggle-btn.active {{
        background-color: white;
        color: #8b1e1e;
        box-shadow: 0 2px 8px rgba(255,255,255,0.4);
    }}

    .theme-toggle-btn:hover {{
        transform: scale(1.05);
        color: white;
    }}

    /* MU SIGMA COLORS FOR BUTTONS */
    .stButton > button, 
    button[kind="primary"], 
    button[kind="secondary"],
    .stDownloadButton > button,
    .stButton > button:not(.theme-toggle-btn) {{
        background: linear-gradient(135deg, #8b1e1e 0%, #ff6b35 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(139,30,30,0.4) !important;
        font-size: 0.95rem !important;
    }}

    .stButton > button:hover,
    button[kind="primary"]:hover,
    button[kind="secondary"]:hover {{
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 6px 20px rgba(139,30,30,0.5) !important;
        background: linear-gradient(135deg, #a82828 0%, #ff7b45 100%) !important;
    }}

    /* Secondary buttons with outline */
    button[kind="secondary"]:not(.theme-toggle-btn) {{
        background: transparent !important;
        border: 2px solid #8b1e1e !important;
        color: #8b1e1e !important;
        box-shadow: 0 2px 8px rgba(139,30,30,0.2) !important;
    }}

    button[kind="secondary"]:not(.theme-toggle-btn):hover {{
        background: linear-gradient(135deg, #8b1e1e 0%, #ff6b35 100%) !important;
        color: white !important;
        border-color: transparent !important;
    }}

        /* ========================================
       DARK MODE THEME STYLES - Enhanced Visibility
       ======================================== */
    /* Fix dropdown selected option visibility in dark mode */
    body[data-theme="dark"] .stSelectbox [data-baseweb="select"] > div {{
        background-color: #1f2937 !important;
        color: #ffffff !important;
        border: 2px solid rgba(255,255,255,0.3) !important;
    }}
    
    body[data-theme="dark"] .stSelectbox [data-baseweb="select"] > div:hover {{
        background-color: #374151 !important;
        border-color: rgba(255,255,255,0.5) !important;
    }}

    body[data-theme="dark"] .stSelectbox [data-baseweb="popover"] {{
        background-color: #1f2937 !important;
        border: 2px solid rgba(255,255,255,0.3) !important;
    }}
    
    body[data-theme="dark"] .stSelectbox [data-baseweb="popover"] div {{
        background-color: #1f2937 !important;
        color: #ffffff !important;
    }}
    
    body[data-theme="dark"] .stSelectbox [data-baseweb="popover"] div:hover {{
        background-color: #374151 !important;
        color: #ffffff !important;
    }}
    
    body[data-theme="dark"] .stSelectbox [data-baseweb="select"] > div:before {{
        color: #ffffff !important;
    }}
    
    /* Consistent text input backgrounds in dark mode */
    body[data-theme="dark"] .stTextInput input,
    body[data-theme="dark"] .stTextArea textarea {{
        background-color: #1f2937 !important;
        color: #ffffff !important;
        border: 2px solid rgba(255,255,255,0.3) !important;
    }}

    body[data-theme="dark"] .stTextInput input:focus,
    body[data-theme="dark"] .stTextArea textarea:focus {{
        background-color: #1f2937 !important;
        border-color: #8b1e1e !important;
    }}
    
    body[data-theme="dark"] .stTextInput input::placeholder,
    body[data-theme="dark"] .stTextArea textarea::placeholder {{
        color: rgba(255,255,255,0.6) !important;
    }}
    
    body[data-theme="dark"] .stRadio label {{
        color: #ffffff !important;
        font-weight: 500 !important;
    }}
    
    body[data-theme="dark"] .stRadio [data-testid="stMarkdownContainer"] {{
        color: #ffffff !important;
    }}
    body[data-theme="dark"] .stApp {{
        background: linear-gradient(135deg, #0b0f14 0%, #18181b 50%, #23272f 100%) !important;
        color: #f8fafc !important;
    }}

    /* Fix cursor visibility in dark mode for all input fields */
    body[data-theme="dark"] .stTextInput input,
    body[data-theme="dark"] .stTextArea textarea,
    body[data-theme="dark"] .stSelectbox [data-baseweb="select"] > div {{
        caret-color: #ffffff !important;
    }}
    
    /* Ensure text selection is visible in dark mode */
    body[data-theme="dark"] ::selection {{
        background-color: rgba(255, 255, 255, 0.3) !important;
        color: #ffffff !important;
    }}

    body[data-theme="dark"] ::-moz-selection {{
        background-color: rgba(255, 255, 255, 0.3) !important;
        color: #ffffff !important;
    }}

    /* Dark mode - Clean headings without blur/shadow */
    body[data-theme="dark"] h1,
    body[data-theme="dark"] h2,
    body[data-theme="dark"] h3,
    body[data-theme="dark"] h4,
    body[data-theme="dark"] h5,
    body[data-theme="dark"] h6 {{
        color: #f8fafc !important;
        text-shadow: none !important;
        filter: none !important;
        font-weight: 700 !important;
    }}

    body[data-theme="dark"] .stMarkdown h1,
    body[data-theme="dark"] .stMarkdown h2,
    body[data-theme="dark"] .stMarkdown h3 {{
        color: #f8fafc !important;
        text-shadow: none !important;
        filter: none !important;
    }}

    /* Dark mode - Enhanced text inputs */
    body[data-theme="dark"] .stTextInput input,
    body[data-theme="dark"] .stTextArea textarea {{
        background: #1f2937 !important;
        color: #ffffff !important;
        border: 2px solid rgba(255,255,255,0.2) !important;
        font-weight: 500 !important;
    }}

    body[data-theme="dark"] .stTextInput input::placeholder,
    body[data-theme="dark"] .stTextArea textarea::placeholder {{
        color: rgba(255,255,255,0.5) !important;
        font-weight: 400 !important;
    }}

    /* DARK MODE DROPDOWN FIX - CRITICAL */
    body[data-theme="dark"] .stSelectbox [data-baseweb="select"] > div {{
        background-color: #1f2937 !important;
        color: #ffffff !important;
        border: 2px solid rgba(255,255,255,0.3) !important;
    }}

    body[data-theme="dark"] .stSelectbox [data-baseweb="select"] > div:hover {{
        background-color: #374151 !important;
        border-color: rgba(255,255,255,0.5) !important;
    }}

    body[data-theme="dark"] .stSelectbox [data-baseweb="popover"] {{
        background-color: #1f2937 !important;
        border: 2px solid rgba(255,255,255,0.3) !important;
    }}

    body[data-theme="dark"] .stSelectbox [data-baseweb="popover"] div {{
        background-color: #1f2937 !important;
        color: #ffffff !important;
    }}

    body[data-theme="dark"] .stSelectbox [data-baseweb="popover"] div:hover {{
        background-color: #374151 !important;
        color: #ffffff !important;
    }}

    body[data-theme="dark"] .stSelectbox [data-baseweb="select"] > div:before {{
        color: #ffffff !important;
    }}

    /* ========================================
       LIGHT MODE THEME STYLES - Clean Headings
       ======================================== */
    body[data-theme="light"] .stApp {{
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%) !important;
        color: #1e293b !important;
    }}

    /* Light mode - Clean headings without blur/shadow */
    body[data-theme="light"] h1,
    body[data-theme="light"] h2,
    body[data-theme="light"] h3,
    body[data-theme="light"] h4,
    body[data-theme="light"] h5,
    body[data-theme="light"] h6 {{
        color: #1e293b !important;
        text-shadow: none !important;
        filter: none !important;
        font-weight: 700 !important;
    }}

    body[data-theme="light"] .stMarkdown h1,
    body[data-theme="light"] .stMarkdown h2,
    body[data-theme="light"] .stMarkdown h3 {{
        color: #1e293b !important;
        text-shadow: none !important;
        filter: none !important;
    }}

    /* Light mode - Enhanced text inputs */
    body[data-theme="light"] .stTextInput input,
    body[data-theme="light"] .stTextArea textarea {{
        background: #ffffff !important;
        color: #1e293b !important;
        border: 2px solid #e2e8f0 !important;
        font-weight: 500 !important;
    }}

    /* Enhanced section titles with Mu Sigma colors */
    .section-title-box {{
        background: linear-gradient(135deg, #8b1e1e 0%, #ff6b35 100%) !important;
        border-radius: 10px;
        padding: 1rem 2rem;
        margin: 0 0 1rem 0 !important;
        text-align: center;
        box-shadow: 0 4px 12px rgba(139,30,30,0.3);
    }}

    .section-title-box h3 {{
        color:#ffffff!important;
        margin:0!important;
        font-weight:700!important;
        font-size:1.3rem!important;
        text-shadow: none !important;
    }}

    /* Enhanced font visibility - NO BLUR */
    .stApp * {{
        font-family: 'Inter', sans-serif !important;
        text-shadow: none !important;
        filter: none !important;
    }}

    body[data-theme="dark"] .stApp * {{
        color: #f8fafc !important;
    }}

    body[data-theme="light"] .stApp * {{
        color: #1e293b !important;
    }}

    /* Remove any text shadows from all elements */
    * {{
        text-shadow: none !important;
    }}

    /* Ensure clean typography */
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {{
        text-shadow: none !important;
        filter: none !important;
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Build admin href - Direct navigation
    admin_href = "?adminPanelToggled=true" if enable_admin_access else "#"

    # Render the header HTML
    st.markdown(f"""
<div class="fixed-header">
    <a href="{admin_href}" style="text-decoration:none;" title="Open Admin View">
        <div class="header-logo">
            <img src="{LOGO_URL}" alt="Mu Sigma Logo">{admin_badge_html}
        </div>
    </a>
    <div class="header-title">
        <h1>{agent_name}</h1>
        <p>{agent_subtitle}</p>
    </div>
    <div class="theme-toggle-capsule">
        <button class="theme-toggle-btn active" id="theme-light-btn">☀️ Light</button>
        <button class="theme-toggle-btn" id="theme-dark-btn">🌙 Dark</button>
    </div>
</div>
    """, unsafe_allow_html=True)

    # Add JavaScript for theme switching with persistent session state
    components.html(f"""
    <script>
    (function() {{
        const doc = window.parent.document;
        
        // Function to apply theme and update Streamlit session state
        function applyTheme(theme) {{
            // Apply to DOM
            doc.body.setAttribute('data-theme', theme);
            localStorage.setItem('appTheme', theme);
            
            // Update button states
            const lightBtn = doc.getElementById('theme-light-btn');
            const darkBtn = doc.getElementById('theme-dark-btn');
            
            if (lightBtn && darkBtn) {{
                if (theme === 'light') {{
                    lightBtn.classList.add('active');
                    darkBtn.classList.remove('active');
                }} else {{
                    darkBtn.classList.add('active');
                    lightBtn.classList.remove('active');
                }}
            }}
            
            // Send theme to Streamlit session state
            if (window.parent.Streamlit) {{
                window.parent.Streamlit.setComponentValue({{
                    theme: theme,
                    timestamp: new Date().getTime()
                }});
            }}
        }}
        
        // Initialize theme from localStorage or default
        function initTheme() {{
            const savedTheme = localStorage.getItem('appTheme') || 'light';
            applyTheme(savedTheme);
            
            // Set up button event listeners
            const lightBtn = doc.getElementById('theme-light-btn');
            const darkBtn = doc.getElementById('theme-dark-btn');
            
            if (lightBtn) {{
                lightBtn.onclick = function(e) {{
                    e.preventDefault();
                    e.stopPropagation();
                    applyTheme('light');
                    return false;
                }};
            }}
            
            if (darkBtn) {{
                darkBtn.onclick = function(e) {{
                    e.preventDefault();
                    e.stopPropagation();
                    applyTheme('dark');
                    return false;
                }};
            }}
        }}
        
        // Enhanced initialization with retry logic
        function tryInit(attempts = 0) {{
            if (attempts > 15) {{
                console.log('Theme initialization failed after max attempts');
                return;
            }}
            
            const lightBtn = doc.getElementById('theme-light-btn');
            const darkBtn = doc.getElementById('theme-dark-btn');
            
            if (lightBtn && darkBtn) {{
                initTheme();
                console.log('Theme initialized successfully');
            }} else {{
                setTimeout(() => tryInit(attempts + 1), 150);
            }}
        }}
        
        // Listen for theme changes from other components
        function setupThemeListener() {{
            window.addEventListener('storage', function(e) {{
                if (e.key === 'appTheme') {{
                    applyTheme(e.newValue);
                }}
            }});
            
            window.addEventListener('themeChange', function(e) {{
                if (e.detail && e.detail.theme) {{
                    applyTheme(e.detail.theme);
                }}
            }});
        }}
        
        // Start initialization
        if (doc.readyState === 'loading') {{
            doc.addEventListener('DOMContentLoaded', function() {{
                tryInit();
                setupThemeListener();
            }});
        }} else {{
            tryInit();
            setupThemeListener();
        }}
        
        // Force theme application on page load
        window.addEventListener('load', function() {{
            const savedTheme = localStorage.getItem('appTheme') || 'light';
            applyTheme(savedTheme);
        }});
    }})();
    </script>
    """, height=0)

def get_shared_data():
    """Get shared data from session state or URL parameters"""
    data = {
        'employee_id': '',
        'account': '',
        'industry': '',
        'problem': ''
    }

    try:
        if hasattr(st, 'query_params'):
            query_params = st.query_params
            for key in data.keys():
                val = query_params.get(key, '')
                if isinstance(val, list):
                    val = val[0] if val else ''
                data[key] = unquote(val) if val else ''
    except Exception:
        pass

    try:
        for key in data.keys():
            session_key = 'employee_id' if key == 'employee_id' else f'business_{key}'
            if data[key] and (session_key not in st.session_state or not st.session_state[session_key]):
                st.session_state[session_key] = data[key]
    except Exception:
        pass

    return {
        'employee_id': st.session_state.get('employee_id', data['employee_id']),
        'account': st.session_state.get('business_account', data['account']),
        'industry': st.session_state.get('business_industry', data['industry']),
        'problem': st.session_state.get('business_problem', data['problem'])
    }

def render_unified_business_inputs(page_key_prefix: str = "global", show_titles: bool = True,
                                   title_account_industry: str = "Account & Industry",
                                   title_problem: str = "Business Problem Description",
                                   save_button_label: str = "✅ Save Problem Details"):
    """Render a standardized Account/Industry + Business Problem input UI."""
    
    # Initialize saved state
    if 'saved_account' not in st.session_state:
        st.session_state.saved_account = "Select Account"
    if 'saved_industry' not in st.session_state:
        st.session_state.saved_industry = "Select Industry"
    if 'saved_problem' not in st.session_state:
        st.session_state.saved_problem = ""

    # Working values
    if 'business_account' not in st.session_state:
        st.session_state.business_account = st.session_state.saved_account
    if 'business_industry' not in st.session_state:
        st.session_state.business_industry = st.session_state.saved_industry
    if 'business_problem' not in st.session_state:
        st.session_state.business_problem = st.session_state.saved_problem

    # Confirmation flags
    if 'edit_confirmed' not in st.session_state:
        st.session_state.edit_confirmed = False
    if 'cancel_clicked' not in st.session_state:
        st.session_state.cancel_clicked = False
    if 'selectbox_key_counter' not in st.session_state:
        st.session_state.selectbox_key_counter = 0

    # Enhanced input styles with better visibility
    st.markdown("""
    <style>
        .stSelectbox { margin-bottom: 1rem; }
        .stSelectbox > label { font-weight:700!important; font-size:1rem!important; margin-bottom:0.5rem!important; color: inherit !important; }
        .stSelectbox > div > div { border:2px solid rgba(139,30,30,0.4)!important; border-radius:10px!important; padding:0.5rem 0.75rem!important; min-height:42px!important; max-height:42px!important; display:flex!important; align-items:center!important; }
        .stSelectbox [data-baseweb="select"] { min-height:36px!important; max-height:36px!important; }
        .stSelectbox [data-baseweb="select"] > div { font-size:0.95rem!important; font-weight:600!important; line-height:1.3!important; white-space:nowrap!important; overflow:hidden!important; text-overflow:ellipsis!important; padding:0!important; display:flex!important; align-items:center!important; }
        .stTextArea textarea { border:2px solid rgba(139,30,30,0.3)!important; border-radius:10px!important; font-size:1.05rem!important; padding:1.25rem!important; line-height:1.7!important; min-height:180px!important; font-weight:500!important; }
        .section-title-box { background: linear-gradient(135deg, #8b1e1e 0%, #ff6b35 100%)!important; border-radius:10px; padding:1rem 2rem; margin:0 0 1rem 0!important; text-align:center; box-shadow: 0 4px 12px rgba(139,30,30,0.3); }
        .section-title-box h3 { color:#ffffff!important; margin:0!important; font-weight:700!important; font-size:1.3rem!important; text-shadow: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # Section title
    if show_titles:
        st.markdown(f'<div class="section-title-box"><h3>{title_account_industry}</h3></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    show_confirmation = False
    account_change_value = None

    with c1:
        account_input = st.selectbox(
            "Select Account:",
            options=ACCOUNTS,
            index=ACCOUNTS.index(st.session_state.business_account) if st.session_state.business_account in ACCOUNTS else 0,
            key=f"{page_key_prefix}_account_select_{st.session_state.selectbox_key_counter}"
        )

        # 🔥 FIX: Handle account change and auto-map industry IMMEDIATELY
        if account_input != st.session_state.business_account:
            if st.session_state.cancel_clicked:
                st.session_state.cancel_clicked = False
            elif st.session_state.saved_problem and not st.session_state.edit_confirmed:
                show_confirmation = True
                account_change_value = account_input
            else:
                # Immediate update
                st.session_state.business_account = account_input
                # 🔥 AUTO-MAP INDUSTRY IMMEDIATELY - This is the key fix
                if account_input in ACCOUNT_INDUSTRY_MAP:
                    mapped_industry = ACCOUNT_INDUSTRY_MAP[account_input]
                    st.session_state.business_industry = mapped_industry
                    # Force a rerun to update the UI
                    st.rerun()

    with c2:
        # 🔥 FIX: Always get the latest values from session state
        current_industry = st.session_state.business_industry
        current_account = st.session_state.business_account
        
        # Check if industry should be auto-mapped (disabled)
        is_auto_mapped = current_account in ACCOUNT_INDUSTRY_MAP and current_account != "Select Account"
        
        # 🔥 FIX: Ensure the index is calculated correctly with current values
        industry_index = INDUSTRIES.index(current_industry) if current_industry in INDUSTRIES else 0
        
        industry_input = st.selectbox(
            "Industry:", 
            options=INDUSTRIES,
            index=industry_index,
            disabled=is_auto_mapped,
            help="Industry is automatically mapped for this account" if is_auto_mapped else "Select the industry for this analysis",
            key=f"{page_key_prefix}_industry_select_{st.session_state.selectbox_key_counter}"
        )
        
        # Only allow manual industry change if not auto-mapped
        if not is_auto_mapped and industry_input != st.session_state.business_industry:
            st.session_state.business_industry = industry_input

    # Confirmation dialog for account change
    if show_confirmation:
        st.markdown("""
            <style>
            .confirmation-box { background: linear-gradient(135deg, rgba(255,107,53,0.15), rgba(139,30,30,0.15)); border: 2px solid rgba(255,107,53,0.4); border-radius: 10px; padding: 18px 24px; box-shadow: 0 4px 12px rgba(139,30,30,0.2); margin: 15px 0; }
            .confirmation-message { color: #8b1e1e; font-size: 16px; font-weight: 700; margin-bottom: 0; text-align: center; text-shadow: none !important; }
            </style>
        """, unsafe_allow_html=True)
        st.markdown("""
            <div class="confirmation-box">
                <div class="confirmation-message">💡 <strong>Proceed with new problem?</strong><br>
                    <span style="font-size: 14px; font-weight: 500; color: #555;">Changing the account will update your business problem details.</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        colA, colB, colC, colD, colE = st.columns([3, 1.2, 0.6, 1.2, 3])
        with colB:
            if st.button("Yes", key=f"{page_key_prefix}_confirm_edit", type="primary"):
                st.session_state.edit_confirmed = True
                st.session_state.business_account = account_change_value
                # 🔥 AUTO-MAP INDUSTRY IN CONFIRMATION FLOW
                if account_change_value in ACCOUNT_INDUSTRY_MAP:
                    mapped_industry = ACCOUNT_INDUSTRY_MAP[account_change_value]
                    st.session_state.business_industry = mapped_industry
                st.session_state.selectbox_key_counter += 1
                # Show Save button after user clicks "Yes" in ALL pages
                st.session_state[f'{page_key_prefix}_show_save_btn'] = True
                _safe_rerun()
        with colD:
            if st.button("No", key=f"{page_key_prefix}_cancel_edit", type="secondary"):
                st.session_state.cancel_clicked = True
                st.session_state.business_account = st.session_state.saved_account
                st.session_state.business_industry = st.session_state.saved_industry
                st.session_state.selectbox_key_counter += 1
                _safe_rerun()

    # Problem section
    if show_titles:
        st.markdown(f'<div class="section-title-box"><h3>{title_problem}</h3></div>', unsafe_allow_html=True)

    problem_input = st.text_area(
        "Describe your business problem in detail:",
        value=st.session_state.business_problem,
        height=180,
        placeholder="Feel free to just type down your problem statement, or copy-paste if you have it handy somewhere...",
        label_visibility="collapsed",
        key=f"{page_key_prefix}_problem_textarea"
    )
    if problem_input != st.session_state.business_problem:
        st.session_state.business_problem = problem_input

    # Add a new parameter to control Save button visibility
    # For Welcome page (main_app), default to True initially, then use session state
    # For other pages, default to False initially, then use session state
    default_show = True if page_key_prefix == "main_app" else False
    show_save_button = st.session_state.get(f'{page_key_prefix}_show_save_btn', default_show)
    
    # Show Save button based on session state
    if show_save_button:
        if st.button(save_button_label, use_container_width=True, type="primary", key=f"{page_key_prefix}_save_btn"):
            if (st.session_state.business_account == "Select Account" or
                st.session_state.business_industry == "Select Industry" or
                not st.session_state.business_problem.strip()):
                st.error("⚠️ Please select an Account, Industry, and provide a Business Problem description.")
            else:
                st.session_state.saved_account = st.session_state.business_account
                st.session_state.saved_industry = st.session_state.business_industry
                st.session_state.saved_problem = st.session_state.business_problem
                st.session_state.edit_confirmed = False
                # Hide Save button after successful save in ALL pages
                st.session_state[f'{page_key_prefix}_show_save_btn'] = False
                st.success("✅ Problem details saved!")
                _safe_rerun()

    return (
        st.session_state.business_account,
        st.session_state.business_industry,
        st.session_state.business_problem,
    )



def render_admin_panel(admin_password="admin123"):
    """
    Render admin panel with password authentication and feedback download.
    Uses the unified admin session storage.
    """
    
    # STOP rendering anything else - Admin panel takes over the entire page
    st.markdown('<div style="padding-top: 10px;"></div>', unsafe_allow_html=True)

    # Admin section header with styling
    st.markdown("""
    <div style='background: linear-gradient(135deg, #8b1e1e 0%, #6b1515 100%); 
                padding: 20px; 
                border-radius: 10px; 
                margin-bottom: 20px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <h2 style='color: white; margin: 0; text-align: center;'>
            📊 Admin Section - Download Reports
        </h2>
    </div>
    """, unsafe_allow_html=True)

    # Small back button to return to main app
    col_back1, col_back2, col_back3 = st.columns([1, 2, 1])
    with col_back1:
        if st.button("← Back to Login", key="admin_back_btn", use_container_width=True):
            st.session_state.current_page = 'login'
            st.session_state.show_admin_panel = False
            st.session_state.admin_view_selected = False
            st.session_state.admin_authenticated = False
            st.session_state.admin_access_requested = False
            try:
                st.query_params.clear()
            except:
                pass
            _safe_rerun()

    st.markdown("---")

    # Admin authentication with button first
    st.markdown("### 🔐 Admin Authentication")
    
    # Show button first, then password field
    if not st.session_state.admin_access_requested:
        st.info("💡 Click the button below to request admin access")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            if st.button("🔓 Request Admin Access", use_container_width=True, type="primary", key="request_admin_btn"):
                st.session_state.admin_access_requested = True
                _safe_rerun()
    else:
        # Show password input after button is clicked
        password = st.text_input("Enter admin password:",
                                 type="password",
                                 key="admin_password",
                                 placeholder="Default: admin123")

        # Load admin password from Streamlit secrets or environment variable for security
        try:
            secret_admin_pw = st.secrets.get("admin_password") if hasattr(st, 'secrets') else None
        except Exception:
            secret_admin_pw = None

        env_admin_pw = os.environ.get("ADMIN_PASSWORD")
        ADMIN_PASSWORD = secret_admin_pw or env_admin_pw or admin_password

        # Authenticate
        if password and password == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            st.success("✅ Access granted! Welcome to Admin Panel")

            st.markdown("---")

            # Admin download options
            st.markdown("### 📋 Feedback Report Management")

            # Get combined feedback data from all sources
            df = get_all_feedback_data()

            if df is not None and not df.empty:
                # Add TWO filter dropdowns
                st.markdown("#### 🔍 Filter Options")
                
                col_filter1, col_filter2 = st.columns(2)
                
                with col_filter1:
                    # Agent filter dropdown
                    agent_filter = st.selectbox(
                        "🤖 Select Agent:",
                        options=[
                            "All Agents",
                            "Vocabulary Agent",
                            "Current System Agent",
                            "Volatility Agent",
                            "Ambiguity Agent",
                            "Complexity Agent",
                            "Interconnectedness Agent",
                            "Uncertainty Agent",
                            "Hardness Agent"
                        ],
                        key="admin_agent_filter",
                        help="Filter feedback by specific agent"
                    )
                
                with col_filter2:
                    # Feedback type filter dropdown
                    feedback_type_filter = st.selectbox(
                        "📋 Select Feedback Type:",
                        options=[
                            "All Feedback Types",
                            "I have read it, found it useful, thanks.",
                            "I have read it, found some definitions to be off.",
                            "The widget seems interesting, but I have some suggestions on the features."
                        ],
                        key="admin_feedback_type_filter",
                        help="Filter by specific feedback type"
                    )

                # Apply BOTH filters
                filtered_df = df.copy()
                
                # Filter by Agent (if Agent column exists)
                if 'Agent' in df.columns:
                    if agent_filter != "All Agents":
                        filtered_df = filtered_df[filtered_df['Agent'] == agent_filter]
                else:
                    if agent_filter != "All Agents":
                        st.warning("⚠️ 'Agent' column not found in feedback data. Showing all agents.")
                
                # Filter by Feedback Type
                if feedback_type_filter != "All Feedback Types":
                    filtered_df = filtered_df[filtered_df['FeedbackType'] == feedback_type_filter]

                # Show count with filter summary
                filter_summary = []
                if agent_filter != "All Agents":
                    filter_summary.append(f"Agent: **{agent_filter}**")
                if feedback_type_filter != "All Feedback Types":
                    filter_summary.append(f"Type: **{feedback_type_filter[:50]}...**")
                
                if filter_summary:
                    st.info(f"📊 Showing **{len(filtered_df)}** of **{len(df)}** feedback entries | Filters: {' | '.join(filter_summary)}")
                else:
                    st.info(f"📊 Showing **{len(filtered_df)}** total feedback entries (no filters applied)")

                # Display filtered feedback data table
                if not filtered_df.empty:
                    st.markdown("#### 📋 Feedback Data")
                    st.dataframe(filtered_df, use_container_width=True, height=400)

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Download filtered feedback
                    feedback_csv = filtered_df.to_csv(index=False).encode("utf-8")
                    
                    # Create descriptive filename
                    agent_part = agent_filter.replace(' ', '_') if agent_filter != "All Agents" else "AllAgents"
                    type_part = feedback_type_filter.replace(' ', '_').replace('.', '').replace(',', '')[:30] if feedback_type_filter != "All Feedback Types" else "AllTypes"
                    download_filename = f"feedback_{agent_part}_{type_part}_{datetime.now().strftime('%Y%m%d')}.csv"

                    col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
                    with col_dl2:
                        st.download_button(
                            "⬇️ Download Filtered Feedback Report",
                            feedback_csv,
                            download_filename,
                            "text/csv",
                            use_container_width=True,
                            type="primary"
                        )
                else:
                    st.warning(f"⚠️ No feedback found matching your filters.")
                    st.info("💡 Try adjusting the filters to see more results.")
            else:
                st.info("📭 No feedback data available yet. Submit feedback from the main page to see it here.")

        elif password and password != "":
            st.session_state.admin_authenticated = False
            st.error("❌ Invalid password. Access denied.")
        else:
            st.info("💡 Please enter the admin password to access reports.")


