"""
utils/theme.py — Custom CSS injections for a premium Streamlit look.
"""

import streamlit as st

def apply_custom_theme():
    st.markdown("""
        <style>
        /* 1. Hide default Streamlit chrome */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="stSidebarNav"] {display: none !important;}

        /* 2. Modern Typography */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* 3. Hero header on login page */
        .hero-header {
            text-align: center;
            padding: 2.5rem 1rem 1.5rem;
        }
        .hero-logo {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 72px;
            height: 72px;
            border-radius: 20px;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            box-shadow: 0 8px 32px rgba(99, 102, 241, 0.35);
            margin-bottom: 1rem;
        }
        .hero-title {
            font-size: 2.2rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px;
            margin: 0 0 0.5rem !important;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .hero-sub {
            font-size: 1rem;
            color: #6b7280;
            margin: 0;
        }

        /* 4. Auth section padding */
        .auth-section {
            padding: 0.5rem 0;
        }

        /* 5. Primary Button — gradient + hover lift */
        .stButton > button[kind="primary"],
        .stFormSubmitButton > button {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
            color: #fff !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            padding: 0.65rem 1.5rem !important;
            transition: all 0.2s ease-in-out !important;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3) !important;
        }
        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.45) !important;
        }

        /* 6. Secondary / other buttons */
        .stButton > button {
            border-radius: 8px;
            transition: all 0.2s ease-in-out;
            font-weight: 500;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }

        /* 7. Form / Card Styling */
        [data-testid="stForm"] {
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
            background-color: var(--background-color);
        }

        /* 8. Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 1.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0.6rem 1.2rem;
            border-radius: 8px 8px 0 0;
            font-weight: 500;
        }

        /* 9. Metric values */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 700;
        }

        /* 10. Circular Profile Images */
        img.profile-img {
            border-radius: 50%;
            object-fit: cover;
            box-shadow: 0 8px 16px rgba(0,0,0,0.15);
            border: 4px solid #6366f1;
            width: 160px;
            height: 160px;
        }

        /* 11. Sidebar branding */
        section[data-testid="stSidebar"] .stMarkdown h2 {
            font-weight: 700;
            font-size: 1.1rem;
            letter-spacing: -0.3px;
        }
        </style>
    """, unsafe_allow_html=True)
