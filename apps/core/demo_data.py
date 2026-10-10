"""
Sample data for the clickable UI screens.

Everything here is FAKE and only exists so every page can be clicked
through before the real database models are built. Each screen will
switch to real data as its app is built (see docs/Roadmap.md).
"""

ORGANISATION = {
    "name": "Udyog Excellence Council",
    "short_name": "UEC",
    "tagline": "Recognising the best of Indian industry",
    "founded": 1985,
    "email": "awards@uec.example",
    "phone": "+91 11 0000 0000",
    "address": "Excellence House, Lodhi Road, New Delhi 110003",
    "is_fictional": True,
}

STATS = [
    {"value": "80+", "label": "Award programmes"},
    {"value": "40", "label": "Years of recognition"},
    {"value": "6,000+", "label": "Organisations assessed"},
    {"value": "900+", "label": "Industry jury members"},
]

SECTORS = [
    "Business Excellence",
    "Energy",
    "Safety",
    "Design",
    "Innovation",
    "Sustainability",
    "Shop-floor",
]

AWARDS = [
    {
        "slug": "business-excellence",
        "name": "Business Excellence Award",
        "sector": "Business Excellence",
        "status": "Open",
        "deadline": "30 Nov 2026",
        "summary": "Our flagship award for organisations that show excellence across leadership, processes and results.",
        "rounds": 2,
        "blind": True,
        "judges_per_entry": 3,
        "fee": "No entry fee",
        "form_length": "Long form: 12 indicators in 3 areas",
        "applicant_type": "Organisation",
        "form_version": "v2026.1",
        "icon": "🏆",
    },
    {
        "slug": "kaizen",
        "name": "Kaizen Competition",
        "sector": "Shop-floor",
        "status": "Open",
        "deadline": "15 Dec 2026",
        "summary": "For shop-floor teams that made a small change with a big, measurable result.",
        "rounds": 1,
        "blind": False,
        "judges_per_entry": 2,
        "fee": "No entry fee",
        "form_length": "Short team form with before/after evidence",
        "applicant_type": "Team",
        "form_version": "v2026.1",
        "icon": "⚙️",
    },
    {
        "slug": "energy-efficiency",
        "name": "Energy Efficiency Award",
        "sector": "Energy",
        "status": "Closing soon",
        "deadline": "20 Oct 2026",
        "summary": "Recognises plants and buildings that cut energy use through smart engineering.",
        "rounds": 2, "blind": False, "judges_per_entry": 3, "fee": "₹15,000 entry fee",
        "form_length": "Medium form", "applicant_type": "Plant / unit", "form_version": "v2026.1", "icon": "⚡",
    },
    {
        "slug": "safety-excellence",
        "name": "Safety Excellence Award",
        "sector": "Safety",
        "status": "Judging",
        "deadline": "Closed",
        "summary": "For workplaces that keep people safe through strong systems and culture.",
        "rounds": 2, "blind": True, "judges_per_entry": 3, "fee": "No entry fee",
        "form_length": "Medium form", "applicant_type": "Plant / unit", "form_version": "v2026.1", "icon": "🦺",
    },
    {
        "slug": "industrial-innovation",
        "name": "Industrial Innovation Award",
        "sector": "Innovation",
        "status": "Open",
        "deadline": "10 Jan 2027",
        "summary": "Celebrates new products, processes and business models built in India.",
        "rounds": 2, "blind": True, "judges_per_entry": 3, "fee": "No entry fee",
        "form_length": "Medium form", "applicant_type": "Organisation", "form_version": "v2026.1", "icon": "💡",
    },
    {
        "slug": "sustainability-leadership",
        "name": "Sustainability Leadership Award",
        "sector": "Sustainability",
        "status": "Results",
        "deadline": "Closed",
        "summary": "For organisations leading on environment, community and responsible growth.",
        "rounds": 2, "blind": False, "judges_per_entry": 3, "fee": "No entry fee",
        "form_length": "Long form", "applicant_type": "Organisation", "form_version": "v2026.1", "icon": "🌱",
    },
    {
        "slug": "design-excellence",
        "name": "Design Excellence Award",
        "sector": "Design",
        "status": "Upcoming",
        "deadline": "Opens Jan 2027",
        "summary": "For products and spaces where good design makes life better.",
        "rounds": 1, "blind": True, "judges_per_entry": 3, "fee": "No entry fee",
        "form_length": "Short form with images", "applicant_type": "Organisation", "form_version": "—", "icon": "🎨",
    },
    {
        "slug": "5s-workplace",
        "name": "5S Workplace Competition",
        "sector": "Shop-floor",
        "status": "Upcoming",
        "deadline": "Opens Feb 2027",
        "summary": "For shop floors that are sorted, organised, clean and run by habit.",
        "rounds": 1, "blind": False, "judges_per_entry": 2, "fee": "No entry fee",
        "form_length": "Short form + on-site visit", "applicant_type": "Team", "form_version": "—", "icon": "🧹",
    },
]

