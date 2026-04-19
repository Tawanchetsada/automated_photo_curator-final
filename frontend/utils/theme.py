"""
utils/theme.py — Custom CSS injections for a premium Streamlit look.
"""

import streamlit as st

def apply_custom_theme():
    st.markdown("""
        <style>
        /* 1. Hide default Streamlit Menus for App-like feel */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="stSidebarNav"] {display: none !important;}

        /* 2. Modern Typography */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* 3. Primary Button Hover Effects */
        .stButton>button {
            border-radius: 8px;
            transition: all 0.2s ease-in-out;
            font-weight: 500;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        /* 4. Form / Card Styling */
        [data-testid="stForm"] {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            background-color: var(--background-color);
        }
        
        /* 5. Circular Profile Images */
        img.profile-img {
            border-radius: 50%;
            object-fit: cover;
            box-shadow: 0 8px 16px rgba(0,0,0,0.15);
            border: 4px solid var(--primary-color, #ff4b4b);
            width: 160px;
            height: 160px;
        }

        /* 6. Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding-right: 1rem;
            padding-left: 1rem;
            border-radius: 8px 8px 0px 0px;
        }

        /* 7. Metric Containers */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 700;
        }
        </style>
    """, unsafe_allow_html=True)
