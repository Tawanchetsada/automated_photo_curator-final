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
    page_icon="📸",
    layout="centered",
    initial_sidebar_state="expanded",
)

apply_custom_theme()

client = ApiClient()


# ── Sidebar (rendered on every page via app.py) ───────────────────────────────
with st.sidebar:
    st.markdown("## 📸 Photo Curator")
    st.markdown("---")
    if st.session_state.get("token"):
        st.success("✅ Logged in")
        st.page_link("pages/2_dashboard.py", label="📊 Dashboard")
        st.page_link("pages/3_profile.py",   label="👤 Profile")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
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
        st.rerun()
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
        st.rerun()
    except Exception as exc:
        st.error(f"Registration failed: {exc}")


# ── Main content ──────────────────────────────────────────────────────────────
if not st.session_state.get("token"):
    # ── Not logged in: Login / Register tabs ─────────────────────────────────
    st.title("📸 Automated Photo Curator")
    st.markdown(
        "Upload your event photos and let AI find every shot that features **you**."
    )
    st.divider()

    tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])

    # ── Login tab ─────────────────────────────────────────────────────────────
    with tab_login:
        _, col_login, _ = st.columns([1, 2, 1])
        with col_login:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="your_username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    _do_login(username, password)

    # ── Register tab ──────────────────────────────────────────────────────────
    with tab_register:
        _, col_reg, _ = st.columns([1, 2, 1])
        with col_reg:
            with st.form("register_form"):
                r_username = st.text_input("Username", placeholder="your_username", key="r_u")
                r_email    = st.text_input("Email",    placeholder="you@example.com")
                r_password = st.text_input("Password", type="password", key="r_p")
                r_selfie   = st.file_uploader(
                    "Selfie (required)",
                    type=["jpg", "jpeg", "png", "webp"],
                    help="A clear photo of your face so the AI can recognise you.",
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

else:
    # ── Logged in: home / quick-links ─────────────────────────────────────────
    st.title("📸 Photo Curator")
    st.markdown("Welcome back! Choose a section from the sidebar or the buttons below.")

    col1, col2 = st.columns(2)
    with col1:
        st.page_link("pages/2_dashboard.py", label="📊 Dashboard", icon="📊")
    with col2:
        st.page_link("pages/3_profile.py", label="👤 Profile", icon="👤")

    st.divider()
    st.info(
        "Upload a ZIP of photos on the **Dashboard** page to start a curation job. "
        "The AI will return only the photos featuring your face."
    )
