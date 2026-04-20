"""
pages/2_dashboard.py — Upload photos and track curation jobs.

Sections
────────
1. New Job      — file uploader + live status poller.
2. History      — expandable cards for past jobs; fetch / download / delete.
"""

import time

import streamlit as st

from utils.api_client import ApiClient
from utils.theme import apply_custom_theme

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("token"):
    st.warning("You must be logged in to view this page.")
    st.switch_page("app.py")

apply_custom_theme()
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

st.title("Dashboard")
st.divider()

# ── Use Tabs to separate concerns ─────────────────────────────────────────────
tab_new, tab_hist = st.tabs(["New Job", "History"])

# ════════════════════════════════════════════════════════════════════════════════
# Tab 1 — New Job & Tracking
# ════════════════════════════════════════════════════════════════════════════════
with tab_new:
    st.markdown("### Upload Photos")

    zip_file = st.file_uploader(
        "Choose a ZIP file containing your event photos",
        type=["zip"],
        help="Pack all photos into a single .zip and upload here. The AI will filter to only those featuring your face.",
    )

    if st.button(
        "Upload & Start Curation",
        disabled=(zip_file is None),
        use_container_width=True,
    ):
        try:
            with st.spinner("Uploading ZIP…"):
                result = client.upload_zip(zip_file)
            st.session_state["current_job_id"] = result["job_id"]
            st.session_state.pop("cached_dl_id",   None)
            st.session_state.pop("cached_dl_data", None)
            st.success(f"Job created — ID: **{result['job_id']}**")
        except Exception as exc:
            st.error(f"Upload failed: {exc}")

    st.markdown("---")
    st.markdown("### Active Job Status")

    _active_id = st.session_state.get("current_job_id")

    if _active_id:
        try:
            with st.spinner("Fetching status…"):
                status_data = client.get_job_status(_active_id)

            status  = status_data["status"]
            updated = status_data.get("updated_at", "")[:19].replace("T", " ")

            _badge = {
                "pending":    "**PENDING**",
                "processing": "**PROCESSING**",
                "done":       "**DONE**",
                "failed":     "**FAILED**",
            }.get(status, f"**{status.upper()}**")

            st.markdown(f"**Job #{_active_id} Status:** {_badge} — Last updated: `{updated}`")

            # ── Progress display ──────────────────────────────────────────────
            total     = status_data.get("total_photos") or 0
            processed = status_data.get("processed_photos") or 0
            matched   = status_data.get("matched_photos") or 0

            if total > 0:
                progress = min(processed / total, 1.0)
                st.progress(progress)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total",     total)
                with col2:
                    st.metric("Processed", processed)
                with col3:
                    st.metric("Matched",   matched)

                if status in ("pending", "processing"):
                    remaining   = total - processed
                    est_seconds = remaining * 0.5
                    if est_seconds > 60:
                        st.caption(f"Estimated {int(est_seconds / 60)} min remaining")
                    else:
                        st.caption("Almost done…")

            # ── Job resolution ────────────────────────────────────────────────
            if status == "done":
                st.success("Curation complete! You can download your photos below.")
                if st.session_state.get("cached_dl_id") != _active_id:
                    with st.spinner("Preparing download…"):
                        st.session_state["cached_dl_data"] = client.download_result(_active_id)
                        st.session_state["cached_dl_id"]   = _active_id

                st.download_button(
                    label="Download Curated ZIP",
                    data=st.session_state["cached_dl_data"],
                    file_name=f"curated_{_active_id}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

            elif status == "failed":
                st.error("Job failed. Please check the logs or upload again.")

            elif status in ("pending", "processing"):
                time.sleep(3)
                st.rerun()

        except Exception as exc:
            st.error(f"Could not fetch status: {exc}")
    else:
        st.info("No active job. Upload a ZIP file above to begin.")

# ════════════════════════════════════════════════════════════════════════════════
# Tab 2 — Upload History
# ════════════════════════════════════════════════════════════════════════════════
with tab_hist:
    if st.button("Refresh History", use_container_width=True):
        try:
            with st.spinner("Loading history…"):
                st.session_state["history"] = client.get_history()
        except Exception as exc:
            st.error(f"Could not load history: {exc}")

    if "history" not in st.session_state:
        st.info("Click 'Refresh History' to load your past jobs.")
    else:
        history: list = st.session_state["history"]

        if not history:
            st.info("No jobs yet.")
        else:
            for job in history:
                jid = job["job_id"]
                status_label = job["status"].upper()

                with st.expander(f"Job #{jid}  ·  {job['created_at'][:10]}  ·  {status_label}"):
                    st.write(f"**Created:** `{job['created_at'][:19].replace('T', ' ')}`")
                    st.write(f"**Updated:** `{job['updated_at'][:19].replace('T', ' ')}`")

                    action_cols = st.columns([1, 1, 1])
                    dl_key = f"hist_dl_{jid}"

                    # Fetch / Download
                    if job["status"] == "done" and job["has_result"]:
                        with action_cols[0]:
                            if st.button("Fetch Result", key=f"fetch_{jid}", use_container_width=True):
                                try:
                                    with st.spinner("Fetching ZIP from server…"):
                                        st.session_state[dl_key] = client.download_result(jid)
                                except Exception as exc:
                                    st.error(f"Download failed: {exc}")

                        with action_cols[1]:
                            if dl_key in st.session_state:
                                st.download_button(
                                    "Save ZIP",
                                    data=st.session_state[dl_key],
                                    file_name=f"curated_{jid}.zip",
                                    mime="application/zip",
                                    key=f"save_{jid}",
                                    use_container_width=True,
                                )

                    # Delete button — always visible
                    with action_cols[2]:
                        if st.button("Delete", key=f"delete_{jid}", use_container_width=True, type="secondary"):
                            try:
                                client.delete_job(jid)
                                # Remove from cached list and refresh
                                st.session_state["history"] = [
                                    j for j in st.session_state["history"]
                                    if j["job_id"] != jid
                                ]
                                # Clear any cached download for this job
                                st.session_state.pop(dl_key, None)
                                st.success(f"Job #{jid} deleted.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Delete failed: {exc}")