HOW_IT_WORKS = [
    {"title": "Register", "text": "Create your organisation profile once, with your GST number."},
    {"title": "Apply", "text": "Pick an award and fill the form at your own pace. It saves as you go."},
    {"title": "Independent jury", "text": "Senior industry experts score your entry on their own, with no conflicts of interest."},
    {"title": "Recognition", "text": "Winners are approved by leadership and celebrated at the national ceremony."},
]

TRUST_PROMISES = [
    {"title": "Blind judging", "text": "For blind awards, jury members never see who applied. Only your work is judged."},
    {"title": "No conflicts", "text": "A jury member is never given an entry from an organisation they are linked to."},
    {"title": "Every score on record", "text": "If a score ever changes, we record who changed it, when and why."},
    {"title": "Your entry stays as sent", "text": "Your application always opens exactly as you submitted it, even if the questions change next year."},
]

PAST_WINNERS = [
    {"org": "Northstar Auto Components", "award": "Business Excellence Award 2025", "city": "Pune"},
    {"org": "Ganga Textiles — Unit 3 Team", "award": "Kaizen Competition 2025", "city": "Kanpur"},
    {"org": "Deccan Power Systems", "award": "Energy Efficiency Award 2025", "city": "Hyderabad"},
]


def get_award(slug):
    for award in AWARDS:
        if award["slug"] == slug:
            return award
    return None


def award_details(award):
    """Extra content for an award's detail page."""
    steps = [
        {"title": "Check eligibility", "text": "Confirm your organisation fits the award."},
        {"title": "Submit your application", "text": f"{award['form_length']}. Save as you go and submit before the deadline."},
        {"title": "Round 1: independent scoring", "text": f"{award['judges_per_entry']} jury members score your entry on their own."
         + (" Judging is blind." if award["blind"] else "")},
    ]
    if award["rounds"] == 2:
        steps.append({"title": "Round 2: live presentation", "text": "Shortlisted entries present to the jury in person."})
    steps.append({"title": "Results", "text": "Leadership approves the winners, then results are announced."})
    return {
        "eligibility": [
            "Operating in India for at least 3 years",
            "Open to members and non-members equally",
            f"Applicant: {award['applicant_type']}",
            "One entry per organisation per cycle",
        ],
        "steps": steps,
        "timeline": [
            {"date": "1 Sep 2026", "label": "Applications open"},
            {"date": award["deadline"], "label": "Applications close"},
            {"date": "Jan 2027", "label": "Round 1 judging"},
        ] + ([{"date": "Feb 2027", "label": "Round 2 presentations"}] if award["rounds"] == 2 else []) + [
            {"date": "Mar 2027", "label": "Winners announced"},
        ],
        "criteria": [
            {"name": "Leadership and strategy", "weight": 30},
            {"name": "Processes and people", "weight": 30},
            {"name": "Results and impact", "weight": 40},
        ],
        "faqs": [
            {"q": "Is there an entry fee?", "a": award["fee"] + "."},
            {"q": "Can I save and finish later?", "a": "Yes. Your form saves automatically and you can come back any time before the deadline."},
            {"q": "Who are the jury?", "a": "Senior people from industry and academia. Each one declares their links to organisations, so no one judges an entry they are connected to."},
            {"q": "Will I get feedback?", "a": "Yes. Every applicant receives a short feedback summary after results."},
        ],
    }


# --- Applicant portal -------------------------------------------------------

APPLICANT_ORG = {
    "name": "Acme Precision Components Pvt Ltd",
    "gstin": "27ABCDE1234F1Z5",
    "pan": "ABCDE1234F",
    "sector": "Manufacturing — Auto components",
    "size": "Medium (250–999 employees)",
    "turnover": "₹100–500 crore",
    "established": "2004",
    "website": "acme-precision.example",
    "address": "Plot 21, MIDC Industrial Area, Chakan, Pune 410501",
    "contact_name": "Priya Kulkarni",
    "contact_role": "Head of Quality",
    "contact_email": "priya.k@acme-precision.example",
    "contact_phone": "+91 98000 00000",
}

