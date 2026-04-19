"""
pages/1_register.py — Standalone registration page.

Redirects to Dashboard automatically if the user is already logged in.
Provides an alternative direct-access registration flow (useful when sharing
a registration link).
"""

import streamlit as st

from utils.api_client import ApiClient
from utils.theme import apply_custom_theme

# ── Auth guard: redirect if already logged in ─────────────────────────────────
if st.session_state.get("token"):
    st.switch_page("pages/2_dashboard.py")

apply_custom_theme()

client = ApiClient()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📸 Photo Curator")
    st.markdown("---")
    st.info("Please log in or register to continue.")

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("📝 Create Account")
st.markdown(
    "Register to start curating your photos with AI. "
    "Already have an account? [Log in here](/)"
)
st.divider()

_, col_center, _ = st.columns([1, 2, 1])

with col_center:
    with st.form("standalone_register_form"):
        username = st.text_input("Username",           placeholder="your_username")
        email    = st.text_input("Email",              placeholder="you@example.com")
        password = st.text_input("Password",           type="password")
        selfie   = st.file_uploader(
            "Selfie (required)",
            type=["jpg", "jpeg", "png", "webp"],
            help="Upload a clear, front-facing photo. The AI uses this to find you in event photos.",
        )
        submitted = st.form_submit_button("Create Account", use_container_width=True)

    if submitted:
        if not selfie:
            st.error("A selfie image is required.")
        elif not all([username, email, password]):
            st.error("All fields are required.")
        else:
            try:
                with st.spinner("Creating account…"):
                    client.register(username, email, password, selfie)
                with st.spinner("Logging in…"):
                    token = client.login(username, password)
                st.session_state["token"] = token
                st.success("✅ Account created! Redirecting to Dashboard…")
                st.switch_page("pages/2_dashboard.py")
            except Exception as exc:
                st.error(f"Registration failed: {exc}")
