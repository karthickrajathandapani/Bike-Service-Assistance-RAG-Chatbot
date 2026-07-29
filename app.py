"""
Streamlit chat UI for the Bike Service Assistant.

Run with:  streamlit run app.py
"""
import time

import streamlit as st

from config.settings import APP_NAME, ANTHROPIC_API_KEY
from ingestion.loader import load_all_manuals, load_pdf
from ingestion.chunking import chunk_manuals, chunk_manual
from ingestion.vector_store import index_chunks
from llm.chains import answer_question, suggest_followups
from services.maintenance import get_due_items
from services.diagnosis import diagnose
from services.recommendation import get_recommendations
from services.scheduler import project_upcoming_services
from utils.helpers import new_session_id, confidence_badge
from utils.logger import log_interaction, read_analytics
from utils.pdf_export import export_maintenance_report, export_diagnosis_report, export_service_checklist
from config.settings import MANUALS_DIR
from pathlib import Path

st.set_page_config(page_title=APP_NAME, page_icon="🏍️", layout="wide")

# --- Session state ---------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = new_session_id()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {"role", "content", "meta"}

# --- Sidebar -----------------------------------------------------------------
with st.sidebar:
    st.markdown(f"## 🏍️ {APP_NAME}")
    if not ANTHROPIC_API_KEY:
        st.warning("No ANTHROPIC_API_KEY set — running in retrieval-only mode. "
                   "Add it to `.env` for full LLM answers.")

    page = st.radio(
        "Navigate",
        ["💬 Chat", "🛠️ Service Recommendation", "🔧 Fault Diagnosis",
         "🧾 Parts", "📤 Upload Manual", "📊 Admin Analytics"],
    )

    st.divider()
    st.caption("Suggested questions")
    for q in [
        "What is the recommended engine oil?",
        "When should I change the spark plug?",
        "What is the tire air pressure?",
        "How do I adjust the drive chain slack?",
    ]:
        if st.button(q, key=f"suggest_{q}", use_container_width=True):
            st.session_state["pending_query"] = q

    st.divider()
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()


# --- Page: Chat --------------------------------------------------------------
if page == "💬 Chat":
    st.title("💬 Ask about your bike")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            meta = msg.get("meta")
            if meta:
                conf = meta.get("confidence")
                if conf is not None:
                    st.caption(f"Confidence: {confidence_badge(conf)} ({conf}%)")
                if meta.get("citations"):
                    with st.expander("📚 Sources"):
                        for c in meta["citations"]:
                            st.markdown(
                                f"**[{c['source_index']}] {c['manual_name']}**, "
                                f"page {c['page']} — similarity {c['similarity_score']}\n\n"
                                f"> {c['excerpt']}"
                            )
                if meta.get("followups"):
                    st.caption("Follow-up ideas: " + " · ".join(meta["followups"]))

    query = st.chat_input("Ask a question about your manual...") or st.session_state.pop("pending_query", None)

    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Searching manuals..."):
                start = time.time()
                result = answer_question(query, session_id=st.session_state.session_id)
                result["followups"] = suggest_followups(query, result["answer"])
                log_interaction(st.session_state.session_id, query, time.time() - start,
                                 result.get("confidence"), result.get("vehicle_key"))
            st.markdown(result["answer"])
            conf = result.get("confidence")
            if conf is not None:
                st.caption(f"Confidence: {confidence_badge(conf)} ({conf}%)")
            if result.get("citations"):
                with st.expander("📚 Sources"):
                    for c in result["citations"]:
                        st.markdown(
                            f"**[{c['source_index']}] {c['manual_name']}**, "
                            f"page {c['page']} — similarity {c['similarity_score']}\n\n"
                            f"> {c['excerpt']}"
                        )
            if result.get("followups"):
                st.caption("Follow-up ideas: " + " · ".join(result["followups"]))

        st.session_state.chat_history.append({
            "role": "assistant", "content": result["answer"], "meta": result,
        })