MY_APPLICATIONS = [
    {"id": "A-0042", "award": "Business Excellence Award", "slug": "business-excellence",
     "status": "Draft", "progress": 58, "deadline": "30 Nov 2026", "form_version": "v2026.1"},
    {"id": "K-0007", "award": "Kaizen Competition", "slug": "kaizen",
     "status": "Under review", "progress": 100, "deadline": "15 Dec 2026", "form_version": "v2026.1"},
    {"id": "A-0019", "award": "Business Excellence Award 2025", "slug": "business-excellence",
     "status": "Result: Finalist", "progress": 100, "deadline": "Closed", "form_version": "v2025.1"},
]

FORM_SECTIONS = [
    {"name": "Organisation details", "done": 4, "total": 4, "questions": [
        {"label": "Organisation name", "type": "text", "value": "Acme Precision Components Pvt Ltd", "identifying": True},
        {"label": "Plant location", "type": "text", "value": "Chakan, Pune", "identifying": True},
    ]},
    {"name": "Leadership and strategy", "done": 3, "total": 4, "questions": [
        {"label": "How do leaders set direction and communicate it?", "type": "textarea",
         "value": "Our leadership team runs a yearly strategy workshop with all plant heads, followed by monthly town halls..."},
        {"label": "How do you review progress against your strategy?", "type": "textarea", "value": ""},
        {"label": "Upload your strategy document (PDF)", "type": "file", "value": "strategy-2026.pdf"},
    ]},
    {"name": "Processes and people", "done": 0, "total": 4, "questions": []},
    {"name": "Results and impact", "done": 0, "total": 4, "questions": []},
]

APPLICATION_TIMELINE = [
    {"label": "Submitted", "date": "2 Oct 2026", "state": "done"},
    {"label": "Eligibility checked", "date": "4 Oct 2026", "state": "done"},
    {"label": "Under review by jury", "date": "In progress", "state": "current"},
    {"label": "Results", "date": "Mar 2027", "state": "todo"},
]

# --- Judge portal -----------------------------------------------------------

JUDGE = {"name": "Dr. R. Kapoor", "expertise": "Manufacturing, Quality"}

ASSIGNMENTS = [
    {"entry": "A-0042", "award": "Business Excellence Award", "round": "Round 1", "blind": True,
     "applicant": None, "status": "In progress", "progress": 60, "due": "15 Jan 2027"},
    {"entry": "A-0051", "award": "Business Excellence Award", "round": "Round 1", "blind": True,
     "applicant": None, "status": "Awaiting response", "progress": 0, "due": "15 Jan 2027"},
    {"entry": "K-0007", "award": "Kaizen Competition", "round": "Round 1", "blind": False,
     "applicant": "Acme Precision — Line 4 Team", "status": "Not started", "progress": 0, "due": "20 Jan 2027"},
    {"entry": "A-0038", "award": "Business Excellence Award", "round": "Round 1", "blind": True,
     "applicant": None, "status": "Submitted", "progress": 100, "due": "15 Jan 2027"},
]

SCORECARD = [
    {"name": "Leadership and strategy", "weight": 30, "score": 8, "comment": "Clear, well-communicated strategy."},
    {"name": "Processes and people", "weight": 30, "score": 7, "comment": ""},
    {"name": "Results and impact", "weight": 40, "score": None, "comment": ""},
]

ENTRY_ANSWERS = [
    {"label": "Organisation name", "value": None},
    {"label": "Plant location", "value": None},
    {"label": "How do leaders set direction and communicate it?",
     "value": "Our leadership team runs a yearly strategy workshop with all plant heads, followed by monthly town halls..."},
    {"label": "Strategy document", "value": "document-1.pdf (file name anonymised)"},
]

# --- Staff portal -----------------------------------------------------------

STAFF_ENTRIES = [
    {"id": "A-0042", "org": "Acme Precision Components", "submitted": "—", "status": "Draft", "flag": ""},
    {"id": "A-0051", "org": "Shri Ganesh Polymers Ltd", "submitted": "28 Sep 2026", "status": "Eligible", "flag": "Possible duplicate"},
    {"id": "A-0053", "org": "Coastal Marine Foods", "submitted": "30 Sep 2026", "status": "Info requested", "flag": ""},
    {"id": "A-0038", "org": "Northstar Auto Components", "submitted": "25 Sep 2026", "status": "Assigned", "flag": ""},
    {"id": "A-0060", "org": "Vertex Pharma Labs", "submitted": "5 Oct 2026", "status": "New", "flag": ""},
]

DUPLICATES = [
    {"a": "Shree Ganesh Polymers Ltd.", "b": "Shri Ganesh Polymers Limited", "score": "0.93",
     "reason": "Same GSTIN", "level": "High"},
    {"a": "Coastal Marine Foods", "b": "COASTAL MARINE FOODS PVT LTD", "score": "1.00",
     "reason": "Same name after cleaning", "level": "High"},
    {"a": "Sharma Traders Pvt Ltd", "b": "Sharma Trading Co", "score": "0.81",
     "reason": "Similar name, different GSTIN", "level": "Possible"},
]

