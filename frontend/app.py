"""
app.py — Streamlit entry point for Automated Photo Curator.

Routing logic
─────────────
• Not logged in  → show Login / Register tabs on the home page.
• Logged in      → show sidebar navigation; home page shows quick-links.

st.set_page_config is called ONLY here (required by Streamlit multipage apps).
"""

import streamlit as st

from utils.api_client import ApiClient
from utils.theme import apply_custom_theme

st.set_page_config(
    page_title="Photo Curator",
    page_icon="camera",
    layout="centered",
    initial_sidebar_state="expanded",
)

apply_custom_theme()

client = ApiClient()


# ── Sidebar (rendered on every page via app.py) ───────────────────────────────
with st.sidebar:
    st.markdown("## Photo Curator")
    st.markdown("---")
    if st.session_state.get("token"):
        st.success("Logged in")
        st.page_link("pages/2_dashboard.py", label="Dashboard")
        st.page_link("pages/3_profile.py",   label="Profile")
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    else:
        st.info("Please log in to continue.")


# ── Helper actions ────────────────────────────────────────────────────────────
def _do_login(username: str, password: str) -> None:
    try:
        with st.spinner("Logging in…"):
            token = client.login(username, password)
        st.session_state["token"] = token
        st.switch_page("pages/2_dashboard.py")
    except Exception as exc:
        st.error(f"Login failed: {exc}")


def _do_register(
    username: str, email: str, password: str, selfie_file
) -> None:
    try:
        with st.spinner("Creating account…"):
            client.register(username, email, password, selfie_file)
        with st.spinner("Logging in…"):
            token = client.login(username, password)
        st.session_state["token"] = token
        st.switch_page("pages/2_dashboard.py")
    except Exception as exc:
        st.error(f"Registration failed: {exc}")


# ── Main content ──────────────────────────────────────────────────────────────
if not st.session_state.get("token"):
    # ── Hero header ───────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="hero-header">
            <div class="hero-logo">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none"
                     xmlns="http://www.w3.org/2000/svg">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0
                           0 1 2 2z" stroke="white" stroke-width="2" stroke-linecap="round"
                           stroke-linejoin="round"/>
                  <circle cx="12" cy="13" r="4" stroke="white" stroke-width="2"/>
                </svg>
            </div>
            <h1 class="hero-title">Photo Curator</h1>
            <p class="hero-sub">Upload your event photos and let AI find every shot featuring <strong>you</strong>.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Auth card ─────────────────────────────────────────────────────────────
    _, col_card, _ = st.columns([1, 10, 1])
    with col_card:
        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        # ── Login tab ─────────────────────────────────────────────────────────
        with tab_login:
            st.markdown("<div class='auth-section'>", unsafe_allow_html=True)
            with st.form("login_form"):
                st.markdown("#### Welcome back")
                username = st.text_input("Username", placeholder="your_username", label_visibility="collapsed")
                st.caption("Username")
                password = st.text_input("Password", type="password", placeholder="••••••••", label_visibility="collapsed")
                st.caption("Password")
                submitted = st.form_submit_button("Sign In", use_container_width=True)
            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    _do_login(username, password)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Register tab ──────────────────────────────────────────────────────
        with tab_register:
            st.markdown("<div class='auth-section'>", unsafe_allow_html=True)
            with st.form("register_form"):
                st.markdown("#### Create your account")
                r_username = st.text_input("Username", placeholder="your_username", key="r_u", label_visibility="collapsed")
                st.caption("Username")
                r_email    = st.text_input("Email", placeholder="you@example.com", label_visibility="collapsed")
                st.caption("Email")
                r_password = st.text_input("Password", type="password", placeholder="••••••••", key="r_p", label_visibility="collapsed")
                st.caption("Password")
                r_selfie   = st.file_uploader(
                    "Upload a selfie photo (JPG / PNG)",
                    type=["jpg", "jpeg", "png", "webp"],
                    help="A clear front-facing photo so the AI can recognise you in event albums.",
                )
                submitted = st.form_submit_button(
                    "Create Account", use_container_width=True
                )
            if submitted:
                if not r_selfie:
                    st.error("A selfie image is required for registration.")
                elif not all([r_username, r_email, r_password]):
                    st.error("All fields are required.")
                else:
                    _do_register(r_username, r_email, r_password, r_selfie)
            st.markdown("</div>", unsafe_allow_html=True)

else:
    # ── Logged in: home / quick-links ─────────────────────────────────────────
    st.title("Photo Curator")
    st.markdown("Welcome back! Choose a section from the sidebar or the buttons below.")

    col1, col2 = st.columns(2)
    with col1:
        st.page_link("pages/2_dashboard.py", label="Dashboard")
    with col2:
        st.page_link("pages/3_profile.py", label="Profile")

    st.divider()
    st.info(
        "Upload a ZIP of photos on the **Dashboard** page to start a curation job. "
        "The AI will return only the photos featuring your face."
    )
