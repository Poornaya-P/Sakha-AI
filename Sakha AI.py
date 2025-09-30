# women_child_safety_app.py
"""
Women & Child Safety — Full Streamlit app with Google Gemini
Brand: Sakha AI
"""

import os
import sqlite3
import streamlit as st
from datetime import datetime

# 🔑 API KEY DIRECTLY SET (local testing or private deploy only!)
os.environ["GOOGLE_API_KEY"] = "AIzaSyDa5GT5p0r2ivRwEknENKUxD_QYMZ4sSz0"

try:
    from google import genai
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

DB_PATH = "safety_reports.db"
APP_TITLE = "Sakha AI — Women & Child Safety Assistant"
POCSO_NOTE = (
    "POCSO (Protection of Children from Sexual Offences Act, 2012) "
    "defines a child as any person below 18 and provides special protection and procedures."
)

EMERGENCY_HELPLINE = "1098 (CHILDLINE India - 24/7)"
NGOS = [
    {"name": "CHILDLINE India (1098)", "contact": "1098", "url": "https://childlineindia.org/"},
    {"name": "Bachpan Bachao Andolan", "contact": "+91 11 49211111", "url": "https://bba.org.in/"},
    {"name": "CRY - Child Rights and You", "contact": "011-29533452", "url": "https://www.cry.org/"},
    {"name": "Save the Children (India)", "contact": "+91 124 475 2000", "url": "https://www.savethechildren.in/"},
]

# ----------------------- Database -----------------------
def init_db(path=DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        reporter_name TEXT,
        reporter_contact TEXT,
        incident_type TEXT,
        description TEXT,
        location TEXT,
        age_of_victim TEXT,
        confidential INTEGER DEFAULT 1
    )""")
    conn.commit()
    return conn

conn = init_db()

def save_report(data):
    cur = conn.cursor()
    cur.execute("""INSERT INTO reports 
        (timestamp, reporter_name, reporter_contact, incident_type, description, location, age_of_victim, confidential)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("timestamp"), data.get("reporter_name"), data.get("reporter_contact"),
            data.get("incident_type"), data.get("description"), data.get("location"),
            data.get("age_of_victim"), 1 if data.get("confidential", True) else 0,
        )
    )
    conn.commit()
    return cur.lastrowid

def get_reports(limit=10):
    cur = conn.cursor()
    cur.execute("SELECT id, timestamp, reporter_name, incident_type, location FROM reports ORDER BY id DESC LIMIT ?", (limit,))
    return cur.fetchall()

def get_report_full(rid):
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports WHERE id=?", (rid,))
    return cur.fetchone()

# ----------------------- Gemini -----------------------
def make_genai_client():
    if not GENAI_AVAILABLE:
        return None
    try:
        return genai.Client()
    except Exception as e:
        st.error(f"GenAI init failed: {e}")
        return None

def call_gemini_simple(prompt, model="gemini-2.5-flash"):
    if not GENAI_AVAILABLE:
        return "Gemini client not installed."
    client = make_genai_client()
    if not client:
        return "Client init failed."
    try:
        response = client.models.generate_content(model=model, contents=[prompt])
        return response.candidates[0].content.parts[0].text
    except Exception as e:
        return f"Error calling Gemini: {e}"

# ----------------------- UI -----------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.markdown("**Provides legal info, emotional support, and NGO resources — not a replacement for police or lawyers.**")

c1, c2 = st.columns([2, 1])

with c1:
    service = st.radio("", ["AI Lawyer", "Moral Support Chatbot", "Report Incident", "Resources & NGOs"])

    if service == "AI Lawyer":
        st.subheader("Ask about laws, procedures, evidence, reporting")
        st.info(POCSO_NOTE)
        q = st.text_area("Your question", placeholder="Steps to report abuse under POCSO...")
        if st.button("Ask AI Lawyer"):
            with st.spinner("AI Lawyer is thinking..."):
                prompt = f"You are an expert legal information assistant (POCSO, IPC). Explain clearly: {q}"
                st.success(call_gemini_simple(prompt))

    elif service == "Moral Support Chatbot":
        msg = st.text_area("Describe your feelings:")
        if st.button("Talk to Support Bot"):
            with st.spinner("Support bot is responding..."):
                prompt = f"You are a compassionate friend. Comfort user, suggest safe steps if urgent. User says: {msg}"
                st.info(call_gemini_simple(prompt))

    elif service == "Report Incident":
        st.subheader("Incident Report Form (Local storage)")
        with st.form("report_form"):
            name = st.text_input("Reporter name (optional)")
            contact = st.text_input("Contact info (optional)")
            itype = st.selectbox("Incident type", ["Sexual assault", "Harassment", "Abuse", "Trafficking", "Other"])
            desc = st.text_area("Describe what happened", height=150)
            loc = st.text_input("Location")
            age = st.text_input("Age of victim")
            conf = st.checkbox("Confidential", value=True)
            submit = st.form_submit_button("Save report")
            if submit:
                if not desc.strip():
                    st.warning("Description required")
                else:
                    rid = save_report({
                        "timestamp": datetime.utcnow().isoformat(),
                        "reporter_name": name,
                        "reporter_contact": contact,
                        "incident_type": itype,
                        "description": desc,
                        "location": loc,
                        "age_of_victim": age,
                        "confidential": conf
                    })
                    st.success(f"Report saved locally (ID: {rid})")

    elif service == "Resources & NGOs":
        st.subheader("Emergency & NGO Contacts")
        st.write(f"📞 **Childline:** {EMERGENCY_HELPLINE}")
        for ngo in NGOS:
            st.markdown(f"- **{ngo['name']}** — {ngo['contact']} — [Website]({ngo['url']})")
        st.markdown("---")
        msg = st.text_area("Compose message for NGO")
        if st.button("Generate concise message"):
            with st.spinner("AI composing..."):
                prompt = f"Make this into a short formal message (no personal data unless mentioned): {msg}"
                st.text_area("Suggested Message", value=call_gemini_simple(prompt), height=150)

with c2:
    st.subheader("Recent Reports")
    rows = get_reports()
    if rows:
        for r in rows:
            st.write(f"ID {r[0]} — {r[1]} — {r[2] or 'Anonymous'} — {r[3]} — {r[4]}")
            if st.button(f"View {r[0]}", key=f"v{r[0]}"):
                full = get_report_full(r[0])
                st.json({
                    "id": full[0], "timestamp": full[1], "name": full[2], "contact": full[3],
                    "type": full[4], "description": full[5], "location": full[6],
                    "age": full[7], "confidential": full[8]
                })
    else:
        st.write("No reports yet.")

    st.markdown("---")
    st.subheader("About App")
    st.caption("Built by Sakha AI — Data stored locally. For production, add encryption + authentication.")
