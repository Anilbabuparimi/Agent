import streamlit as st
from shared_header import (
    render_header, 
    render_unified_business_inputs,
    ACCOUNTS, 
    INDUSTRIES, 
    ACCOUNT_INDUSTRY_MAP,
    _safe_rerun
)
import os
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# --- Page Config ---
st.set_page_config(
    page_title="Business Problem Analysis Platform",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Session State Initialization ---
if 'page' not in st.session_state:
    st.session_state.page = "login"
if 'employee_id' not in st.session_state:
    st.session_state.employee_id = ""
if 'launched_agent' not in st.session_state:
    st.session_state.launched_agent = None
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False
if 'main_app_show_save_btn' not in st.session_state:
    st.session_state.main_app_show_save_btn = True
if 'saved_account' not in st.session_state:
    st.session_state.saved_account = "Select Account"
if 'saved_industry' not in st.session_state:
    st.session_state.saved_industry = "Select Industry"
if 'saved_problem' not in st.session_state:
    st.session_state.saved_problem = ""
if 'business_account' not in st.session_state:
    st.session_state.business_account = st.session_state.saved_account
if 'business_industry' not in st.session_state:
    st.session_state.business_industry = st.session_state.saved_industry
if 'business_problem' not in st.session_state:
    st.session_state.business_problem = st.session_state.saved_problem
if 'edit_confirmed' not in st.session_state:
    st.session_state.edit_confirmed = False
if 'cancel_clicked' not in st.session_state:
    st.session_state.cancel_clicked = False
if 'selectbox_key_counter' not in st.session_state:
    st.session_state.selectbox_key_counter = 0
if 'show_admin_panel' not in st.session_state:
    st.session_state.show_admin_panel = False
if 'admin_view_selected' not in st.session_state:
    st.session_state.admin_view_selected = False
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = ''
if 'admin_access_requested' not in st.session_state:
    st.session_state.admin_access_requested = False

# Feedback file configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

try:
    if not os.path.exists(FEEDBACK_FILE):
        df = pd.DataFrame(columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType",
                          "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement", "Agent"])
        df.to_csv(FEEDBACK_FILE, index=False)
except (PermissionError, OSError) as e:
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = pd.DataFrame(
            columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType", "OffDefinitions", 
                    "Suggestions", "Account", "Industry", "ProblemStatement", "Agent"])

# Admin panel URL parameter handling
try:
    qparams = st.query_params
    if 'adminPanelToggled' in qparams:
        param_value = qparams.get('adminPanelToggled')
        if isinstance(param_value, list):
            param_value = param_value[0] if param_value else ''
        
        v = str(param_value).lower()
        if v in ('1', 't', 'true', 'show', 'yes'):
            st.session_state.current_page = 'admin'
            st.session_state.show_admin_panel = True
            st.session_state.admin_view_selected = True
            st.session_state.page = "admin"
        
        components.html("""
            <script>
            (function(){
                try {
                    const url = new URL(window.location.href);
                    url.searchParams.delete('adminPanelToggled');
                    history.replaceState(null, '', url.pathname + url.search + url.hash);
                } catch(e) {}
            })();
            </script>
        """, height=0)
except Exception:
    pass


