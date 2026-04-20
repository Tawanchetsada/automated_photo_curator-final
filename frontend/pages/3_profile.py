"""
pages/3_profile.py — View and update the authenticated user's profile.

Shows current profile metadata and (optionally) the stored selfie image.
The selfie preview silently fails if the backend doesn't serve static files.
"""

import base64

import streamlit as st

from utils.api_client import BACKEND_URL, ApiClient
from utils.theme import apply_custom_theme

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("token"):
    st.warning("You must be logged in to view this page.")
    st.switch_page("app.py")

client = ApiClient()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Photo Curator")
    st.markdown("---")
    st.page_link("pages/2_dashboard.py", label="Dashboard")
    st.page_link("pages/3_profile.py",   label="Profile")
    st.markdown("---")
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("app.py")

# ── Load profile ──────────────────────────────────────────────────────────────
apply_custom_theme()

st.title("Profile")
st.divider()

try:
    with st.spinner("Loading profile…"):
        profile = client.get_profile()
except Exception as exc:
    st.error(f"Could not load profile: {exc}")
    st.stop()

# ── Profile info & selfie preview ─────────────────────────────────────────────
col_info, col_selfie = st.columns([3, 2])

with col_info:
    st.subheader(profile['username'])
    st.markdown(f"**Email:** {profile['email']}")
    st.markdown(f"**Member since:** `{profile['created_at'][:10]}`")
    st.markdown(
        f"**Selfie on file:** {'Yes' if profile['has_selfie'] else 'No'}"
    )

with col_selfie:
    if profile.get("has_selfie"):
        # Try to fetch selfie preview; silently skip if endpoint is unavailable
        try:
            import requests as _req

            selfie_url = f"{BACKEND_URL}/selfies/{profile['user_id']}.jpg"
            r = _req.get(selfie_url, timeout=2)
            if r.ok and r.headers.get("content-type", "").startswith("image/"):
                b64_img = base64.b64encode(r.content).decode("utf-8")
                st.markdown(
                    f'<div class="centered-container"><img src="data:image/jpeg;base64,{b64_img}" class="profile-img"></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("(Selfie preview unavailable)")
        except Exception:
            st.caption("(Selfie preview unavailable)")
    else:
        st.info("No selfie uploaded yet.\nAdd one below to enable face recognition.")

st.divider()

# ── Update selfie ─────────────────────────────────────────────────────────────
st.subheader("Update Selfie")
st.markdown(
    "Upload a new front-facing photo to improve recognition accuracy. "
    "All future jobs will use this image."
)

new_selfie = st.file_uploader(
    "Choose a selfie image",
    type=["jpg", "jpeg", "png"],
    help="Clear, well-lit, single-face photos work best.",
)

if st.button(
    "Update Selfie",
    disabled=(new_selfie is None),
    use_container_width=True,
    type="primary",
):
    try:
        with st.spinner("Uploading new selfie…"):
            client.update_selfie(new_selfie)
        st.success("Selfie updated! Future jobs will use your new photo.")
        st.rerun()
    except Exception as exc:
        st.error(f"Update failed: {exc}")