# --- Page: Service Recommendation --------------------------------------------
elif page == "🛠️ Service Recommendation":
    st.title("🛠️ Service Recommendation")
    col1, col2 = st.columns(2)
    odometer = col1.number_input("Current odometer (km)", min_value=0, value=8500, step=100)
    avg_daily = col2.number_input("Average km ridden per day", min_value=1.0, value=25.0, step=5.0)

    if st.button("Get recommendations", type="primary"):
        items = get_due_items(odometer)
        st.subheader("Due now / due soon")
        for item in items:
            if item.overdue_km > 0:
                st.error(f"🔴 **{item.name}** — overdue by {item.overdue_km} km (every {item.interval_km} km)")
            elif item.due:
                st.warning(f"🟡 **{item.name}** — due soon (every {item.interval_km} km)")
            else:
                st.success(f"🟢 **{item.name}** — OK (every {item.interval_km} km)")

        st.subheader("Upcoming services (projected)")
        upcoming = project_upcoming_services(odometer, avg_daily)
        for u in upcoming:
            st.write(f"- **{u.name}** around **{u.at_odometer_km} km** (≈ {u.estimated_date.isoformat()})")

        pdf_path = export_maintenance_report(odometer, items)
        with open(pdf_path, "rb") as f:
            st.download_button("📄 Download Maintenance Report (PDF)", f, file_name=pdf_path.name)

        checklist_path = export_service_checklist(items)
        with open(checklist_path, "rb") as f:
            st.download_button("✅ Download Service Checklist (PDF)", f, file_name=checklist_path.name)


# --- Page: Fault Diagnosis ----------------------------------------------------
elif page == "🔧 Fault Diagnosis":
    st.title("🔧 Fault Diagnosis")
    symptom = st.text_area("Describe the problem", placeholder="e.g. Bike won't start")
    if st.button("Diagnose", type="primary") and symptom.strip():
        with st.spinner("Analyzing symptom against the manual..."):
            result = diagnose(symptom)
        st.markdown(result["answer"])
        if result.get("citations"):
            with st.expander("📚 Sources"):
                for c in result["citations"]:
                    st.markdown(f"**[{c['source_index']}] {c['manual_name']}**, page {c['page']}\n\n> {c['excerpt']}")

        pdf_path = export_diagnosis_report(symptom, result["answer"])
        with open(pdf_path, "rb") as f:
            st.download_button("📄 Download Diagnosis Report (PDF)", f, file_name=pdf_path.name)


# --- Page: Parts recommendation -----------------------------------------------
elif page == "🧾 Parts":
    st.title("🧾 Recommended Parts & Consumables")
    recs = get_recommendations()
    for key, rec in recs.items():
        st.markdown(f"**{key.replace('_', ' ').title()}**: {rec['item']}")
        st.caption(rec["note"])
        st.divider()


# --- Page: Upload Manual -------------------------------------------------------
elif page == "📤 Upload Manual":
    st.title("📤 Upload a New Manual")
    st.write("Supports multiple bikes/brands — the vehicle is auto-detected from the PDF content.")
    uploaded = st.file_uploader("Upload a PDF owner's manual", type=["pdf"])
    if uploaded and st.button("Ingest manual", type="primary"):
        dest = Path(MANUALS_DIR) / uploaded.name
        with open(dest, "wb") as f:
            f.write(uploaded.getbuffer())
        with st.spinner("Parsing, chunking, and embedding..."):
            manual = load_pdf(dest)
            chunks = chunk_manual(manual)
            count = index_chunks(chunks, reset=False)
        st.success(f"Indexed **{manual.manual_name}** as vehicle `{manual.vehicle_key}` "
                   f"— {len(chunks)} chunks added (collection size: {count}).")

    st.divider()
    st.subheader("Currently indexed manuals")
    for m in load_all_manuals():
        st.write(f"- **{m.manual_name}** → detected vehicle: `{m.vehicle_key}` ({len(m.pages)} pages)")


# --- Page: Admin Analytics -----------------------------------------------------
elif page == "📊 Admin Analytics":
    st.title("📊 Admin Analytics Dashboard")
    records = read_analytics()
    if not records:
        st.info("No interactions logged yet — ask a question in the Chat tab first.")
    else:
        import pandas as pd
        df = pd.DataFrame(records)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total chat sessions", df["session_id"].nunique())
        col2.metric("Total questions", len(df))
        col3.metric("Avg retrieval time (s)", round(df["retrieval_time_s"].mean(), 3))

        st.subheader("Most asked questions")
        st.dataframe(df["question"].value_counts().head(10))

        st.subheader("Confidence distribution")
        st.bar_chart(df["confidence"].dropna())

        st.subheader("Retrieval time over interactions")
        st.line_chart(df["retrieval_time_s"])
