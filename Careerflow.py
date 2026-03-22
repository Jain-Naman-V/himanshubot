import streamlit as st
import os
import asyncio
import edge_tts
import speech_recognition as sr
import json
import plotly.graph_objects as go
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.document_loaders import PyPDFLoader
from streamlit_mic_recorder import mic_recorder
from fpdf import FPDF
import tempfile
import io
import base64
from pathlib import Path

# --- 1. CONFIGURATION ---
load_dotenv()
st.set_page_config(page_title="CareerFlow: Find Your Challenge", layout="centered", page_icon="💼")

# Base URL for sharing (set CAREERFLOW_BASE_URL in .env when deploying)
BASE_URL = os.getenv("CAREERFLOW_BASE_URL", "https://careerflow.app")

# LLM provider is configured in the sidebar (BYOK - any OpenAI-compatible endpoint)

# Spacing for broad, presentable layout
st.markdown("""
<style>
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; max-width: 1400px !important; padding-left: 2.5rem !important; padding-right: 2.5rem !important; }
    div[data-testid="column"] { padding-left: 1.25rem !important; padding-right: 1.25rem !important; }
    .job-card-wrap { padding: 2.25rem 2.25rem; margin-bottom: 2rem; border-radius: 12px; border: 1px solid #e5e7eb; background: inherit; min-height: 220px; }
    .custom-section { padding: 1.5rem; margin-bottom: 1.5rem; }
    .section-box { padding: 1.5rem; margin: 1rem 0; border-radius: 10px; border: 1px solid #e5e7eb; background: #fafafa; }
    .section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; padding-bottom: 0.5rem; }
    .streamlit-expanderHeader { font-size: 1rem !important; font-weight: 600 !important; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: 0.5rem !important; }
</style>
""", unsafe_allow_html=True)

# Placeholder avatar (1x1 blue pixel PNG) when assets not present
AVATAR_PLACEHOLDER = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

# Predefined mock interview jobs with full JDs (realistic)
PREDEFINED_JOBS = [
    {
        "id": "fund_accountant_gs",
        "label": "Fund Accountant",
        "role": "Fund Accountant",
        "company": "Goldman Sachs",
        "location": "Bangalore",
        "job_type": "Hybrid",
        "salary": "12,00,000 - 18,00,000 LPA",
        "industry": "Financial Services",
        "experience": "3-8 Years",
        "focus_topics": "NAV calculation, Reconciliation, Fund accounting, Cash flows",
        "jd_text": """Fund Accountant - Goldman Sachs Asset Management

Responsibilities:
• Prepare and review daily/weekly/monthly NAV packages for hedge funds and mutual funds.
• Perform cash, position, and P&L reconciliations.
• Coordinate with custodians and prime brokers for breaks resolution.
• Ensure compliance with accounting standards (GAAP/IFRS) and regulatory requirements.
• Support audit and financial reporting cycles.

Requirements:
• 1–3 years of fund accounting or related experience.
• Strong knowledge of NAV calculation, reconciliation processes, and financial instruments.
• Proficiency in Excel; experience with Bloomberg, Advent Geneva, or similar.
• Attention to detail and ability to meet tight deadlines.
• Degree in Finance, Accounting, or related field. CA/CFA/ACCA preferred.""",
    },
    {
        "id": "data_analyst_maersk",
        "label": "Data Analyst",
        "role": "Data Analyst",
        "company": "Maersk",
        "location": "Mumbai",
        "job_type": "On-site",
        "salary": "1,50,000 - 2,50,000 LPA",
        "industry": "Logistics & Shipping",
        "experience": "3-5 Years",
        "focus_topics": "SQL, Python, Data visualization, Supply chain metrics",
        "jd_text": """Data Analyst - Maersk

Responsibilities:
• Analyze supply chain, shipping, and operations data to drive decisions.
• Build dashboards and reports for KPIs (on-time delivery, cost, utilization).
• Write SQL queries and use Python/R for data processing.
• Partner with business teams to define metrics and track performance.
• Identify trends, anomalies, and improvement opportunities.

Requirements:
• 1–3 years of experience in data analysis or business intelligence.
• Strong SQL; proficiency in Python or R.
• Experience with Power BI, Tableau, or Looker.
• Understanding of supply chain/logistics is a plus.
• Bachelor’s degree in a quantitative field (CS, Engineering, Statistics).""",
    },
    {
        "id": "ops_manager",
        "label": "Ops Manager",
        "role": "Ops Manager",
        "company": "Logistics Co",
        "location": "Delhi NCR",
        "job_type": "Full Time",
        "salary": "1,50,000 - 3,00,000 LPA",
        "industry": "Operations",
        "experience": "7+ Years",
        "focus_topics": "Operations, Supply chain, Team management",
        "jd_text": """Ops Manager

Responsibilities:
• Oversee daily operations and ensure smooth workflows.
• Manage team performance and coordinate with stakeholders.
• Monitor KPIs and implement process improvements.
• Handle escalations and vendor management.

Requirements:
• 7+ years of operations experience.
• Strong leadership and communication skills.
• Experience in supply chain or logistics preferred.""",
    },
    {
        "id": "software_engineer_tcs",
        "label": "Software Engineer",
        "role": "Software Engineer",
        "company": "Tata Consultancy Services",
        "location": "Multiple",
        "job_type": "Hybrid",
        "salary": "6,00,000 - 12,00,000 LPA",
        "industry": "IT Services",
        "experience": "1-4 Years",
        "focus_topics": "Java, System design, Algorithms, SDLC",
        "jd_text": """Software Engineer - Tata Consultancy Services

Responsibilities:
• Design, develop, and maintain enterprise applications.
• Participate in code reviews and follow SDLC best practices.
• Collaborate with BA/QA teams and clients.
• Troubleshoot production issues and optimize performance.
• Contribute to technical documentation.

Requirements:
• 1–4 years of software development experience.
• Strong programming in Java, C#, or Python.
• Knowledge of databases (SQL/NoSQL), REST APIs, and cloud (AWS/Azure) preferred.
• Good problem-solving and communication skills.
• BE/BTech in Computer Science or equivalent.""",
    },
    {
        "id": "risk_executive_zomato",
        "label": "Risk Executive",
        "role": "Risk Executive",
        "company": "Zomato",
        "location": "Remote",
        "job_type": "Remote",
        "salary": "18,00,000 - 23,00,000 LPA",
        "industry": "Fintech / Food Tech",
        "experience": "3-8 Years",
        "focus_topics": "Risk management, Compliance, Fraud detection",
        "jd_text": """Risk Executive - Zomato

Responsibilities:
• Identify and assess operational and financial risks.
• Implement risk frameworks and compliance processes.
• Monitor fraud and collaborate with cross-functional teams.
• Report to leadership on risk metrics.

Requirements:
• 3-8 years of risk or compliance experience.
• Knowledge of fintech/payments risk preferred.
• Strong analytical and communication skills.""",
    },
    {
        "id": "audit_intern_deloitte",
        "label": "Audit Intern",
        "role": "Audit Intern",
        "company": "Deloitte",
        "location": "Gurgaon",
        "job_type": "Internship",
        "salary": "25,000 / Month",
        "industry": "Accounting & Audit",
        "experience": "Fresher",
        "focus_topics": "Audit basics, Financial statements, Documentation",
        "jd_text": """Audit Intern - Deloitte

Responsibilities:
• Assist in audit fieldwork and documentation.
• Support review of financial statements.
• Learn audit procedures and compliance.
• Collaborate with audit teams.

Requirements:
• Final year or recent graduate in Commerce/Accounting.
• Interest in audit and assurance.
• Good communication and attention to detail.""",
    },
    {
        "id": "product_manager_flipkart",
        "label": "Product Manager",
        "role": "Product Manager",
        "company": "Flipkart",
        "location": "Bangalore",
        "job_type": "Hybrid",
        "salary": "15,00,000 - 25,00,000 LPA",
        "industry": "E-commerce",
        "experience": "2-5 Years",
        "focus_topics": "Product strategy, User research, Roadmaps, Stakeholder management",
        "jd_text": """Product Manager - Flipkart

Responsibilities:
• Define product vision and roadmap for customer or seller-facing features.
• Conduct user research, analyze data, and prioritize backlog.
• Work with engineering, design, and business to ship features.
• Define KPIs and monitor product performance.
• Own PRDs and acceptance criteria for releases.

Requirements:
• 2–5 years of product management experience in tech.
• Strong analytical and problem-solving skills.
• Experience with agile, user research, and data-driven decisions.
• Prior e-commerce or consumer tech experience preferred.
• MBA or equivalent with technical background.""",
    },
    {
        "id": "hr_analyst_accenture",
        "label": "HR Analyst",
        "role": "HR Analyst",
        "company": "Accenture",
        "location": "Multiple",
        "job_type": "Hybrid",
        "salary": "5,00,000 - 10,00,000 LPA",
        "industry": "Consulting",
        "experience": "1-3 Years",
        "focus_topics": "HR analytics, Workforce planning, Attrition, Talent metrics",
        "jd_text": """HR Analyst - Accenture

Responsibilities:
• Analyze HR data (attrition, hiring, engagement, diversity).
• Build dashboards and reports for workforce planning.
• Support talent acquisition and retention initiatives.
• Partner with HR Business Partners for insights and recommendations.
• Ensure data quality and compliance.

Requirements:
• 1–3 years of HR analytics or people analytics experience.
• Proficiency in Excel; experience with Power BI, Workday, or HR systems.
• Understanding of HR processes and metrics.
• Strong communication and stakeholder management.
• Degree in HR, Business, Statistics, or related field.""",
    },
    {
        "id": "business_analyst_ibm",
        "label": "Business Analyst",
        "role": "Business Analyst",
        "company": "IBM",
        "location": "Multiple",
        "job_type": "Hybrid",
        "salary": "8,00,000 - 14,00,000 LPA",
        "industry": "Technology",
        "experience": "2-4 Years",
        "focus_topics": "Requirements gathering, Process mapping, Agile, UAT",
        "jd_text": """Business Analyst - IBM

Responsibilities:
• Elicit and document business and functional requirements.
• Create process flows, user stories, and acceptance criteria.
• Facilitate workshops with stakeholders.
• Support UAT and coordinate with development teams.
• Track project status and risks.

Requirements:
• 2–4 years of business analysis experience in tech projects.
• Strong analytical skills and experience with agile/scrum.
• Proficiency in Jira, Confluence, or similar.
• Ability to translate business needs into technical requirements.
• Bachelor’s degree; certification (CBAP, PMI-PBA) is a plus.""",
    },
]