def render_login_page():
    """Fixed login page with proper vertical stacking"""
    
    render_header(
        agent_name="Business Problem Analysis Platform",
        agent_subtitle="AI-powered agents for strategic business insights",
        enable_admin_access=True,
        header_height=100
    )

    # 🔥 FIXED CSS - Removed fixed positioning, proper vertical flow
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Poppins', sans-serif !important;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Floating Particles */
    .particles {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        z-index: 0;
        pointer-events: none;
    }
    
    .particle {
        position: absolute;
        width: 4px;
        height: 4px;
        background: rgba(255, 107, 53, 0.6);
        border-radius: 50%;
        animation: float 20s infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0) translateX(0); opacity: 0; }
        10% { opacity: 1; }
        90% { opacity: 1; }
        100% { transform: translateY(-100vh) translateX(50px); opacity: 0; }
    }
    
    /* FIXED: Remove fixed positioning, use normal flow */
    .block-container {
        padding-top: 2rem !important;
        max-width: 600px !important;
        margin: 0 auto !important;
    }
    
    /* Welcome Card - Normal document flow */
    .welcome-card-static {
        position: relative;
        width: 100%;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(30px) saturate(180%);
        border: 2px solid rgba(255, 255, 255, 0.2);
        border-radius: 25px;
        padding: 3.5rem 3rem;
        box-shadow: 
            0 25px 80px rgba(0, 0, 0, 0.4),
            0 0 60px rgba(255, 107, 53, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        margin-bottom: 2.5rem;
    }
    
    [data-theme="dark"] .welcome-card-static {
        background: rgba(20, 20, 30, 0.3);
        border: 2px solid rgba(255, 107, 53, 0.4);
    }
    
    /* Static Border - NO ANIMATION */
    .welcome-card-static::before {
        content: '';
        position: absolute;
        inset: -2px;
        border-radius: 25px;
        background: linear-gradient(45deg, #ff6b35, #8b1e1e);
        z-index: -1;
        opacity: 0.6;
        filter: blur(8px);
    }
    
    /* Static Title */
    .static-title {
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        color: #ffffff;
        margin: 0 0 0.8rem 0;
        letter-spacing: -1px;
    }
    
    [data-theme="dark"] .static-title {
        color: #ffffff;
    }
    
    .static-subtitle {
        text-align: center;
        color: rgba(255, 255, 255, 0.85);
        font-size: 1.3rem;
        font-weight: 500;
        margin: 0;
    }
    
    [data-theme="dark"] .static-subtitle {
        color: rgba(255, 255, 255, 0.8);
    }
    
    /* Input Styling */
    .stTextInput label {
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 0.4rem !important;
    }
    
    [data-theme="dark"] .stTextInput label {
        color: rgba(255, 255, 255, 0.9) !important;
    }
    
    .stTextInput input {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 2px solid rgba(255, 107, 53, 0.4) !important;
        border-radius: 12px !important;
        color: white !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        padding: 0.65rem 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.3);
        height: 45px !important;
    }
    
    [data-theme="dark"] .stTextInput input {
        background: rgba(10, 10, 20, 0.4) !important;
        border: 2px solid rgba(255, 107, 53, 0.5) !important;
    }
    
    .stTextInput input:focus {
        background: rgba(255, 255, 255, 0.15) !important;
        border-color: #ff6b35 !important;
        box-shadow: 
            inset 0 2px 8px rgba(0, 0, 0, 0.3),
            0 0 20px rgba(255, 107, 53, 0.5) !important;
        transform: scale(1.01);
    }
    
    .stTextInput input::placeholder {
        color: rgba(255, 255, 255, 0.5) !important;
    }
    
    /* Button Styling */
    .stButton > button {
        position: relative;
        background: linear-gradient(135deg, #ff6b35 0%, #8b1e1e 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.8rem 2rem !important;
        width: 100% !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        text-transform: uppercase;
        letter-spacing: 2.5px;
        overflow: hidden;
        box-shadow: 
            0 8px 30px rgba(255, 107, 53, 0.5),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        transition: all 0.3s ease !important;
        margin-top: 1rem !important;
        height: 50px !important;
    }
    
    [data-theme="dark"] .stButton > button {
        background: linear-gradient(135deg, #ff6b35 0%, #8b1e1e 100%) !important;
        box-shadow: 
            0 8px 30px rgba(255, 107, 53, 0.6),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow: 
            0 12px 40px rgba(255, 107, 53, 0.7),
            0 0 40px rgba(255, 107, 53, 0.5) !important;
    }
    
    .stButton > button:hover::before {
        width: 300px;
        height: 300px;
    }
    
    .stButton > button:active {
        transform: translateY(-1px) scale(0.99) !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Error message styling */
    .stAlert {
        background: rgba(255, 50, 50, 0.2) !important;
        backdrop-filter: blur(15px) !important;
        border: 2px solid rgba(255, 50, 50, 0.5) !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        padding: 0.8rem !important;
    }
    
    /* Input container spacing */
    .stTextInput {
        margin-bottom: 0.8rem !important;
    }
    </style>
    
    <!-- Particle System -->
    <div class="particles">
        <div class="particle" style="left: 10%; animation-delay: 0s;"></div>
        <div class="particle" style="left: 20%; animation-delay: 2s;"></div>
        <div class="particle" style="left: 30%; animation-delay: 4s;"></div>
        <div class="particle" style="left: 40%; animation-delay: 1s;"></div>
        <div class="particle" style="left: 50%; animation-delay: 3s;"></div>
        <div class="particle" style="left: 60%; animation-delay: 5s;"></div>
        <div class="particle" style="left: 70%; animation-delay: 2.5s;"></div>
        <div class="particle" style="left: 80%; animation-delay: 4.5s;"></div>
        <div class="particle" style="left: 90%; animation-delay: 1.5s;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Welcome Card in normal flow
    st.markdown("""
    <div class="welcome-card-static">
        <h1 class="static-title">Welcome</h1>
        <p class="static-subtitle">🚀 Enter the AI-Powered Future</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inputs naturally stacked below
    employee_id = st.text_input(
        "Employee ID",
        placeholder="Your ID",
        key="employee_id_input",
        label_visibility="visible"
    )
    
    if st.button("🚀 LAUNCH", use_container_width=True, key="login_btn"):
        if employee_id:
            st.session_state.employee_id = employee_id
            st.session_state.page = "main_app"
            st.session_state.main_app_show_save_btn = True
            st.rerun()
        else:
            st.error("⚠️ Please enter your Employee ID")


def render_main_app():
    """MAIN APP with agent navigation"""
    
    if st.session_state.get('show_admin_panel') and not st.session_state.get('admin_view_selected'):
        _render_admin_confirmation()
        return
    
    if st.session_state.get('admin_view_selected'):
        _render_admin_panel()
        return

    # CSS for main app (keeping your existing styles)
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');
        
        * {
            font-family: 'Poppins', sans-serif !important;
        }
        
        /* Mesh Gradient Background */
        .main {
            background: 
                radial-gradient(at 0% 0%, rgba(139, 30, 30, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(255, 107, 53, 0.1) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 30, 30, 0.1) 0px, transparent 50%),
                radial-gradient(at 0% 100%, rgba(255, 107, 53, 0.15) 0px, transparent 50%);
            animation: meshMove 20s ease-in-out infinite;
        }
        
        @keyframes meshMove {
            0%, 100% { background-position: 0% 0%, 100% 0%, 100% 100%, 0% 100%; }
            50% { background-position: 100% 100%, 0% 100%, 0% 0%, 100% 0%; }
        }
        
        [data-theme="dark"] .main {
            background: 
                radial-gradient(at 0% 0%, rgba(139, 30, 30, 0.25) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(255, 107, 53, 0.2) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 30, 30, 0.2) 0px, transparent 50%),
                radial-gradient(at 0% 100%, rgba(255, 107, 53, 0.25) 0px, transparent 50%),
                #0a0a0f;
        }
        
        /* Hero Banner */
        .hero-banner {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 20px;
            padding: 1.5rem 2rem;
            margin: 1.5rem auto 2rem auto;
            max-width: 1200px;
            box-shadow: 
                0 15px 40px rgba(139, 30, 30, 0.15),
                inset 0 1px 0 rgba(255, 255, 255, 0.8);
            position: relative;
            overflow: hidden;
            animation: bannerFloat 4s ease-in-out infinite;
        }
        
        @keyframes bannerFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-5px); }
        }
        
        .hero-banner::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
            animation: shine 3s infinite;
        }
        
        @keyframes shine {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        [data-theme="dark"] .hero-banner {
            background: rgba(20, 20, 30, 0.7);
            border: 1px solid rgba(255, 107, 53, 0.3);
            box-shadow: 
                0 15px 40px rgba(0, 0, 0, 0.4),
                0 0 30px rgba(255, 107, 53, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }
        
        .hero-banner h2 {
            text-align: center;
            font-size: 2rem;
            font-weight: 900;
            margin: 0 0 0.8rem 0;
            background: linear-gradient(135deg, #8b1e1e, #ff6b35, #8b1e1e);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientText 3s linear infinite;
            letter-spacing: -1px;
        }
        
        @keyframes gradientText {
            0%, 100% { background-position: 0% center; }
            50% { background-position: 100% center; }
        }
        
        .hero-banner p {
            text-align: center;
            color: #64748b;
            font-size: 1rem;
            font-weight: 500;
            margin: 0;
            position: relative;
            z-index: 1;
        }
        
        [data-theme="dark"] .hero-banner p {
            color: #cbd5e1;
        }
        
        /* Section Headers */
        .section-header-magnetic {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(248, 250, 252, 0.9));
            backdrop-filter: blur(15px);
            border: 2px solid transparent;
            background-clip: padding-box;
            border-radius: 15px;
            padding: 1.5rem 2rem;
            margin: 2rem 0 1.5rem 0;
            position: relative;
            box-shadow: 
                0 8px 25px rgba(139, 30, 30, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.9);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
        }
        
        .section-header-magnetic::before {
            content: '';
            position: absolute;
            inset: -2px;
            border-radius: 15px;
            background: linear-gradient(135deg, #ff6b35, #8b1e1e, #ff6b35);
            background-size: 200% 200%;
            animation: borderRotate 4s linear infinite;
            z-index: -1;
            opacity: 0;
            transition: opacity 0.4s;
        }
        
        .section-header-magnetic:hover::before {
            opacity: 1;
        }
        
        @keyframes borderRotate {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .section-header-magnetic:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 
                0 15px 40px rgba(139, 30, 30, 0.2),
                0 0 30px rgba(255, 107, 53, 0.3);
        }
        
        .section-header-magnetic h3 {
            color: #1e293b;
            font-size: 1.5rem;
            font-weight: 800;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.8rem;
            letter-spacing: -0.5px;
        }
        
        [data-theme="dark"] .section-header-magnetic {
            background: linear-gradient(135deg, rgba(30, 30, 40, 0.9), rgba(20, 20, 30, 0.9));
            box-shadow: 
                0 8px 25px rgba(0, 0, 0, 0.4),
                0 0 20px rgba(255, 107, 53, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }
        
        [data-theme="dark"] .section-header-magnetic h3 {
            color: #f1f5f9;
        }
        
        /* Enhanced Agent Buttons */
        .stButton > button[kind="secondary"] {
            position: relative;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
            color: #1e293b !important;
            border: 2px solid rgba(255, 107, 53, 0.3) !important;
            border-radius: 20px !important;
            padding: 1.5rem 1rem !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            box-shadow: 
                0 8px 20px rgba(0, 0, 0, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.8) !important;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
            overflow: hidden;
            height: auto !important;
            min-height: 90px !important;
        }
        
        .stButton > button[kind="secondary"]::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255, 107, 53, 0.4), transparent);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }
        
        .stButton > button[kind="secondary"]:hover::before {
            width: 300px;
            height: 300px;
        }
        
        .stButton > button[kind="secondary"]:hover:not(:disabled) {
            transform: translateY(-5px) scale(1.03) rotateZ(-1deg) !important;
            box-shadow: 
                0 15px 40px rgba(139, 30, 30, 0.3),
                0 0 35px rgba(255, 107, 53, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.9) !important;
            border-color: #ff6b35 !important;
            background: linear-gradient(135deg, #8b1e1e 0%, #ff6b35 100%) !important;
            color: white !important;
        }
        
        .stButton > button[kind="secondary"]:active:not(:disabled) {
            transform: translateY(-3px) scale(1.01) !important;
        }
        
        [data-theme="dark"] .stButton > button[kind="secondary"] {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.8)) !important;
            color: #f1f5f9 !important;
            border: 2px solid rgba(255, 107, 53, 0.4) !important;
            box-shadow: 
                0 8px 20px rgba(0, 0, 0, 0.4),
                0 0 15px rgba(255, 107, 53, 0.2) !important;
        }
        
        /* Neon Active Agent Box */
        .active-agent-neon {
            background: linear-gradient(135deg, rgba(139, 30, 30, 0.15), rgba(255, 107, 53, 0.1));
            backdrop-filter: blur(15px);
            border: 2px solid transparent;
            border-radius: 20px;
            padding: 1.5rem;
            margin: 2rem 0;
            position: relative;
            overflow: hidden;
            animation: neonPulse 3s ease-in-out infinite;
        }
        
        .active-agent-neon::before {
            content: '';
            position: absolute;
            inset: -2px;
            border-radius: 20px;
            background: linear-gradient(45deg, #ff6b35, #8b1e1e, #ff6b35);
            background-size: 300% 300%;
            animation: neonBorder 3s linear infinite;
            z-index: -1;
        }
        
        @keyframes neonPulse {
            0%, 100% { box-shadow: 0 0 15px rgba(255, 107, 53, 0.3); }
            50% { box-shadow: 0 0 25px rgba(255, 107, 53, 0.6), 0 0 40px rgba(139, 30, 30, 0.4); }
        }
        
        @keyframes neonBorder {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .active-agent-neon .title {
            color: #8b1e1e;
            font-weight: 800;
            font-size: 1.2rem;
            margin: 0 0 0.5rem 0;
            text-shadow: 0 0 8px rgba(139, 30, 30, 0.3);
        }
        
        [data-theme="dark"] .active-agent-neon {
            background: linear-gradient(135deg, rgba(139, 30, 30, 0.3), rgba(255, 107, 53, 0.2));
        }
        
        [data-theme="dark"] .active-agent-neon .title {
            color: #ff6b35;
            text-shadow: 0 0 12px rgba(255, 107, 53, 0.5);
        }
        
        /* Cosmic Primary Buttons */
        .stButton > button[kind="primary"] {
            position: relative;
            background: linear-gradient(135deg, #8b1e1e 0%, #ff6b35 50%, #8b1e1e 100%) !important;
            background-size: 200% auto;
            animation: cosmicShift 3s linear infinite;
            border: none !important;
            border-radius: 15px !important;
            padding: 1rem 2rem !important;
            font-weight: 800 !important;
            font-size: 1rem !important;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: white !important;
            box-shadow: 
                0 8px 25px rgba(139, 30, 30, 0.5),
                0 0 20px rgba(255, 107, 53, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
            transition: all 0.3s ease !important;
            overflow: hidden;
            height: 50px !important;
        }
        
        @keyframes cosmicShift {
            0%, 100% { background-position: 0% center; }
            50% { background-position: 100% center; }
        }
        
        .stButton > button[kind="primary"]::after {
            content: '✨';
            position: absolute;
            top: 50%;
            left: -50px;
            transform: translateY(-50%);
            font-size: 1.2rem;
            animation: sparkleMove 2s ease-in-out infinite;
        }
        
        @keyframes sparkleMove {
            0% { left: -50px; opacity: 0; }
            50% { opacity: 1; }
            100% { left: calc(100% + 50px); opacity: 0; }
        }
        
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-5px) scale(1.03) !important;
            box-shadow: 
                0 15px 40px rgba(139, 30, 30, 0.6),
                0 0 35px rgba(255, 107, 53, 0.6) !important;
        }
        
        /* Holographic Dividers */
        hr {
            margin: 2.5rem 0 !important;
            border: none !important;
            height: 1px !important;
            background: linear-gradient(90deg, transparent, #ff6b35, #8b1e1e, #ff6b35, transparent) !important;
            background-size: 200% 100%;
            animation: holoDivider 3s linear infinite;
        }
        
        @keyframes holoDivider {
            0%, 100% { background-position: 0% center; }
            50% { background-position: 100% center; }
        }
        
        /* Info Alert */
        .stAlert {
            background: rgba(255, 255, 255, 0.8) !important;
            backdrop-filter: blur(15px) !important;
            border: 1px solid rgba(255, 107, 53, 0.3) !important;
            border-radius: 12px !important;
            border-left: 4px solid #ff6b35 !important;
            box-shadow: 0 6px 20px rgba(139, 30, 30, 0.15) !important;
            font-weight: 600 !important;
            animation: alertGlow 2s ease-in-out infinite;
            padding: 0.8rem !important;
        }
        
        @keyframes alertGlow {
            0%, 100% { box-shadow: 0 6px 20px rgba(139, 30, 30, 0.15); }
            50% { box-shadow: 0 6px 25px rgba(255, 107, 53, 0.3); }
        }
        
        [data-theme="dark"] .stAlert {
            background: rgba(30, 30, 40, 0.8) !important;
            border: 1px solid rgba(255, 107, 53, 0.4) !important;
        }
        
        /* Smooth Page Load Animation */
        .main > .block-container {
            animation: pageLoad 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        @keyframes pageLoad {
            0% {
                opacity: 0;
                transform: translateY(30px) scale(0.98);
            }
            100% {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        
        /* Responsive Grid Gap */
        .row-widget.stHorizontal {
            gap: 1.5rem !important;
        }
        
        /* Hide default elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

    render_header(
        agent_name="Business Problem Analysis Platform",
        agent_subtitle="",
        enable_admin_access=True,
        header_height=85
    )

    # Hero Banner
    st.markdown("""
    <div class="hero-banner">
        <h2>🧠 AI-Powered Intelligence</h2>
        <p>Unleash specialized agents to decode your business challenges</p>
    </div>
    """, unsafe_allow_html=True)

    account, industry, problem = render_unified_business_inputs(
        page_key_prefix="main_app",
        show_titles=True,
        title_account_industry="Account & Industry",
        title_problem="Business Problem Description",
        save_button_label="Save Problem Details"
    )

    st.markdown("---")
    
    st.markdown("""
    <div class="section-header-magnetic">
        <h3>🤖 AI Agent Arsenal</h3>
    </div>
    """, unsafe_allow_html=True)

    # 🔥 FIXED: Correct page paths for Streamlit Cloud
    agents = [
        {"name": "Vocabulary Agent", "icon": "📚", "page": "pages/1__Vocabulary_Agent.py", "desc": "Decode industry terminology"},
        {"name": "Current System Agent", "icon": "⚙️", "page": "pages/2__Current_System_Agent.py", "desc": "Analyze existing systems"},
        {"name": "Volatility Agent", "icon": "📈", "page": "pages/3__Volatility_Agent.py", "desc": "Track market dynamics"},
        {"name": "Ambiguity Agent", "icon": "🔍", "page": "pages/4__Ambiguity_Agent.py", "desc": "Clarify uncertainties"},
        {"name": "Interconnectedness Agent", "icon": "🔗", "page": "pages/5__Interconnectedness_Agent.py", "desc": "Map relationships"},
        {"name": "Uncertainty Agent", "icon": "⚠️", "page": "pages/6__Uncertainty_Agent.py", "desc": "Quantify risks"},
        {"name": "Hardness Summary Agent", "icon": "📊", "page": "pages/7__Hardness_Summary_Agent.py", "desc": "Assess complexity"},
    ]

    if st.session_state.launched_agent:
        active_agent = next((agent for agent in agents if agent["page"] == st.session_state.launched_agent), None)
        if active_agent:
            st.markdown(f"""
            <div class="active-agent-neon">
                <p class="title">🎯 Active: {active_agent['icon']} {active_agent['name']}</p>
                <p style="color: #64748b; font-weight: 500; margin: 0;">Currently deployed • {active_agent['desc']}</p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button(f"↩️ Return to {active_agent['icon']} {active_agent['name']}", use_container_width=True, type="primary"):
                    try:
                        st.switch_page(active_agent["page"])
                    except Exception as e:
                        st.error(f"Navigation error: {str(e)}")
                        st.info(f"Expected page: {active_agent['page']}")

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    # Agent grid - First 6 agents in 2 rows
    for row in range(2):
        cols = st.columns(3)
        for col_idx in range(3):
            agent_idx = row * 3 + col_idx
            if agent_idx < 6:
                agent = agents[agent_idx]
                with cols[col_idx]:
                    is_disabled = (st.session_state.launched_agent is not None and 
                                 st.session_state.launched_agent != agent["page"])
                    if st.button(f"{agent['icon']} {agent['name']}", 
                               use_container_width=True, 
                               disabled=is_disabled, 
                               type="secondary", 
                               key=f"agent_{agent_idx}",
                               help=agent['desc']):
                        if st.session_state.saved_problem:
                            st.session_state.launched_agent = agent["page"]
                            try:
                                st.switch_page(agent["page"])
                            except Exception as e:
                                st.error(f"❌ Cannot navigate to {agent['name']}")
                                st.info(f"Looking for: {agent['page']}")
                                st.info(f"Make sure file exists at: {os.path.join(os.getcwd(), agent['page'])}")
                        else:
                            st.warning("⚠️ Please save your business problem details first")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # 7th agent centered
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        agent = agents[6]
        is_disabled = (st.session_state.launched_agent is not None and 
                     st.session_state.launched_agent != agent["page"])
        if st.button(f"{agent['icon']} {agent['name']}", 
                   use_container_width=True, 
                   disabled=is_disabled, 
                   type="secondary", 
                   key=f"agent_6",
                   help=agent['desc']):
            if st.session_state.saved_problem:
                st.session_state.launched_agent = agent["page"]
                try:
                    st.switch_page(agent["page"])
                except Exception as e:
                    st.error(f"❌ Cannot navigate to {agent['name']}")
                    st.info(f"Looking for: {agent['page']}")
                    st.info(f"Make sure file exists at: {os.path.join(os.getcwd(), agent['page'])}")
            else:
                st.warning("⚠️ Please save your business problem details first")

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚪 Logout & Reset", use_container_width=True, type="primary"):
            st.session_state.launched_agent = None
            st.session_state.edit_confirmed = False
            st.balloons()
            st.success("✅ Session reset successfully!")
            st.rerun()


def _render_admin_confirmation():
    """Admin confirmation page"""
    render_header(
        agent_name="Admin Access Required",
        agent_subtitle="Secure authentication required",
        enable_admin_access=True,
        header_height=85
    )
    
    st.markdown("""
    <style>
        .admin-confirm-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 50vh;
        }
        
        .admin-confirm-card {
            max-width: 500px;
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(25px) saturate(180%);
            border: 2px solid rgba(139, 30, 30, 0.2);
            border-radius: 25px;
            padding: 2.5rem 2.5rem;
            box-shadow: 
                0 20px 60px rgba(0, 0, 0, 0.15),
                0 0 40px rgba(255, 107, 53, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.9);
            position: relative;
            overflow: hidden;
            animation: confirmEntrance 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        @keyframes confirmEntrance {
            0% {
                opacity: 0;
                transform: scale(0.9) translateY(30px);
            }
            100% {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }
        
        .admin-confirm-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #8b1e1e, #ff6b35, #8b1e1e);
            background-size: 200% 100%;
            animation: borderFlow 3s linear infinite;
        }
        
        @keyframes borderFlow {
            0%, 100% { background-position: 0% center; }
            50% { background-position: 100% center; }
        }
        
        .admin-confirm-card h2 {
            font-size: 2rem;
            font-weight: 900;
            text-align: center;
            margin: 0 0 0.8rem 0;
            background: linear-gradient(135deg, #8b1e1e, #ff6b35);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .admin-confirm-card p {
            text-align: center;
            color: #64748b;
            font-size: 1rem;
            font-weight: 500;
            margin: 0;
        }
        
        [data-theme="dark"] .admin-confirm-card {
            background: rgba(20, 20, 30, 0.8);
            border: 2px solid rgba(255, 107, 53, 0.3);
            box-shadow: 
                0 20px 60px rgba(0, 0, 0, 0.4),
                0 0 40px rgba(255, 107, 53, 0.3);
        }
        
        [data-theme="dark"] .admin-confirm-card p {
            color: #cbd5e1;
        }
    </style>
    
    <div class="admin-confirm-container">
        <div class="admin-confirm-card">
            <h2>🔐 Admin Portal</h2>
            <p>Restricted area • Authentication required</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔓 Authenticate", key="open_admin_view_btn", use_container_width=True, type="primary"):
            st.session_state.admin_view_selected = True
            st.session_state.current_page = 'admin'
            st.session_state.page = 'admin'
            st.rerun()
        
        st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
        
        if st.button("❌ Cancel", key="cancel_admin_view_btn", use_container_width=True):
            st.session_state.show_admin_panel = False
            st.session_state.admin_view_selected = False
            st.session_state.current_page = ''
            st.session_state.page = 'login'
            st.rerun()


def _render_admin_panel():
    """Admin panel with dashboard"""
    render_header(
        agent_name="Admin Dashboard",
        agent_subtitle="Analytics & Feedback Management",
        enable_admin_access=True,
        header_height=85
    )
    
    st.markdown("""
    <style>
        .admin-dash-header {
            background: linear-gradient(135deg, #8b1e1e 0%, #6b1515 50%, #ff6b35 100%);
            padding: 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            box-shadow: 
                0 12px 40px rgba(139, 30, 30, 0.4),
                0 0 40px rgba(255, 107, 53, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        .admin-dash-header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,107,53,0.3), transparent 70%);
            animation: dashRotate 10s linear infinite;
        }
        
        @keyframes dashRotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .admin-dash-header h2 {
            color: white;
            font-size: 2rem;
            font-weight: 900;
            text-align: center;
            margin: 0;
            position: relative;
            z-index: 1;
            text-shadow: 0 3px 15px rgba(0, 0, 0, 0.3);
        }
        
        .admin-card {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(15px);
            border: 2px solid rgba(139, 30, 30, 0.15);
            border-radius: 15px;
            padding: 2rem;
            margin: 1.5rem 0;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        
        .admin-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 35px rgba(139, 30, 30, 0.2);
        }
        
        [data-theme="dark"] .admin-card {
            background: rgba(30, 41, 59, 0.8);
            border: 2px solid rgba(255, 107, 53, 0.25);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
        }
        
        .admin-card h3 {
            color: #1e293b;
            font-size: 1.5rem;
            font-weight: 800;
            margin: 0 0 1rem 0;
        }
        
        [data-theme="dark"] .admin-card h3 {
            color: #f1f5f9;
        }
        
        .stat-metric {
            background: linear-gradient(135deg, rgba(255,107,53,0.1), rgba(139,30,30,0.1));
            border: 2px solid rgba(255,107,53,0.2);
            border-radius: 12px;
            padding: 1.5rem 1rem;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .stat-metric:hover {
            transform: scale(1.03) translateY(-3px);
            box-shadow: 0 8px 25px rgba(255,107,53,0.3);
            border-color: #ff6b35;
        }
        
        [data-theme="dark"] .stat-metric {
            background: linear-gradient(135deg, rgba(255,107,53,0.2), rgba(139,30,30,0.2));
            border: 2px solid rgba(255,107,53,0.3);
        }
    </style>
    
    <div class="admin-dash-header">
        <h2>🎛️ Control Center</h2>
    </div>
    """, unsafe_allow_html=True)

    col_back1, col_back2, col_back3 = st.columns([1, 2, 1])
    with col_back1:
        if st.button("← Back", key="admin_back_btn", use_container_width=True):
            st.session_state.show_admin_panel = False
            st.session_state.admin_view_selected = False
            st.session_state.admin_authenticated = False
            st.session_state.current_page = ''
            st.rerun()

    st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
    st.markdown("<h3>🔐 Authentication</h3>", unsafe_allow_html=True)
    
    if not st.session_state.admin_access_requested:
        st.info("💡 Secure access required")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn2:
            if st.button("🔓 Request Access", use_container_width=True, type="primary"):
                st.session_state.admin_access_requested = True
                st.rerun()
    else:
        password = st.text_input("Admin Password:",
                                type="password",
                                key="admin_password",
                                placeholder="Enter password")

        ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
        
        if password and password == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            st.success("✅ Access Granted")
            st.markdown("</div>", unsafe_allow_html=True)
            _render_admin_dashboard()
        elif password and password != "":
            st.session_state.admin_authenticated = False
            st.error("❌ Access Denied")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("🔑 Enter credentials")
            st.markdown("</div>", unsafe_allow_html=True)


def _render_admin_dashboard():
    """Render feedback dashboard"""
    
    st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
    st.markdown("<h3>📋 Feedback Analytics</h3>", unsafe_allow_html=True)
    
    st.markdown("#### 🔍 Filters")
    
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        agent_filter = st.selectbox(
            "🤖 Agent:",
            options=[
                "All Agents",
                "Vocabulary Agent",
                "Current System Agent",
                "Volatility Agent",
                "Ambiguity Agent",
                "Interconnectedness Agent",
                "Uncertainty Agent",
                "Hardness Summary Agent"
            ],
            key="admin_agent_filter"
        )
    
    with col_filter2:
        feedback_type_filter = st.selectbox(
            "📋 Type:",
            options=[
                "All Feedback Types",
                "I have read it, found it useful, thanks.",
                "I have read it, found some definitions to be off.",
                "The widget seems interesting, but I have some suggestions on the features."
            ],
            key="admin_feedback_type_filter"
        )

    df = None
    if os.path.exists(FEEDBACK_FILE):
        try:
            df = pd.read_csv(FEEDBACK_FILE)
        except Exception as e:
            st.warning(f"⚠️ Error: {e}")
            df = None

    if df is None or df.empty:
        if 'feedback_data' in st.session_state and not st.session_state.feedback_data.empty:
            df = st.session_state.feedback_data.copy()
            st.info("📊 Session data (cloud mode)")
        else:
            df = None

    if df is not None and not df.empty:
        filtered_df = df.copy()
        
        if 'Agent' in df.columns and agent_filter != "All Agents":
            filtered_df = filtered_df[filtered_df['Agent'] == agent_filter]
        
        if feedback_type_filter != "All Feedback Types":
            filtered_df = filtered_df[filtered_df['FeedbackType'] == feedback_type_filter]

        st.info(f"📊 Showing **{len(filtered_df)}** of **{len(df)}** entries")

        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True, height=350)

            feedback_csv = filtered_df.to_csv(index=False).encode("utf-8")
            
            agent_part = agent_filter.replace(' ', '_') if agent_filter != "All Agents" else "AllAgents"
            download_filename = f"feedback_{agent_part}_{datetime.now().strftime('%Y%m%d')}.csv"

            col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
            with col_dl2:
                st.download_button(
                    "⬇️ Download Report",
                    feedback_csv,
                    download_filename,
                    "text/csv",
                    use_container_width=True,
                    type="primary"
                )
        else:
            st.warning("⚠️ No matching feedback")
    else:
        st.info("💡 No feedback data available")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
    
    if df is not None and not df.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<div class='stat-metric'>", unsafe_allow_html=True)
            st.metric("📊 Total", len(df))
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='stat-metric'>", unsafe_allow_html=True)
            if 'Agent' in df.columns:
                st.metric("🤖 Agents", df['Agent'].nunique())
            else:
                st.metric("🤖 Agents", "N/A")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='stat-metric'>", unsafe_allow_html=True)
            if 'Timestamp' in df.columns:
                try:
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    current_month = datetime.now().month
                    current_year = datetime.now().year
                    this_month = len(df[(df['Timestamp'].dt.month == current_month) & 
                                       (df['Timestamp'].dt.year == current_year)])
                    st.metric("📅 This Month", this_month)
                except:
                    st.metric("📅 This Month", "N/A")
            else:
                st.metric("📅 This Month", "N/A")
            st.markdown("</div>", unsafe_allow_html=True)

    
    st.markdown("</div>", unsafe_allow_html=True)


# --- PAGE ROUTER ---
if st.session_state.get('page') == 'admin' or st.session_state.get('admin_view_selected'):
    _render_admin_panel()
elif st.session_state.get('show_admin_panel') and not st.session_state.get('admin_view_selected'):
    _render_admin_confirmation()
elif st.session_state.page == "login":
    render_login_page()
elif st.session_state.page == "main_app":
    render_main_app()
else:
    render_login_page()