FORM_VERSIONS = [
    {"version": "v2026.1", "status": "Published (locked)", "date": "1 Sep 2026", "applications": 64},
    {"version": "v2025.1", "status": "Archived (locked)", "date": "1 Sep 2025", "applications": 128},
    {"version": "v2024.1", "status": "Archived (locked)", "date": "1 Sep 2024", "applications": 117},
]

FORM_QUESTIONS = [
    {"section": "Organisation details", "label": "Organisation name", "type": "Short text", "required": True, "identifying": True},
    {"section": "Organisation details", "label": "Plant location", "type": "Short text", "required": True, "identifying": True},
    {"section": "Leadership and strategy", "label": "How do leaders set direction and communicate it?", "type": "Long text", "required": True, "identifying": False},
    {"section": "Leadership and strategy", "label": "Upload your strategy document", "type": "File (PDF)", "required": False, "identifying": False},
    {"section": "Results and impact", "label": "Key results over the last 3 years", "type": "Long text", "required": True, "identifying": False},
]

JUDGE_POOL = [
    {"name": "Dr. R. Kapoor", "expertise": "Manufacturing, Quality", "load": "4 / 15", "match": "Strong"},
    {"name": "Ms. A. Iyer", "expertise": "Strategy, Finance", "load": "7 / 15", "match": "Good"},
    {"name": "Mr. S. Bose", "expertise": "Operations", "load": "12 / 15", "match": "Good"},
    {"name": "Prof. N. Rao", "expertise": "Quality, Academia", "load": "3 / 15", "match": "Strong"},
]

# --- Leadership portal ------------------------------------------------------

LEADER_OVERVIEW = [
    {"award": "Business Excellence Award", "stage": "Applications open", "entries": 64, "judged": 0, "flags": 1},
    {"award": "Kaizen Competition", "stage": "Applications open", "entries": 41, "judged": 0, "flags": 0},
    {"award": "Energy Efficiency Award", "stage": "Closing soon", "entries": 52, "judged": 0, "flags": 0},
    {"award": "Safety Excellence Award", "stage": "Judging", "entries": 38, "judged": 72, "flags": 3},
    {"award": "Sustainability Leadership Award", "stage": "Results", "entries": 29, "judged": 100, "flags": 0},
]

REVIEW_QUEUE = [
    {"type": "Big score gap", "award": "Safety Excellence Award", "entry": "S-0012",
     "detail": "Judge scores 4.1, 8.6 and 7.9 — gap of 4.5 points.", "action": "Add an extra judge"},
    {"type": "Tie", "award": "Safety Excellence Award", "entry": "S-0004 / S-0019",
     "detail": "Both entries average 8.20 for 3rd place.", "action": "Decide tie-break"},
    {"type": "Late conflict", "award": "Safety Excellence Award", "entry": "S-0027",
     "detail": "Judge declared a conflict after starting. Scores removed and logged.", "action": "Confirm reassignment"},
    {"type": "Appeal", "award": "Sustainability Leadership Award", "entry": "SL-0009",
     "detail": "Applicant asks for review of Round 2 result.", "action": "Review appeal"},
]

RESULTS_TO_APPROVE = [
    {"rank": 1, "org": "Evergreen Paper Mills", "score": "8.74"},
    {"rank": 2, "org": "Sunrise Agro Industries", "score": "8.51"},
    {"rank": 3, "org": "Blue Delta Logistics", "score": "8.12"},
]

PORTAL_NAV = {
    "applicant": [
        ("Dashboard", "entries:dashboard"),
        ("Organisation profile", "entries:organisation"),
        ("Application form", "entries:form"),
        ("Application status", "entries:status"),
    ],
    "judge": [
        ("My assignments", "judging:assignments"),
        ("Score an entry", "judging:score"),
    ],
    "staff": [
        ("My awards", "awards:staff_home"),
        ("Award settings", "awards:settings"),
        ("Form builder", "awards:form_builder"),
        ("Entries", "awards:entries"),
        ("Duplicate review", "awards:duplicates"),
        ("Assign judges", "awards:assign"),
    ],
    "leader": [
        ("Overview", "dashboard:overview"),
        ("Review queue", "dashboard:review"),
        ("Approve results", "dashboard:results"),
    ],
}

ROLE_LABELS = {
    "applicant": "Applicant",
    "judge": "Judge",
    "staff": "Programme staff",
    "leader": "Leadership",
}