# --- 2. CORE FUNCTIONS ---

def get_llm():
    api_key = st.session_state.get("llm_api_key", "")
    base_url = st.session_state.get("llm_base_url", "")
    model_name = st.session_state.get("llm_model", "")
    if not api_key or not base_url or not model_name:
        st.error("LLM not configured. Please set Base URL, Model, and API Key in the sidebar.")
        st.stop()
    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.3,
    )


def transcribe_audio(audio_bytes):
    r = sr.Recognizer()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.wav"
    with sr.AudioFile(audio_file) as source:
        audio_data = r.record(source)
        try:
            return r.recognize_google(audio_data, language="en-IN")
        except Exception:
            return None


async def text_to_speech(text, voice, output_file="ai_reply.mp3"):
    communicate = edge_tts.Communicate(text, voice, rate="+20%")
    await communicate.save(output_file)


def extract_text_from_pdf(uploaded_file, max_chars=4000):
    """Extract text from PDF. Returns (text, error_msg). error_msg is None on success."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(uploaded_file.read())
            temp_path = temp_pdf.name
        loader = PyPDFLoader(temp_path)
        pages = loader.load()
        full_text = "\n".join([page.page_content for page in pages])
        os.remove(temp_path)
        text = full_text[:max_chars] if len(full_text) > max_chars else full_text
        if not text or not text.strip():
            return "No resume provided.", "The PDF appears empty or has no extractable text."
        return text, None
    except Exception as e:
        return "No resume provided.", f"Could not read PDF: {str(e)[:100]}. Ensure it's a valid PDF with selectable text."


def _parse_json_from_llm(raw_text):
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


def generate_jd(role, company, industry):
    """Generate JD using LLM. Returns plain text."""
    try:
        llm = get_llm()
        prompt = f"""Generate a concise job description (150-300 words) for:
Role: {role}
Company: {company}
Industry: {industry or 'General'}

Include: Responsibilities (4-6), Requirements (3-5), preferred qualifications. Professional tone. Plain text only."""
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        st.error(f"Error generating JD: {e}")
        return ""


def run_cv_scrutiny(cv_text, target_role, candidate_type, jd_text=None):
    """Run CV scrutiny. Returns dict with cv_quality_score, parameters, strengths, issues, suggestions, optional jd_fit_score."""
    try:
        llm = get_llm()
        base_prompt = f"""You are a professional CV reviewer.

CV:
{cv_text[:4000]}

Target role (for context only): {target_role}
Candidate type: {candidate_type}

Score ONLY CV quality. Do NOT penalize for lacking experience in {target_role}.
- Format & Structure (20%): Layout, sections, length, readability.
- Content Quality (25%): Bullets, action verbs, quantifiable results.
- Experience section (25%): Is their experience clearly presented? Gaps explained?
- Skills section (20%): Are skills clearly listed and evidenced?
- Impact & Achievements (10%): Concrete outcomes.

Apply red-flag deductions: grammar, missing contact, unexplained gaps, no numbers, >3 pages.

Return ONLY valid JSON:
{{
  "cv_quality_score": 0-100,
  "parameters": {{"format_structure": 0-100, "content_quality": 0-100, "experience_section": 0-100, "skills_section": 0-100, "impact_achievements": 0-100}},
  "strengths": ["point1", "point2"],
  "issues": ["point1", "point2"],
  "suggestions": ["point1", "point2"]
}}"""
        if jd_text:
            base_prompt += f"""

**Job Description:** {jd_text[:2000]}

Also return jd_fit_score (0-100). For freshers, score on skills and potential. For career switchers, score on transferable skills and upskilling."""
        response = llm.invoke([HumanMessage(content=base_prompt)])
        data = _parse_json_from_llm(response.content)
        if jd_text and "jd_fit_score" not in data:
            data["jd_fit_score"] = None
        return data
    except Exception as e:
        st.error(f"Error running CV scrutiny: {e}")
        return None


def run_cv_update(cv_text, issues, suggestions):
    """Generate improved CV from scrutiny feedback."""
    try:
        llm = get_llm()
        prompt = f"""You are a professional CV writer. Improve this CV based on the feedback below.

CV:
{cv_text[:4000]}

Scrutiny feedback:
- Issues: {issues}
- Suggestions: {suggestions}

Rules: Do NOT invent experience. Improve bullets with action verbs and numbers. Fix grammar. Keep 1-2 pages. Preserve all facts.

Output the improved CV as plain text, section by section."""
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        st.error(f"Error updating CV: {e}")
        return ""


def run_cv_tailor(cv_text, jd_text):
    """Tailor CV to match JD."""
    try:
        llm = get_llm()
        prompt = f"""You are a CV tailor. Adapt this CV to match the job description.

CV: {cv_text[:4000]}
Job description: {jd_text[:2000]}

Rules: Use JD keywords where they fit real experience. Reframe bullets for relevance. Do NOT invent. Keep facts accurate.

Output the tailored CV as plain text, section by section."""
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        st.error(f"Error tailoring CV: {e}")
        return ""


def run_cv_complete_improvement(cv_text, issues, suggestions, jd_text=None):
    """Create one improved CV addressing ALL issues + suggestions, and tailor for JD if provided."""
    try:
        llm = get_llm()
        base = f"""You are a professional CV writer. Create a single improved CV that addresses ALL feedback.

CV:
{cv_text[:4000]}

Scrutiny feedback:
- Issues to fix: {issues}
- Suggestions to apply: {suggestions}
"""
        if jd_text and jd_text.strip():
            base += f"""
Job description (tailor content to match keywords and requirements where experience aligns):
{jd_text[:2000]}
"""
        base += """
Rules: Do NOT invent experience. Improve bullets with action verbs and numbers. Fix grammar. Keep 1-2 pages. Preserve all facts. Apply all suggestions. If JD provided, weave in relevant keywords naturally.
Output the complete improved CV as plain text, section by section."""
        response = llm.invoke([HumanMessage(content=base)])
        return response.content.strip()
    except Exception as e:
        st.error(f"Error creating improved CV: {e}")
        return ""


def run_study_material(role, weak_areas, focus_topics):
    """Generate study material. Returns dict with study_items."""
    try:
        llm = get_llm()
        prompt = f"""You are a career coach. Generate study material.

Role: {role}
Weak areas: {weak_areas}
Focus topics: {focus_topics or 'General'}

Return ONLY valid JSON:
{{
  "study_items": [
    {{"topic": "name", "description": "what", "why_for_you": "why", "resource": "optional URL"}}
  ]
}}

5-10 items. Role-specific + weak areas. Concise."""
        response = llm.invoke([HumanMessage(content=prompt)])
        return _parse_json_from_llm(response.content)
    except Exception as e:
        st.error(f"Error generating study material: {e}")
        return {"study_items": []}


def _get_avatar_image(is_male):
    """Return avatar image path or placeholder bytes. Uses man.jpg / woman.jpg or man.png / woman.png."""
    base = Path(__file__).parent
    assets_dir = base / "assets"
    base_name = "man" if is_male else "woman"
    for folder in (assets_dir, base):  # check assets first, then project root
        for ext in (".jpg", ".jpeg", ".png"):
            path = folder / f"{base_name}{ext}"
            if path.exists():
                return str(path)
    return io.BytesIO(AVATAR_PLACEHOLDER)


def do_start_interview(role, company, focus_topics, jd_text, resume_text, current_voice, current_name, candidate_type):
    """Start interview session - sets up system prompt and state."""
    if os.path.exists("ai_reply.mp3"):
        try:
            os.remove("ai_reply.mp3")
        except OSError:
            pass
    st.session_state.selected_voice = current_voice
    st.session_state.interviewer_name = current_name
    jd_to_use = jd_text or st.session_state.get("generated_jd", "")
    system_prompt = f"""### IDENTITY
You are {current_name}, a Senior Hiring Manager at {company}. You are conducting an interview for the role of {role}. Be professional, fair, and slightly formal.

### CONTEXT
**Resume:** {resume_text[:3000]}
**Job Description:** {jd_to_use[:2000] if jd_to_use else "Not provided."}
**Focus Topics:** {focus_topics}
**Candidate Type:** {candidate_type}

### GOAL
Conduct an interview that tests role-specific competence. Prioritize JD-based and topic-based questions. Do NOT over-focus on resume or background—assess knowledge and fit for the role.

### STRUCTURE (follow strictly)
1. **INTRO (1 question only):** Welcome. Ask for a brief introduction (30–60 sec). Do not drill into resume here.
2. **JD & TOPIC DEEP-DIVE (5–7 questions):** This is the MAIN part. Ask questions directly from:
   - Job description: requirements, responsibilities, skills, tools mentioned.
   - Focus topics: if provided (e.g. NAV, Reconciliation), ask technical/conceptual questions on these.
   - Role-specific knowledge: industry concepts, processes, scenarios.
   Ask technical, situational, and behavioral questions that the JD demands. Probe depth. Avoid generic "tell me about your experience" questions.
3. **RESUME TIE-IN (0–1 question, optional):** At most one question linking their experience to the role. Do not dwell on resume.
4. **CLOSING:** Ask "What are you looking for in this role?" or "Do you have any questions for me?" -> Answer briefly -> "Thanks for your time. HR will be in touch." -> Output [INTERVIEW_COMPLETE] on the next line.

### RULES
- Ask ONE question at a time.
- Keep each question SHORT (1–2 sentences).
- Prioritize JD and focus topics over resume.
- No lecturing. If wrong or vague, one follow-up then move on.
- Adapt to candidate type: softer for freshers, deeper for experienced.
- Total: 6–9 questions. JD/topic questions must be the majority.
- After closing, output [INTERVIEW_COMPLETE].

### TIMING
15–20 minutes. Most questions should test JD and topics, not just "what you did."."""
    st.session_state.report_role = role
    st.session_state.report_company = company
    st.session_state.report_focus_topics = focus_topics
    st.session_state.report_jd = jd_to_use
    st.session_state.history = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="I am ready. Start Phase 1."),
    ]
    st.session_state.interview_active = True
    st.session_state.generate_report = False
    st.session_state.report_data = None
    st.session_state.study_material_data = None
    st.session_state.counselor_history = []
    st.session_state.counselor_messages = []


# --- 3. PDF REPORT ENGINE ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(10, 25, 60)
        self.rect(0, 0, 210, 40, "F")
        self.set_font("helvetica", "B", 22)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, "INTERVIEW PERFORMANCE REPORT", 0, new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("helvetica", "", 12)
        self.cell(0, 5, "Powered by CareerFlow AI", 0, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, "Developed by Himanshu Rawat", 0, new_x="RIGHT", new_y="TOP", align="C")


def create_rich_pdf_report(data, role, company):
    """Create PDF with full report data (enhanced structure)."""
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, 20)

    # Normalize data for backward compatibility
    score = data.get("overall_score", data.get("score", 0))
    dimensions = data.get("dimensions", {})
    tech = dimensions.get("technical", dimensions.get("knowledge", 0))
    comm = dimensions.get("communication", 0)
    conf = dimensions.get("confidence", 0)
    rel = dimensions.get("relevance", 0)

    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Role: {role}  |  Company: {company}", 0, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(5)

    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, 60, 190, 30, "DF")
    pdf.set_xy(10, 65)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(190, 10, "OVERALL MATCH SCORE", 0, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", "B", 24)
    pdf.set_text_color(10, 25, 60)
    pdf.cell(190, 10, f"{score}/100", 0, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)

    # Dimensions
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "Dimensions: Knowledge/Technical | Communication | Confidence | Relevance", 0, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 6, f"{tech} | {comm} | {conf} | {rel}", 0, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(5)

    # Strengths
    strengths = data.get("strengths", [])
    if strengths:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Strengths", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 10)
        for s in strengths[:5]:
            clean = str(s).encode("latin-1", "replace").decode("latin-1")
            _safe_multi_cell(pdf, 0, 5, f"- {clean}")
        pdf.ln(3)

    # Weaknesses
    weaknesses = data.get("weaknesses", [])
    if weaknesses:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Weaknesses", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 10)
        for w in weaknesses[:5]:
            clean = str(w).encode("latin-1", "replace").decode("latin-1")
            _safe_multi_cell(pdf, 0, 5, f"- {clean}")
        pdf.ln(3)

    # How to present better
    how_to = data.get("how_to_present_better", [])
    if how_to:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "How to Present Yourself Better", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        for h in how_to[:4]:
            if isinstance(h, dict):
                tip = h.get("tip", "")
                do = h.get("do_instead", "")[:100]
                clean = f"{tip}: {do}".encode("latin-1", "replace").decode("latin-1")
                _safe_multi_cell(pdf, 0, 5, clean)
        pdf.ln(3)

    # Intro review
    intro = data.get("intro_review")
    if intro and isinstance(intro, dict):
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Suggested Intro", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        si = intro.get("suggested_intro", "")[:500]
        clean = si.encode("latin-1", "replace").decode("latin-1")
        _safe_multi_cell(pdf, 0, 5, clean)
        pdf.ln(3)

    # Detailed analysis
    bullets = data.get("detailed_analysis_bullets", [])
    detail = data.get("detailed_analysis", "")
    if bullets:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Detailed Feedback", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        for b in bullets[:8]:
            clean = str(b).encode("latin-1", "replace").decode("latin-1")
            _safe_multi_cell(pdf, 0, 5, f"- {clean}")
    elif detail:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Detailed Feedback", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        clean = str(detail)[:800].encode("latin-1", "replace").decode("latin-1")
        _safe_multi_cell(pdf, 0, 5, clean)

    pdf.ln(5)
    # Next steps
    steps = data.get("next_steps", [])
    if steps:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Next Steps", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        for s in steps[:5]:
            clean = str(s).encode("latin-1", "replace").decode("latin-1")
            _safe_multi_cell(pdf, 0, 5, f"- {clean}")

    filename = "CareerFlow_Report.pdf"
    pdf.output(filename)
    return filename


def _clean_pdf_text(s, max_len=800):
    return str(s)[:max_len].encode("latin-1", "replace").decode("latin-1")


def _safe_multi_cell(pdf, w, h, text):
    """Safely write multi_cell, resetting X to left margin to avoid 'Not enough horizontal space' errors."""
    pdf.set_x(pdf.l_margin)
    try:
        pdf.multi_cell(w, h, text)
    except Exception:
        # Fallback: truncate aggressively and retry
        try:
            pdf.multi_cell(w, h, text[:80])
        except Exception:
            pass  # Skip this text entirely rather than crash


def _parse_cv_sections(cv_text):
    """Parse CV text into (title, content) sections for PDF layout."""
    import re
    text = (cv_text or "").strip()
    if not text:
        return [("", "")]
    sections = []
    headers = [
        "PROFESSIONAL SUMMARY", "SUMMARY", "EXECUTIVE SUMMARY", "OBJECTIVE",
        "EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT",
        "EDUCATION", "QUALIFICATIONS",
        "SKILLS", "TECHNICAL SKILLS", "CORE COMPETENCIES",
        "PROJECTS", "CERTIFICATIONS", "ACHIEVEMENTS", "CONTACT",
    ]
    pat = re.compile(r"\n\s*(" + "|".join(re.escape(h) for h in headers) + r")\s*\n", re.IGNORECASE)
    parts = pat.split(text)
    if len(parts) <= 1:
        return [("", _clean_pdf_text(text, 4000))]
    if parts[0].strip():
        sections.append(("", _clean_pdf_text(parts[0].strip(), 800)))
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].strip().upper()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections.append((title, _clean_pdf_text(content, 1200)))
    return sections if sections else [("", _clean_pdf_text(text, 4000))]


def create_cv_pdf(cv_text):
    """Create a professional PDF from CV text. Returns file path."""
    class CVPDF(FPDF):
        def header(self):
            self.set_fill_color(40, 50, 70)
            self.rect(0, 0, 210, 35, "F")
            self.set_font("helvetica", "B", 18)
            self.set_text_color(255, 255, 255)
            self.cell(0, 12, "IMPROVED CV", 0, new_x="LMARGIN", new_y="NEXT", align="C")
            self.set_font("helvetica", "", 10)
            self.cell(0, 5, "CareerFlow AI", 0, new_x="LMARGIN", new_y="NEXT", align="C")
            self.ln(15)

        def footer(self):
            self.set_y(-12)
            self.set_font("helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, "Generated by CareerFlow", 0, new_x="RIGHT", new_y="TOP", align="C")

    pdf = CVPDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, 20)
    sections = _parse_cv_sections(cv_text)
    for title, content in sections:
        if title:
            pdf.set_font("helvetica", "B", 11)
            pdf.set_text_color(40, 50, 70)
            pdf.cell(0, 8, title.upper(), 0, new_x="LMARGIN", new_y="NEXT", align="L")
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
            pdf.ln(6)
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        for line in content.split("\n"):
            line = line.strip()
            if line:
                pdf.set_x(10)
                _safe_multi_cell(pdf, 0, 5, line[:500])
        pdf.ln(4)
    pdf_dir = os.path.join(tempfile.gettempdir(), "CareerFlow")
    os.makedirs(pdf_dir, exist_ok=True)
    fname = os.path.join(pdf_dir, "CareerFlow_Improved_CV.pdf")
    pdf.output(fname)
    return fname


def create_main_report_pdf(data, role, company):
    """PDF 1: Main report - scores, summary, strengths, weaknesses."""
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, 20)
    score = data.get("overall_score", data.get("score", 0))
    dims = data.get("dimensions", {})
    tech = dims.get("technical", dims.get("knowledge", 0))
    comm = dims.get("communication", 0)
    conf = dims.get("confidence", 0)
    rel = dims.get("relevance", 0)
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, f"Role: {role}  |  Company: {company}", 0, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, 55, 190, 35, "DF")
    pdf.set_xy(10, 60)
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(190, 10, "OVERALL SCORE", 0, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", "B", 28)
    pdf.set_text_color(10, 25, 60)
    pdf.cell(190, 12, f"{score}/100", 0, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"Dimensions: Knowledge {tech} | Communication {comm} | Confidence {conf} | Relevance {rel}", 0, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(5)
    for label, items in [("Strengths", data.get("strengths", [])[:6]), ("Weaknesses", data.get("weaknesses", [])[:6])]:
        if items:
            pdf.set_font("helvetica", "B", 11)
            pdf.cell(0, 8, label, 0, new_x="LMARGIN", new_y="NEXT", align="L")
            pdf.set_font("helvetica", "", 10)
            for x in items:
                _safe_multi_cell(pdf, 0, 5, f"- {_clean_pdf_text(x, 500)}")
            pdf.ln(3)
    pdf_dir = os.path.join(tempfile.gettempdir(), "CareerFlow")
    os.makedirs(pdf_dir, exist_ok=True)
    fname = os.path.join(pdf_dir, "CareerFlow_Main_Report.pdf")
    pdf.output(fname)
    return fname


def create_detailed_feedback_pdf(data, role, company):
    """PDF 2: Detailed feedback - answer reviews, how to present, intro, analysis."""
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, 20)
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(10, 25, 60)
    pdf.cell(0, 10, "DETAILED FEEDBACK REPORT", 0, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, f"Role: {role}  |  Company: {company}", 0, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)
    # Answer reviews
    for ar in data.get("answer_reviews", [])[:6]:
        if isinstance(ar, dict):
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 6, ar.get("question_topic", "Question"), 0, new_x="LMARGIN", new_y="NEXT", align="L")
            pdf.set_font("helvetica", "", 9)
            _safe_multi_cell(pdf, 0, 5, f"You said: {_clean_pdf_text(ar.get('user_answer_summary', ''), 200)}")
            _safe_multi_cell(pdf, 0, 5, f"Improve: {_clean_pdf_text(ar.get('improvement', ''), 300)}")
            pdf.ln(4)
    how_to = data.get("how_to_present_better", [])
    if how_to:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "How to Present Yourself Better", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        for h in how_to[:6]:
            if isinstance(h, dict):
                _safe_multi_cell(pdf, 0, 5, f"{h.get('tip','')}: {_clean_pdf_text(h.get('do_instead',''), 150)}")
        pdf.ln(4)
    intro = data.get("intro_review")
    if intro and isinstance(intro, dict):
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Intro - Tell Me About Yourself", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        _safe_multi_cell(pdf, 0, 5, f"Feedback: {_clean_pdf_text(intro.get('feedback',''), 300)}")
        _safe_multi_cell(pdf, 0, 5, f"Suggested intro: {_clean_pdf_text(intro.get('suggested_intro',''), 500)}")
        pdf.ln(4)
    bullets = data.get("detailed_analysis_bullets", [])
    if bullets:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Detailed Analysis", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        for b in bullets[:10]:
            _safe_multi_cell(pdf, 0, 5, f"- {_clean_pdf_text(b, 400)}")
    pdf_dir = os.path.join(tempfile.gettempdir(), "CareerFlow")
    os.makedirs(pdf_dir, exist_ok=True)
    fname = os.path.join(pdf_dir, "CareerFlow_Detailed_Feedback.pdf")
    pdf.output(fname)
    return fname


def create_action_items_pdf(data, role, company):
    """PDF 3: Action items - suggested questions, next steps, intro to practice."""
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, 20)
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(10, 25, 60)
    pdf.cell(0, 10, "ACTION ITEMS - FUTURE PREPARATION", 0, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, f"Role: {role}  |  Company: {company}", 0, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)
    sug_q = data.get("suggested_questions", [])
    if sug_q:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Suggested Questions for Real Interview", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        for q in sug_q[:10]:
            _safe_multi_cell(pdf, 0, 5, f"- {_clean_pdf_text(q, 300)}")
        pdf.ln(4)
    steps = data.get("next_steps", [])
    if steps:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Next Steps", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        for s in steps[:8]:
            _safe_multi_cell(pdf, 0, 5, f"- {_clean_pdf_text(s, 300)}")
        pdf.ln(4)
    intro = data.get("intro_review")
    if intro and isinstance(intro, dict):
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Intro to Practice (30-60 sec)", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        _safe_multi_cell(pdf, 0, 5, _clean_pdf_text(intro.get("suggested_intro", ""), 600))
    if data.get("negotiation_tip"):
        pdf.ln(4)
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, "Negotiation Tip", 0, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.set_font("helvetica", "", 9)
        _safe_multi_cell(pdf, 0, 5, _clean_pdf_text(data["negotiation_tip"], 300))
    pdf_dir = os.path.join(tempfile.gettempdir(), "CareerFlow")
    os.makedirs(pdf_dir, exist_ok=True)
    fname = os.path.join(pdf_dir, "CareerFlow_Action_Items.pdf")
    pdf.output(fname)
    return fname


# --- 4. SESSION STATE INIT ---
def init_session_state():
    defaults = {
        "history": [],
        "interview_active": False,
        "generate_report": False,
        "last_audio_id": None,
        "selected_voice": "en-IN-PrabhatNeural",
        "interviewer_name": "Alex",
        "candidate_type": "Experienced",
        "cv_scrutiny_data": None,
        "cv_scrutiny_data_jd": None,
        "counselor_history": [],
        "counselor_messages": [],
        "study_material_data": None,
        "report_data": None,
        "cv_generation_data": None,
        "jd_text": "",
        "shared_recruiters": False,
        "report_role": PREDEFINED_JOBS[0]["role"],
        "report_company": PREDEFINED_JOBS[0]["company"],
        "report_focus_topics": PREDEFINED_JOBS[0]["focus_topics"],
        "report_industry": PREDEFINED_JOBS[0].get("industry", "General"),
        "jd_text": PREDEFINED_JOBS[0]["jd_text"],
        "custom_mode": False,
        "cv_only_mode": False,
        "selected_job_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()

# --- 5. SIDEBAR ---

# Provider presets: (label, base_url, models)
PROVIDER_PRESETS = {
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o3-mini"],
    },
    "Groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"],
    },
    "Together AI": {
        "base_url": "https://api.together.xyz/v1",
        "models": ["meta-llama/Llama-3.3-70B-Instruct-Turbo", "mistralai/Mixtral-8x7B-Instruct-v0.1", "Qwen/Qwen2.5-72B-Instruct-Turbo"],
    },
    "Google Gemini (OpenAI)": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "models": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    },
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["google/gemini-2.5-flash", "openai/gpt-4o", "anthropic/claude-3.5-sonnet", "meta-llama/llama-3.3-70b-instruct"],
    },
    "Ollama (Local)": {
        "base_url": "http://localhost:11434/v1",
        "models": ["llama3.2", "mistral", "gemma2", "phi3", "qwen2.5"],
    },
    "Custom": {
        "base_url": "",
        "models": [],
    },
}

with st.sidebar:
    st.title("CareerFlow")
    st.caption("Professional Edition")
    st.divider()

    st.caption("🔗 LLM Provider")
    provider_names = list(PROVIDER_PRESETS.keys())
    selected_provider = st.selectbox("Provider", provider_names, index=3, help="Choose your LLM provider or select Custom")
    preset = PROVIDER_PRESETS[selected_provider]

    # Base URL
    if selected_provider == "Custom":
        base_url_val = st.text_input("Base URL", value="", placeholder="https://your-api.com/v1", help="OpenAI-compatible API endpoint")
    else:
        base_url_val = st.text_input("Base URL", value=preset["base_url"], help="OpenAI-compatible API endpoint")

    # Model
    preset_models = preset["models"]
    if preset_models:
        model_val = st.selectbox("Model", preset_models, index=0, help="Select a model or type to search")
    else:
        model_val = st.text_input("Model Name", value="", placeholder="e.g., gpt-4o", help="Enter the model name")

    # API Key
    api_key_val = st.text_input("API Key", value="", type="password", help="Your provider's API key")

    # Store in session state
    st.session_state.llm_base_url = base_url_val
    st.session_state.llm_model = model_val
    if api_key_val:
        st.session_state.llm_api_key = api_key_val

    if not st.session_state.get("llm_api_key"):
        st.warning("Please provide your API Key to use CareerFlow.")

    st.divider()
    st.caption("Settings")
    role = st.session_state.get("report_role", PREDEFINED_JOBS[0]["role"])
    company = st.session_state.get("report_company", PREDEFINED_JOBS[0]["company"])
    jd_text = st.session_state.get("jd_text", PREDEFINED_JOBS[0]["jd_text"])
    focus_topics = st.session_state.get("report_focus_topics", PREDEFINED_JOBS[0]["focus_topics"])
    industry = st.session_state.get("report_industry", PREDEFINED_JOBS[0].get("industry", "General"))
    gender = st.radio("Voice", ["Male", "Female"], horizontal=True)
    if gender == "Male":
        current_voice = "en-IN-PrabhatNeural"
        current_name = "Alex"
    else:
        current_voice = "en-IN-NeerjaNeural"
        current_name = "Sam"

    candidate_type = st.selectbox(
        "I am",
        ["Fresher", "Experienced", "Career switcher"],
        index=1,
    )
    st.session_state.candidate_type = candidate_type

    uploaded_resume = st.file_uploader("Resume (PDF)", type="pdf", help="Required for CV analysis and interview")

    # CV Scrutiny - run both quality and JD comparison when possible
    st.divider()
    st.markdown("**CV Analysis**")
    col_sq, col_sj = st.columns(2)
    with col_sq:
        if st.button("Quality", key="side_qual", use_container_width=True):
            if not uploaded_resume:
                st.warning("Upload a resume first.")
            else:
                with st.spinner("Analyzing CV quality..."):
                    cv_text, err = extract_text_from_pdf(uploaded_resume)
                    if err:
                        st.error(err)
                    else:
                        result = run_cv_scrutiny(cv_text, role, candidate_type, jd_text=None)
                        if result:
                            st.session_state.cv_scrutiny_data = result
                            st.session_state.cv_text_for_generation = cv_text
                            st.rerun()
    with col_sj:
        if jd_text and jd_text.strip() and st.button("Compare JD", key="side_jd", use_container_width=True):
            if not uploaded_resume:
                st.warning("Upload a resume first.")
            else:
                with st.spinner("Comparing CV with JD..."):
                    cv_text, err = extract_text_from_pdf(uploaded_resume)
                    if err:
                        st.error(err)
                    else:
                        result = run_cv_scrutiny(cv_text, role, candidate_type, jd_text=jd_text)
                        if result:
                            st.session_state.cv_scrutiny_data_jd = result
                            if "cv_text_for_generation" not in st.session_state or not st.session_state.cv_text_for_generation:
                                st.session_state.cv_text_for_generation = cv_text
                            st.rerun()
        elif not (jd_text and jd_text.strip()):
            st.caption("Add a JD to compare")

    # Sidebar: CV scrutiny results with speedometers
    cv_data = st.session_state.get("cv_scrutiny_data")
    cv_data_jd = st.session_state.get("cv_scrutiny_data_jd")
    if cv_data or cv_data_jd:
        st.divider()
        st.caption("CV Analysis")
        if cv_data:
            score = cv_data.get("cv_quality_score", 0)
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "CV Quality"},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#1a5276"}, "steps": [
                    {"range": [0, 40], "color": "#fadbd8"},
                    {"range": [40, 70], "color": "#fef9e7"},
                    {"range": [70, 100], "color": "#d5f5e3"},
                ], "threshold": {"line": {"color": "red", "width": 2}, "value": 70}}))
            fig.update_layout(height=180, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("Quality details"):
                for s in cv_data.get("strengths", [])[:3]:
                    st.success(f"✓ {s}")
                for i in cv_data.get("issues", [])[:3]:
                    st.error(f"✗ {i}")
        if cv_data_jd:
            jd_score = cv_data_jd.get("jd_fit_score")
            if jd_score is not None:
                fig_jd = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=jd_score,
                    domain={"x": [0, 1], "y": [0, 1]},
                    title={"text": "JD Fit"},
                    gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#145a32"}, "steps": [
                        {"range": [0, 40], "color": "#fadbd8"},
                        {"range": [40, 70], "color": "#fef9e7"},
                        {"range": [70, 100], "color": "#d5f5e3"},
                    ], "threshold": {"line": {"color": "red", "width": 2}, "value": 70}}))
                fig_jd.update_layout(height=180, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_jd, use_container_width=True)
                with st.expander("JD fit details"):
                    for s in cv_data_jd.get("strengths", [])[:3]:
                        st.success(f"✓ {s}")
                    for i in cv_data_jd.get("issues", [])[:3]:
                        st.error(f"✗ {i}")

    st.divider()

    if not st.session_state.get("cv_only_mode"):
        if st.button("End & View Report"):
            st.session_state.generate_report = True
            st.rerun()

# --- 6. MAIN SCREEN ---

if not st.session_state.generate_report:
    # Pre-interview: CV scrutiny results + CV generation
    if not st.session_state.interview_active:
        custom_mode = st.session_state.get("custom_mode", False)
        cv_only_mode = st.session_state.get("cv_only_mode", False)
        selected_job_id = st.session_state.get("selected_job_id")

        if cv_only_mode:
            # --- CV-ONLY: Just improve CV, no interview ---
            st.markdown("### Just Improve My CV")
            st.caption("Upload your resume, get analysis, and improve your CV. No interview required.")
            if st.button("← Back", key="back_cv_only"):
                st.session_state.cv_only_mode = False
                st.rerun()
            st.markdown("---")
            cv_only_resume = st.file_uploader("Upload Resume (PDF)", type="pdf", key="cv_only_resume", help="Required for CV analysis")
            cv_only_jd = st.text_area("Job Description (optional)", height=100, placeholder="Paste JD to tailor your CV, or leave blank for quality-only analysis.", key="cv_only_jd")
            col_q, col_j = st.columns(2, gap="medium")
            with col_q:
                if st.button("Analyze CV (quality)", key="cv_only_qual", use_container_width=True):
                    if not cv_only_resume:
                        st.warning("Upload a resume first.")
                    else:
                        with st.spinner("Analyzing..."):
                            cv_t, err = extract_text_from_pdf(cv_only_resume)
                            if err:
                                st.error(err)
                            else:
                                res = run_cv_scrutiny(cv_t, "General", candidate_type, jd_text=None)
                                if res:
                                    st.session_state.cv_scrutiny_data = res
                                    st.session_state.cv_text_for_generation = cv_t
                                    st.rerun()
            with col_j:
                if cv_only_jd and cv_only_jd.strip() and st.button("Compare with JD", key="cv_only_jdfit", use_container_width=True):
                    if not cv_only_resume:
                        st.warning("Upload a resume first.")
                    else:
                        with st.spinner("Comparing..."):
                            cv_t, err = extract_text_from_pdf(cv_only_resume)
                            if err:
                                st.error(err)
                            else:
                                res = run_cv_scrutiny(cv_t, "General", candidate_type, jd_text=cv_only_jd)
                                if res:
                                    st.session_state.cv_scrutiny_data_jd = res
                                    if "cv_text_for_generation" not in st.session_state:
                                        st.session_state.cv_text_for_generation = cv_t
                                    st.rerun()
            cvo_data = st.session_state.get("cv_scrutiny_data")
            cvo_data_jd = st.session_state.get("cv_scrutiny_data_jd")
            if cvo_data or cvo_data_jd:
                if cvo_data:
                    st.metric("CV Quality Score", f"{cvo_data.get('cv_quality_score', 0)}/100")
                if cvo_data_jd and cvo_data_jd.get("jd_fit_score") is not None:
                    st.metric("JD Fit Score", f"{cvo_data_jd.get('jd_fit_score')}/100")
                cvo_txt = st.session_state.get("cv_text_for_generation", "")
                cvo_jd = cv_only_jd or ""
                cvo_issues = list(dict.fromkeys(
                    (cvo_data.get("issues", []) if cvo_data else []) + (cvo_data_jd.get("issues", []) if cvo_data_jd else [])
                ))
                cvo_sugg = list(dict.fromkeys(
                    (cvo_data.get("suggestions", []) if cvo_data else []) + (cvo_data_jd.get("suggestions", []) if cvo_data_jd else [])
                ))
                cvo_for_gen = cvo_data or cvo_data_jd
                col_a, col_b, col_c = st.columns(3, gap="medium")
                with col_a:
                    if st.button("Update my CV", key="cvo_upd", use_container_width=True):
                        with st.spinner("Generating..."):
                            imp = run_cv_update(cvo_txt, cvo_for_gen.get("issues", []), cvo_for_gen.get("suggestions", []))
                            if imp:
                                st.session_state.cv_generation_data = {"type": "update", "text": imp}
                                st.rerun()
                with col_b:
                    if cvo_jd and st.button("Tailor for this JD", key="cvo_tail", use_container_width=True):
                        with st.spinner("Generating..."):
                            imp = run_cv_tailor(cvo_txt, cvo_jd)
                            if imp:
                                st.session_state.cv_generation_data = {"type": "tailor", "text": imp}
                                st.rerun()
                with col_c:
                    if st.button("Create improved CV", type="primary", key="cvo_comp", use_container_width=True):
                        with st.spinner("Creating..."):
                            imp = run_cv_complete_improvement(cvo_txt, cvo_issues, cvo_sugg, cvo_jd)
                            if imp:
                                st.session_state.cv_generation_data = {"type": "complete", "text": imp}
                                st.rerun()
            cvo_gen = st.session_state.get("cv_generation_data")
            if cvo_gen:
                st.success("Your improved CV is ready.")
                with st.expander("Your Improved CV", expanded=True):
                    st.text_area("Preview", cvo_gen.get("text", ""), height=220, disabled=True, key="cvo_preview")
                    txt = cvo_gen.get("text", "")
                    col_p, col_t = st.columns(2, gap="medium")
                    with col_p:
                        pdf_path = create_cv_pdf(txt)
                        with open(pdf_path, "rb") as f:
                            st.download_button("Download CV (PDF)", f.read(), "CareerFlow_Improved_CV.pdf", "application/pdf", type="primary", key="cvo_dl_pdf", use_container_width=True)
                    with col_t:
                        st.download_button("Download as text", txt, "CareerFlow_Improved_CV.txt", "text/plain", key="cvo_dl_txt", use_container_width=True)
                st.info("Ready for a mock interview? Pick a job from the landing page.")
        elif custom_mode:
            # --- CUSTOM CHALLENGE: Full form with all options ---
            st.markdown("### Create Custom Challenge")
            st.caption("Input your own job details. All features: CV scrutiny, scoring, CV generation & mock interview.")
            st.markdown("")
            if st.button("← Back to challenges", key="back_custom"):
                st.session_state.custom_mode = False
                st.rerun()

            st.markdown("**Job details**")
            col1, col2 = st.columns(2)
            with col1:
                cust_role = st.text_input("Target Role", "Fund Accountant", key="cust_role", help="e.g. Data Analyst, Product Manager")
                cust_company = st.text_input("Target Company", "Goldman Sachs", key="cust_company")
            with col2:
                cust_focus = st.text_input("Focus Topics", placeholder="e.g., NAV, Reconciliation", key="cust_focus")
                cust_industry = st.text_input("Industry", "Financial Services", key="cust_industry")
            # Sync generated JD into widget before text_area is created (Streamlit disallows modifying widget state after creation)
            if st.session_state.get("jd_just_generated"):
                st.session_state.cust_jd = st.session_state.cust_jd_gen
                del st.session_state["jd_just_generated"]
            cust_jd = st.text_area("Job Description (JD)", value=st.session_state.get("cust_jd_gen", ""), height=150, placeholder="Paste your JD or click Generate below...", key="cust_jd", help="Paste the full job description for better CV tailoring and interview prep")
            col_gj, _ = st.columns([1, 4])
            with col_gj:
                if st.button("Generate JD", key="gen_jd"):
                    with st.spinner("Generating JD..."):
                        gen = generate_jd(cust_role, cust_company, cust_industry)
                        if gen:
                            st.session_state.cust_jd_gen = gen
                            st.session_state.jd_just_generated = True  # will sync into cust_jd before widget on next run
                            st.rerun()
            st.markdown("---")
            st.markdown("**Upload & analyze**")
            cust_resume = st.file_uploader("Upload Resume (PDF)", type="pdf", key="cust_resume", help="Required for CV analysis and mock interview")
            st.markdown("**CV Analysis**")
            col_q, col_jd = st.columns(2, gap="medium")
            with col_q:
                if st.button("Analyze CV (quality)", key="cust_qual", use_container_width=True):
                    if not cust_resume:
                        st.warning("Upload a resume first.")
                    else:
                        with st.spinner("Analyzing..."):
                            cv_t, err = extract_text_from_pdf(cust_resume)
                            if err:
                                st.error(err)
                            else:
                                res = run_cv_scrutiny(cv_t, cust_role, candidate_type, jd_text=None)
                                if res:
                                    st.session_state.cv_scrutiny_data = res
                                    st.session_state.cv_text_for_generation = cv_t
                                    st.rerun()
            with col_jd:
                if cust_jd and st.button("Compare with JD", key="cust_jdfit", use_container_width=True):
                    if not cust_resume:
                        st.warning("Upload a resume first.")
                    else:
                        with st.spinner("Comparing..."):
                            cv_t, err = extract_text_from_pdf(cust_resume)
                            if err:
                                st.error(err)
                            else:
                                res = run_cv_scrutiny(cv_t, cust_role, candidate_type, jd_text=cust_jd)
                                if res:
                                    st.session_state.cv_scrutiny_data_jd = res
                                    if "cv_text_for_generation" not in st.session_state:
                                        st.session_state.cv_text_for_generation = cv_t
                                    st.rerun()

            cv_data = st.session_state.get("cv_scrutiny_data")
            cv_data_jd = st.session_state.get("cv_scrutiny_data_jd")
            if cv_data or cv_data_jd:
                if cv_data:
                    st.metric("CV Quality Score", f"{cv_data.get('cv_quality_score', 0)}/100")
                if cv_data_jd and cv_data_jd.get("jd_fit_score") is not None:
                    st.metric("JD Fit Score", f"{cv_data_jd.get('jd_fit_score')}/100")
                cv_txt = st.session_state.get("cv_text_for_generation", "")
                issues = list(dict.fromkeys((cv_data.get("issues", []) if cv_data else []) + (cv_data_jd.get("issues", []) if cv_data_jd else [])))
                suggestions = list(dict.fromkeys((cv_data.get("suggestions", []) if cv_data else []) + (cv_data_jd.get("suggestions", []) if cv_data_jd else [])))
                col_u, col_t, col_c = st.columns(3, gap="medium")
                with col_u:
                    if st.button("Update my CV", key="cust_upd", use_container_width=True):
                        with st.spinner("Generating..."):
                            imp = run_cv_update(cv_txt, (cv_data or cv_data_jd).get("issues", []), (cv_data or cv_data_jd).get("suggestions", []))
                            if imp:
                                st.session_state.cv_generation_data = {"type": "update", "text": imp}
                                st.rerun()
                with col_t:
                    if cust_jd and st.button("Tailor for this JD", key="cust_tail", use_container_width=True):
                        with st.spinner("Generating..."):
                            imp = run_cv_tailor(cv_txt, cust_jd)
                            if imp:
                                st.session_state.cv_generation_data = {"type": "tailor", "text": imp}
                                st.rerun()
                with col_c:
                    if st.button("Create improved CV", type="primary", key="cust_comp", use_container_width=True):
                        with st.spinner("Creating..."):
                            imp = run_cv_complete_improvement(cv_txt, issues, suggestions, cust_jd)
                            if imp:
                                st.session_state.cv_generation_data = {"type": "complete", "text": imp}
                                st.rerun()
            cv_gen = st.session_state.get("cv_generation_data")
            if cv_gen:
                st.success("Your improved CV is ready.")
                with st.expander("Your Improved CV", expanded=True):
                    st.text_area("Preview", cv_gen.get("text", ""), height=220, disabled=True, key="cust_preview")
                    txt = cv_gen.get("text", "")
                    col_pdf, col_txt = st.columns(2, gap="medium")
                    with col_pdf:
                        pdf_path = create_cv_pdf(txt)
                        with open(pdf_path, "rb") as f:
                            st.download_button("Download CV (PDF)", f.read(), "CareerFlow_Improved_CV.pdf", "application/pdf", type="primary", key="cust_dl_pdf", use_container_width=True)
                    with col_txt:
                        st.download_button("Download as text", txt, "CareerFlow_Improved_CV.txt", "text/plain", key="cust_dl_txt", use_container_width=True)

            st.divider()
            if st.button("Start Custom Interview", type="primary", key="start_custom"):
                st.session_state.report_role = cust_role
                st.session_state.report_company = cust_company
                st.session_state.report_focus_topics = cust_focus
                st.session_state.report_industry = cust_industry
                st.session_state.jd_text = cust_jd or ""
                if cust_resume:
                    txt, err = extract_text_from_pdf(cust_resume)
                    resume_text = txt if not err else "Not provided."
                    if err:
                        st.warning(err)
                else:
                    resume_text = "Not provided."
                do_start_interview(cust_role, cust_company, cust_focus, cust_jd or "", resume_text, current_voice, current_name, candidate_type)
                st.rerun()

        elif selected_job_id:
            # --- PRE-SELECTED JOB: Show prep and start ---
            job = next((j for j in PREDEFINED_JOBS if j["id"] == selected_job_id), PREDEFINED_JOBS[0])
            st.markdown(f"### Selected: **{job['role']}** @ {job['company']}")
            st.caption(f"{job.get('location', '')} · {job.get('job_type', '')} · {job.get('experience', '')} · {job.get('salary', '')}")
            if st.button("← Choose another"):
                st.session_state.selected_job_id = None
                st.rerun()
            st.session_state.report_role = job["role"]
            st.session_state.report_company = job["company"]
            st.session_state.report_focus_topics = job["focus_topics"]
            st.session_state.report_industry = job.get("industry", "General")
            st.session_state.jd_text = job["jd_text"]
            st.info("Upload your resume in the sidebar, run CV analysis if needed, then click **Start Mock Interview** below.")
            if st.button("Start Mock Interview", type="primary", key="start_predef"):
                if uploaded_resume:
                    txt, err = extract_text_from_pdf(uploaded_resume)
                    resume_text = txt if not err else "Not provided."
                    if err:
                        st.warning(err)
                else:
                    resume_text = "Not provided."
                do_start_interview(job["role"], job["company"], job["focus_topics"], job["jd_text"], resume_text, current_voice, current_name, candidate_type)
                st.rerun()
            cv_data = st.session_state.get("cv_scrutiny_data")
            cv_data_jd = st.session_state.get("cv_scrutiny_data_jd")
            if cv_data or cv_data_jd:
                st.markdown("---")
                st.markdown("**CV Analysis** (results in sidebar)")
                cv_txt = st.session_state.get("cv_text_for_generation", "")
                jd_for_tailor = job["jd_text"]
                data_for_gen = cv_data or cv_data_jd
                issues = list(dict.fromkeys((cv_data.get("issues", []) if cv_data else []) + (cv_data_jd.get("issues", []) if cv_data_jd else [])))
                suggestions = list(dict.fromkeys((cv_data.get("suggestions", []) if cv_data else []) + (cv_data_jd.get("suggestions", []) if cv_data_jd else [])))
                col_a, col_b, col_c = st.columns(3, gap="medium")
                with col_a:
                    if st.button("Update my CV", key="predef_upd", use_container_width=True):
                        with st.spinner("Generating..."):
                            imp = run_cv_update(cv_txt, data_for_gen.get("issues", []), data_for_gen.get("suggestions", []))
                            if imp:
                                st.session_state.cv_generation_data = {"type": "update", "text": imp}
                                st.rerun()
                with col_b:
                    if st.button("Tailor for this JD", key="predef_tail", use_container_width=True):
                        with st.spinner("Generating..."):
                            imp = run_cv_tailor(cv_txt, jd_for_tailor)
                            if imp:
                                st.session_state.cv_generation_data = {"type": "tailor", "text": imp}
                                st.rerun()
                with col_c:
                    if st.button("Create improved CV", type="primary", key="predef_comp", use_container_width=True):
                        with st.spinner("Creating..."):
                            imp = run_cv_complete_improvement(cv_txt, issues, suggestions, jd_for_tailor)
                            if imp:
                                st.session_state.cv_generation_data = {"type": "complete", "text": imp}
                                st.rerun()
            cv_gen = st.session_state.get("cv_generation_data")
            if cv_gen:
                st.success("Your improved CV is ready.")
                with st.expander("Your Improved CV", expanded=True):
                    st.text_area("Preview", cv_gen.get("text", ""), height=220, disabled=True, key="predef_preview")
                    txt = cv_gen.get("text", "")
                    col_pdf, col_txt = st.columns(2, gap="medium")
                    with col_pdf:
                        pdf_path = create_cv_pdf(txt)
                        with open(pdf_path, "rb") as f:
                            st.download_button("Download CV (PDF)", f.read(), "CareerFlow_Improved_CV.pdf", "application/pdf", type="primary", key="predef_dl_pdf", use_container_width=True)
                    with col_txt:
                        st.download_button("Download as text", txt, "CareerFlow_Improved_CV.txt", "text/plain", key="predef_dl_txt", use_container_width=True)
            if st.session_state.get("jd_text"):
                with st.expander("View Job Description"):
                    st.text_area("JD", st.session_state.jd_text, height=180, disabled=True, key="view_jd_predef")

        else:
            # --- LANDING ---
            st.markdown("""
            <div style="margin-bottom: 2.5rem; padding-bottom: 0.5rem;">
                <p style="font-size: 2.75rem; margin: 0; line-height: 1.2;">💼</p>
                <h1 style="font-size: 1.9rem; font-weight: 700; margin: 0.75rem 0 0.5rem 0;">CareerFlow: Find Your Challenge</h1>
                <p style="font-size: 1.1rem; color: #6b7280; margin: 0;">Select a role to start your AI mock interview & Resume Audit.</p>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("How it works", expanded=False):
                st.markdown("""
                1. **Pick a job** – Choose a pre-posted role or create your own with a custom JD.
                2. **Upload & analyze** – Upload your resume in the sidebar and run CV analysis (quality and JD fit).
                3. **Improve your CV** – Generate an improved CV based on feedback.
                4. **Mock interview** – Start the AI interview, answer verbally, and get a detailed report with scores and action items.
                """)
            st.markdown("---")
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

            row1, row2 = st.columns([1, 2], gap="large")
            with row1:
                st.markdown("""
                <div class="custom-section" style="padding: 2rem; margin-bottom: 2rem; min-height: 200px;">
                    <p style="font-size: 2.25rem; margin: 0;">📄</p>
                    <h2 style="font-size: 1.35rem; font-weight: 600; margin: 0.75rem 0 0.6rem 0;">Just Improve My CV</h2>
                    <p style="font-size: 1.05rem; color: #6b7280; margin: 0.5rem 0 1.25rem 0; line-height: 1.6;">Upload resume, get analysis, improve your CV. No interview needed.</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("+ Just Improve CV", key="btn_cv_only", use_container_width=True):
                    st.session_state.cv_only_mode = True
                    st.rerun()
                st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
                st.markdown("""
                <div class="custom-section" style="padding: 2rem; margin-bottom: 2rem; min-height: 200px;">
                    <p style="font-size: 2.25rem; margin: 0;">💡</p>
                    <h2 style="font-size: 1.35rem; font-weight: 600; margin: 0.75rem 0 0.6rem 0;">Have a Custom Idea?</h2>
                    <p style="font-size: 1.05rem; color: #6b7280; margin: 0.5rem 0 1.25rem 0; line-height: 1.6;">Use this to upload your OWN Job Description (The 'Old Way').</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("+ Create Custom Challenge", key="btn_custom", use_container_width=True):
                    st.session_state.custom_mode = True
                    st.rerun()

            with row2:
                st.markdown("<h2 style='font-size: 1.5rem; font-weight: 600; margin-bottom: 2rem;'>Pre-posted Jobs</h2>", unsafe_allow_html=True)
                jobs = PREDEFINED_JOBS
                for i in range(0, len(jobs), 2):
                    cols = st.columns(2, gap="large")
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx < len(jobs):
                            job = jobs[idx]
                            loc = job.get("location", "")
                            jt = job.get("job_type", "Full Time")
                            sal = job.get("salary", "—")
                            exp = job.get("experience", "—")
                            with col:
                                st.markdown(f"""
                                <div class="job-card-wrap">
                                    <p style="font-size: 1.6rem; font-weight: 600; margin: 0 0 1rem 0;">{job['role']}</p>
                                    <p style="font-size: 1.15rem; color: #6b7280; margin: 0 0 0.65rem 0;">{job['company']} | {loc} · {jt}</p>
                                    <p style="font-size: 1.1rem; margin: 0 0 0.65rem 0;">{sal}</p>
                                    <p style="font-size: 1.05rem; color: #6b7280; margin: 0 0 1.25rem 0;">{exp}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                if st.button("Check Eligibility", key=f"sel_{job['id']}", use_container_width=True):
                                    st.session_state.selected_job_id = job["id"]
                                    st.rerun()
                    if i + 2 < len(jobs):
                        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        if not cv_only_mode:
            cv_data = st.session_state.get("cv_scrutiny_data")
            cv_data_jd = st.session_state.get("cv_scrutiny_data_jd")
            if cv_data or cv_data_jd:
                st.markdown("---")
                st.markdown("**CV analysis results** are in the sidebar. Generate an improved CV below:")
                cv_text = st.session_state.get("cv_text_for_generation", "")
                jd_for_tailor = jd_text if jd_text else ""
                data_for_gen = cv_data or cv_data_jd
                issues = list(dict.fromkeys(
                    (cv_data.get("issues", []) if cv_data else []) + (cv_data_jd.get("issues", []) if cv_data_jd else [])
                ))
                suggestions = list(dict.fromkeys(
                    (cv_data.get("suggestions", []) if cv_data else []) + (cv_data_jd.get("suggestions", []) if cv_data_jd else [])
                ))
                col_a, col_b, col_c = st.columns(3, gap="medium")
                with col_a:
                    if st.button("Update my CV", key="btn_update", use_container_width=True):
                        with st.spinner("Generating..."):
                            improved = run_cv_update(cv_text, data_for_gen.get("issues", []), data_for_gen.get("suggestions", []))
                            if improved:
                                st.session_state.cv_generation_data = {"type": "update", "text": improved}
                                st.rerun()
                with col_b:
                    if jd_for_tailor and st.button("Tailor for this JD", key="btn_tailor", use_container_width=True):
                        with st.spinner("Generating..."):
                            tailored = run_cv_tailor(cv_text, jd_for_tailor)
                            if tailored:
                                st.session_state.cv_generation_data = {"type": "tailor", "text": tailored}
                                st.rerun()
                with col_c:
                    if st.button("Create improved CV", type="primary", key="btn_complete", use_container_width=True):
                        with st.spinner("Creating improved CV (all fixes)..."):
                            improved = run_cv_complete_improvement(cv_text, issues, suggestions, jd_for_tailor)
                            if improved:
                                st.session_state.cv_generation_data = {"type": "complete", "text": improved}
                                st.rerun()

            cv_gen = st.session_state.get("cv_generation_data")
            if cv_gen:
                st.success("Your improved CV is ready.")
                with st.expander("Your Improved CV", expanded=True):
                    st.text_area("Preview", cv_gen.get("text", ""), height=280, disabled=True, key="main_preview")
                    txt = cv_gen.get("text", "")
                    col_pdf, col_txt = st.columns(2, gap="medium")
                    with col_pdf:
                        pdf_path = create_cv_pdf(txt)
                        with open(pdf_path, "rb") as f:
                            st.download_button("Download CV (PDF)", f.read(), "CareerFlow_Improved_CV.pdf", "application/pdf", type="primary", key="main_dl_pdf", use_container_width=True)
                    with col_txt:
                        st.download_button("Download as text", txt, "CareerFlow_Improved_CV.txt", "text/plain", key="main_dl_txt", use_container_width=True)

    else:
        # Interview screen
        is_male = st.session_state.interviewer_name == "Alex"
        avatar = _get_avatar_image(is_male)

        st.header(f"Interview with {st.session_state.interviewer_name}")
        st.caption("Speak clearly into your microphone.")
        # Prominent interviewer avatar at top
        av_col, audio_col = st.columns([1, 1], gap="large")
        with av_col:
            st.image(avatar, use_container_width=True)
        with audio_col:
            if st.session_state.interview_active and os.path.exists("ai_reply.mp3"):
                st.audio("ai_reply.mp3", format="audio/mp3", autoplay=True)
        st.markdown("---")

        chat_container = st.container(height=400)
        with chat_container:
            for msg in st.session_state.history:
                if isinstance(msg, AIMessage):
                    clean = msg.content.replace("[INTERVIEW_COMPLETE]", "")
                    st.markdown(f"**{st.session_state.interviewer_name}:** {clean}")
                elif isinstance(msg, HumanMessage) and "System" not in str(msg):
                    if msg.content != "I am ready. Start Phase 1.":
                        st.markdown(f"**You:** {msg.content}")

        if st.session_state.interview_active and st.session_state.history:
            last_msg = st.session_state.history[-1]
            if isinstance(last_msg, HumanMessage) and "System" not in str(last_msg):
                with st.spinner("Thinking..."):
                    try:
                        llm = get_llm()
                        response = llm.invoke(st.session_state.history)
                        st.session_state.history.append(AIMessage(content=response.content))
                        asyncio.run(text_to_speech(response.content, st.session_state.selected_voice))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        if st.session_state.interview_active:
            last_text = st.session_state.history[-1].content if st.session_state.history else ""
            if "[INTERVIEW_COMPLETE]" in last_text:
                st.success("Interview Complete. Click 'End & View Report'.")
            else:
                if isinstance(st.session_state.history[-1], AIMessage):
                    audio = mic_recorder(
                        start_prompt="Speak",
                        stop_prompt="Send",
                        just_once=False,
                        format="wav",
                    )
                    if audio and audio.get("id") != st.session_state.last_audio_id:
                        st.session_state.last_audio_id = audio.get("id")
                        with st.spinner("Listening..."):
                            user_text = transcribe_audio(audio["bytes"])
                        if user_text:
                            st.session_state.history.append(HumanMessage(content=user_text))
                            st.rerun()

else:
    # --- REPORT SCREEN ---
    st.markdown("## Performance Analysis")

    if st.session_state.report_data is None:
        with st.spinner("Generating Report..."):
            try:
                # Build transcript from history
                lines = []
                for msg in st.session_state.history:
                    if isinstance(msg, AIMessage):
                        lines.append(f"Interviewer: {msg.content.replace('[INTERVIEW_COMPLETE]', '')}")
                    elif isinstance(msg, HumanMessage) and msg.content != "I am ready. Start Phase 1.":
                        lines.append(f"Candidate: {msg.content}")
                transcript = "\n".join(lines)

                llm = get_llm()
                role = st.session_state.get("report_role", "Fund Accountant")
                company = st.session_state.get("report_company", "Goldman Sachs")

                prompt = f"""You are an interview assessor. Analyze this transcript and produce a candidate report.

Transcript:
{transcript[:8000]}

Role: {role}
Company: {company}

Return ONLY valid JSON. No markdown.
{{
  "overall_score": 0-100,
  "dimensions": {{"knowledge": 0-100, "communication": 0-100, "confidence": 0-100, "relevance": 0-100}},
  "strengths": ["p1", "p2", "p3"],
  "weaknesses": ["p1", "p2", "p3"],
  "detailed_analysis_bullets": ["Phase: feedback"],
  "how_to_present_better": [{{"tip": "name", "avoid": "ex", "do_instead": "ex"}}],
  "intro_review": {{"their_answer_summary": "...", "feedback": "...", "suggested_intro": "30-60 sec personalized intro"}},
  "answer_reviews": [{{"question_topic": "topic", "user_answer_summary": "...", "improvement": "..."}}],
  "suggested_questions": ["q1","q2","q3","q4","q5"],
  "next_steps": ["s1","s2","s3"],
  "negotiation_tip": "One line if overall_score>=75 else null"
}}

Rules: 3-5 answer_reviews. 4-6 how_to_present_better. Include intro_review if intro was weak. negotiation_tip only when overall_score >= 75."""

                response = llm.invoke([HumanMessage(content=prompt)])
                data = _parse_json_from_llm(response.content)
                data["score"] = data.get("overall_score", data.get("score", 0))
                data["technical"] = data.get("dimensions", {}).get("knowledge", data.get("technical", 0))
                data["communication"] = data.get("dimensions", {}).get("communication", data.get("communication", 0))
                data["confidence"] = data.get("dimensions", {}).get("confidence", data.get("confidence", 0))
                data["detailed_analysis"] = "\n".join(data.get("detailed_analysis_bullets", [])) or data.get(
                    "detailed_analysis", "No detailed analysis."
                )
                st.session_state.report_data = data
                st.rerun()
            except Exception as e:
                st.error(f"Error generating report: {e}")

    if st.session_state.report_data:
        data = st.session_state.report_data
        role = st.session_state.get("report_role", "Fund Accountant")
        company = st.session_state.get("report_company", "Goldman Sachs")

        score = data.get("overall_score", data.get("score", 0))
        dims = data.get("dimensions", {})
        knowledge = dims.get("knowledge", dims.get("technical", 0))
        communication = dims.get("communication", 0)
        confidence = dims.get("confidence", 0)
        relevance = dims.get("relevance", 0)

        st.markdown("### Overall Score")
        st.metric("Score", f"{score}/100")
        st.markdown("")
        c1, c2, c3, c4 = st.columns(4, gap="medium")
        c1.metric("Knowledge", f"{knowledge}/100")
        c2.metric("Communication", f"{communication}/100")
        c3.metric("Confidence", f"{confidence}/100")
        c4.metric("Relevance", f"{relevance}/100")

        st.divider()
        categories = ["Knowledge", "Communication", "Confidence", "Relevance"]
        values = [knowledge, communication, confidence, relevance]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill="toself"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Strengths")
        for s in data.get("strengths", []):
            st.success(f"- {s}")
        st.markdown("### Weaknesses")
        for w in data.get("weaknesses", []):
            st.error(f"- {w}")

        how_to = data.get("how_to_present_better", [])
        if how_to:
            st.markdown("### How to Present Yourself Better")
            for h in how_to:
                if isinstance(h, dict):
                    st.markdown(f"- **{h.get('tip', '')}**")
                    st.markdown(f"  - Avoid: {h.get('avoid', '')}")
                    st.markdown(f"  - Do: {h.get('do_instead', '')}")

        intro = data.get("intro_review")
        if intro and isinstance(intro, dict):
            st.markdown("### Intro: Tell Me About Yourself")
            st.markdown("- **Your answer:** " + (intro.get("their_answer_summary", "") or ""))
            st.markdown("- **Feedback:** " + (intro.get("feedback", "") or ""))
            st.markdown("- **Suggested intro:**")
            st.info(intro.get("suggested_intro", ""))

        answer_reviews = data.get("answer_reviews", [])
        if answer_reviews:
            st.markdown("### Answer Reviews")
            for ar in answer_reviews:
                if isinstance(ar, dict):
                    st.markdown(f"- **{ar.get('question_topic', '')}**")
                    st.markdown(f"  - You said: {ar.get('user_answer_summary', '')}")
                    st.markdown(f"  - Improve: {ar.get('improvement', '')}")

        bullets = data.get("detailed_analysis_bullets", [])
        if bullets:
            st.markdown("### Detailed Feedback")
            for b in bullets:
                st.write(f"- {b}")
        elif data.get("detailed_analysis"):
            st.markdown("### Detailed Feedback")
            st.write(data["detailed_analysis"])

        sug_q = data.get("suggested_questions", [])
        if sug_q:
            st.markdown("### Suggested Questions for Real Interview")
            st.markdown("\n".join([f"- {q}" for q in sug_q]))

        steps = data.get("next_steps", [])
        if steps:
            st.markdown("### Next Steps")
            st.markdown("\n".join([f"- {s}" for s in steps]))

        if score >= 75 and data.get("negotiation_tip"):
            st.info(data["negotiation_tip"])

        st.markdown("---")
        st.markdown("### Download Reports")
        f1 = create_main_report_pdf(data, role, company)
        f2 = create_detailed_feedback_pdf(data, role, company)
        f3 = create_action_items_pdf(data, role, company)
        col1, col2, col3 = st.columns(3, gap="medium")
        with col1:
            with open(f1, "rb") as f:
                st.download_button("Main Report (PDF)", f.read(), "CareerFlow_Main_Report.pdf", "application/pdf", type="primary", key="dl_main", use_container_width=True)
        with col2:
            with open(f2, "rb") as f:
                st.download_button("Detailed Feedback (PDF)", f.read(), "CareerFlow_Detailed_Feedback.pdf", "application/pdf", key="dl_detail", use_container_width=True)
        with col3:
            with open(f3, "rb") as f:
                st.download_button("Action Items (PDF)", f.read(), "CareerFlow_Action_Items.pdf", "application/pdf", key="dl_action", use_container_width=True)

        col_li, col_rec = st.columns(2, gap="medium")
        with col_li:
            summary = f"Score: {score}/100 for {role} - Prepared with CareerFlow"
            li_url = f"https://www.linkedin.com/sharing/share-offsite/?url={BASE_URL}&summary={summary}"
            st.link_button("Share on LinkedIn", li_url, use_container_width=True)
        with col_rec:
            st.caption("Demo: simulate recruiter interest")
            if st.button("Share with Recruiters (demo)"):
                st.session_state.shared_recruiters = True
                st.success("Demo: Request received. In production, this would notify recruiters.")
                st.rerun()
            elif st.session_state.shared_recruiters:
                st.success("Demo: Request received. In production, this would notify recruiters.")

        st.markdown("---")
        st.markdown("### Study Material")
        if st.session_state.study_material_data is None:
            with st.spinner("Generating study material..."):
                try:
                    weak = data.get("weaknesses", [])
                    sm = run_study_material(role, weak, st.session_state.get("report_focus_topics", ""))
                    st.session_state.study_material_data = sm
                    st.session_state.report_role = role
                    st.session_state.report_company = company
                    st.session_state.focus_topics = st.session_state.get("focus_topics", "")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        if st.session_state.study_material_data:
            items = st.session_state.study_material_data.get("study_items", [])
            for item in items:
                if isinstance(item, dict):
                    with st.expander(item.get("topic", "Topic")):
                        st.write(item.get("description", ""))
                        st.caption(item.get("why_for_you", ""))
                        if item.get("resource"):
                            st.markdown(f"[Resource]({item['resource']})")

        st.markdown("---")
        st.markdown("### Career Counselor")
        counselor_system = f"""You are a friendly career counselor. Help with interview prep and next steps.
Role: {role}
Weak areas: {data.get('weaknesses', [])}
Scores: Knowledge {knowledge}, Communication {communication}, Confidence {confidence}
Use this to personalize advice. Be concise (2-4 sentences). Supportive and practical."""

        suggested_qs = [
            "What should I do next to improve?",
            "How do I work on my weak areas?",
            "How do I answer Tell me about yourself?",
            "How do I handle salary questions?",
            "How can I present myself better?",
        ]
        st.caption("Suggested questions:")
        for i, sq in enumerate(suggested_qs):
            if st.button(sq, key=f"cq_{i}"):
                if "counselor_messages" not in st.session_state:
                    st.session_state.counselor_messages = [SystemMessage(content=counselor_system)]
                st.session_state.counselor_messages.append(HumanMessage(content=sq))
                try:
                    llm = get_llm()
                    resp = llm.invoke(st.session_state.counselor_messages)
                    st.session_state.counselor_messages.append(resp)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        if "counselor_messages" in st.session_state:
            for m in st.session_state.counselor_messages[1:]:
                if isinstance(m, HumanMessage):
                    with st.chat_message("user"):
                        st.write(m.content)
                else:
                    with st.chat_message("assistant"):
                        st.write(m.content)

        if prompt := st.chat_input("Ask career counselor..."):
            if "counselor_messages" not in st.session_state:
                st.session_state.counselor_messages = [SystemMessage(content=counselor_system)]
            st.session_state.counselor_messages.append(HumanMessage(content=prompt))
            try:
                llm = get_llm()
                resp = llm.invoke(st.session_state.counselor_messages)
                st.session_state.counselor_messages.append(resp)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        st.markdown("---")
        st.markdown("<h5 style='text-align: center; color: grey;'>Powered by Himanshu Rawat</h5>", unsafe_allow_html=True)
