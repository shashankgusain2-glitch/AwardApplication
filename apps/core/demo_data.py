"""
Sample data for the clickable UI screens.

Everything here is FAKE and only exists so every page can be clicked
through before the real database models are built. Each screen will
switch to real data as its app is built (see docs/Roadmap.md).

Award settings changed on the staff "Award settings" screen are kept in
the browser session (see award_overrides) and applied on top of AWARDS,
so every screen follows them. This stands in for the database for now.
"""

ORGANISATION = {
    "name": "Awards Platform",
    "short_name": "AP",
    "tagline": "Recognising the best of Indian industry",
    "founded": 1985,
    "email": "awards@awards.example",
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

APPLICANT_TYPES = ["Organisation", "Team", "Plant / unit"]

# How judges meet an entry in each round. Blind judging is only possible
# in a desk review: in a site visit or live presentation the judge meets
# the applicant, so identity can't be hidden.
ROUND_TYPES = {
    "desk": "Desk review",
    "site": "Site visit",
    "live": "Live presentation",
}
BLIND_POSSIBLE = {"desk"}

# --- The two fully built demo awards ----------------------------------------
#
# These two show the brief's main point: one system, two awards that work
# differently, and the differences are data (settings), not code.

BUSINESS_EXCELLENCE = {
    "slug": "business-excellence",
    "name": "Business Excellence Award",
    "sector": "Business Excellence",
    "status": "Open",
    "deadline": "30 Nov 2026",
    "summary": "Our flagship award for organisations that show excellence across leadership, processes and results.",
    "icon": "🏆",
    # Settings staff can change on the Award settings screen
    "round_types": ["desk", "live"],
    "blind": True,
    "judges_per_entry": 3,
    "applicant_type": "Organisation",
    "fee_amount": 0,
    # Content
    "form_length": "Long form: 12 indicators in 3 areas",
    "form_version": "v2026.1",
    "eligibility": [
        "Operating in India for at least 3 years, with 3 years of performance data",
        "Whole organisations or business units can apply",
        "Open to members and non-members equally",
        "One entry per GSTIN per cycle",
    ],
    "criteria": [
        {"name": "Leadership and strategy", "weight": 30},
        {"name": "Processes and people", "weight": 30},
        {"name": "Results and impact", "weight": 40},
    ],
    "round2_criteria": [
        {"name": "Clarity of the story", "weight": 30},
        {"name": "Evidence behind the claims", "weight": 40},
        {"name": "Answers to the jury", "weight": 30},
    ],
    "extra_faqs": [
        {"q": "How long is the application?", "a": "12 indicators across 3 areas. Most organisations take 3–4 weeks, working on it in parts."},
        {"q": "What happens in Round 2?", "a": "Shortlisted organisations present to the jury in person for 30 minutes, followed by questions."},
    ],
    "form_sections": [
        {"name": "Organisation details", "questions": [
            {"label": "Organisation name", "type": "text", "identifying": True, "key": "org"},
            {"label": "Headquarters or main plant location", "type": "text", "identifying": True, "sample": "Chakan, Pune"},
            {"label": "Number of employees", "type": "text", "identifying": False, "sample": "640"},
        ]},
        {"name": "Leadership and strategy", "questions": [
            {"label": "How do leaders set direction and communicate it?", "type": "textarea", "identifying": False,
             "sample": "Our leadership team runs a yearly strategy workshop with all plant heads, followed by monthly town halls on the shop floor."},
            {"label": "How do you turn your strategy into yearly plans?", "type": "textarea", "identifying": False,
             "sample": "Each goal is broken into plant-level targets, reviewed every quarter by the management committee."},
            {"label": "How do you review progress against your strategy?", "type": "textarea", "identifying": False, "sample": ""},
            {"label": "Upload your strategy document (PDF)", "type": "file", "identifying": False, "sample": "acme-strategy-2026.pdf"},
        ]},
        {"name": "Processes and people", "questions": [
            {"label": "How do you design and improve your key processes?", "type": "textarea", "identifying": False, "sample": ""},
            {"label": "How do you develop and engage your people?", "type": "textarea", "identifying": False, "sample": ""},
            {"label": "How do you listen to your customers?", "type": "textarea", "identifying": False, "sample": ""},
            {"label": "Supporting evidence (PDF)", "type": "file", "identifying": False, "sample": ""},
        ]},
        {"name": "Results and impact", "questions": [
            {"label": "Customer results over the last 3 years", "type": "textarea", "identifying": False, "sample": ""},
            {"label": "People results over the last 3 years", "type": "textarea", "identifying": False, "sample": ""},
            {"label": "Business results over the last 3 years", "type": "textarea", "identifying": False, "sample": ""},
            {"label": "Society and environment results", "type": "textarea", "identifying": False, "sample": ""},
        ]},
    ],
    "form_versions": [
        {"version": "v2026.1", "status": "Published (locked)", "date": "1 Sep 2026", "applications": 64},
        {"version": "v2025.1", "status": "Archived (locked)", "date": "1 Sep 2025", "applications": 128},
        {"version": "v2024.1", "status": "Archived (locked)", "date": "1 Sep 2024", "applications": 117},
    ],
}

KAIZEN = {
    "slug": "kaizen",
    "name": "Kaizen Competition",
    "sector": "Shop-floor",
    "status": "Open",
    "deadline": "15 Dec 2026",
    "summary": "For shop-floor teams that made a small change with a big, measurable result.",
    "icon": "⚙️",
    # Settings staff can change on the Award settings screen
    # Assumption (to confirm with the client): written entries are screened
    # at a desk first, then judges visit the shortlisted teams on site.
    "round_types": ["desk", "site"],
    "blind": False,
    "judges_per_entry": 2,
    "applicant_type": "Team",
    "fee_amount": 0,
    # Content
    "form_length": "Short team form with before/after evidence",
    "form_version": "v2026.1",
    "eligibility": [
        "Teams of 2 to 8 people who work on the shop floor",
        "The improvement was finished in the last 12 months",
        "Results measured for at least 3 months after the change",
        "Nominated by the plant head; one entry per team per cycle",
    ],
    "criteria": [
        {"name": "Problem clarity", "weight": 25},
        {"name": "Root cause found", "weight": 25},
        {"name": "Improvement made", "weight": 25},
        {"name": "Result and how it is kept going", "weight": 25},
    ],
    "round2_criteria": [
        {"name": "Change seen working on the floor", "weight": 40},
        {"name": "Team can explain it themselves", "weight": 30},
        {"name": "Kept going (checklists, audits)", "weight": 30},
    ],
    "extra_faqs": [
        {"q": "Our team isn't good with long forms. Is that a problem?", "a": "No. The form is short and photos count as evidence. Before and after pictures often say more than words."},
        {"q": "What happens on the site visit?", "a": "Two jury members visit your plant for about an hour. They watch the improvement working and talk to the team that made it."},
        {"q": "Can more than one team from our plant enter?", "a": "Yes. Each team enters separately, with its own improvement."},
    ],
    "form_sections": [
        {"name": "Team details", "questions": [
            {"label": "Team name", "type": "text", "identifying": True, "sample": "Line 4 Changeover Crew"},
            {"label": "Company and plant", "type": "text", "identifying": True, "key": "org"},
            {"label": "Team members", "type": "text", "identifying": True, "sample": "R. Patil, S. Khan, M. Joshi, A. Das"},
        ]},
        {"name": "The problem (before)", "questions": [
            {"label": "What was the problem?", "type": "textarea", "identifying": False,
             "sample": "Changeover on Line 4 took 48 minutes, and operators walked about 30 metres for each tool."},
            {"label": "Photo before the change", "type": "file", "identifying": False, "sample": "line4-before.jpg"},
        ]},
        {"name": "The change", "questions": [
            {"label": "What was the root cause?", "type": "textarea", "identifying": False,
             "sample": "Tools were stored in a shared crib far from the line, and there was no fixed changeover sequence."},
            {"label": "What did the team change?", "type": "textarea", "identifying": False,
             "sample": "We built a shadow board at the line and wrote a 12-step changeover card."},
        ]},
        {"name": "The result (after)", "questions": [
            {"label": "What is the result, in numbers?", "type": "textarea", "identifying": False,
             "sample": "Changeover now takes 19 minutes (60% less), saving about 2 hours of production a week."},
            {"label": "Photo after the change", "type": "file", "identifying": False, "sample": "line4-after.jpg"},
            {"label": "How do you keep the improvement going?", "type": "textarea", "identifying": False,
             "sample": "A daily 2-minute checklist, and the shadow board is audited every Friday."},
        ]},
    ],
    "form_versions": [
        {"version": "v2026.1", "status": "Published (locked)", "date": "1 Aug 2026", "applications": 41},
        {"version": "v2025.1", "status": "Archived (locked)", "date": "1 Aug 2025", "applications": 57},
    ],
}

# --- Other awards (listed on the website; not fully built) ------------------

_DEFAULTS = {
    "fee_amount": 0, "form_version": "v2026.1", "form_sections": [], "form_versions": [],
    "eligibility": [], "criteria": [], "round2_criteria": [], "extra_faqs": [],
}

AWARDS = [
    BUSINESS_EXCELLENCE,
    KAIZEN,
    {**_DEFAULTS,
     "slug": "energy-efficiency", "name": "Energy Efficiency Award", "sector": "Energy",
     "status": "Closing soon", "deadline": "20 Oct 2026", "icon": "⚡",
     "summary": "Recognises plants and buildings that cut energy use through smart engineering.",
     "round_types": ["desk", "site"], "blind": False, "judges_per_entry": 3, "applicant_type": "Plant / unit",
     "fee_amount": 15000, "form_length": "Medium form"},
    {**_DEFAULTS,
     "slug": "safety-excellence", "name": "Safety Excellence Award", "sector": "Safety",
     "status": "Judging", "deadline": "Closed", "icon": "🦺",
     "summary": "For workplaces that keep people safe through strong systems and culture.",
     "round_types": ["desk", "site"], "blind": True, "judges_per_entry": 3, "applicant_type": "Plant / unit",
     "form_length": "Medium form"},
    {**_DEFAULTS,
     "slug": "industrial-innovation", "name": "Industrial Innovation Award", "sector": "Innovation",
     "status": "Open", "deadline": "10 Jan 2027", "icon": "💡",
     "summary": "Celebrates new products, processes and business models built in India.",
     "round_types": ["desk", "live"], "blind": True, "judges_per_entry": 3, "applicant_type": "Organisation",
     "form_length": "Medium form"},
    {**_DEFAULTS,
     "slug": "sustainability-leadership", "name": "Sustainability Leadership Award", "sector": "Sustainability",
     "status": "Results", "deadline": "Closed", "icon": "🌱",
     "summary": "For organisations leading on environment, community and responsible growth.",
     "round_types": ["desk", "site"], "blind": False, "judges_per_entry": 3, "applicant_type": "Organisation",
     "form_length": "Long form"},
    {**_DEFAULTS,
     "slug": "design-excellence", "name": "Design Excellence Award", "sector": "Design",
     "status": "Upcoming", "deadline": "Opens Jan 2027", "icon": "🎨",
     "summary": "For products and spaces where good design makes life better.",
     "round_types": ["desk"], "blind": True, "judges_per_entry": 3, "applicant_type": "Organisation",
     "form_length": "Short form with images", "form_version": "—"},
    {**_DEFAULTS,
     "slug": "5s-workplace", "name": "5S Workplace Competition", "sector": "Shop-floor",
     "status": "Upcoming", "deadline": "Opens Feb 2027", "icon": "🧹",
     "summary": "For shop floors that are sorted, organised, clean and run by habit.",
     "round_types": ["site"], "blind": False, "judges_per_entry": 2, "applicant_type": "Team",
     "form_length": "Short form, then an on-site audit", "form_version": "—"},
]

BUILT_AWARDS = ["business-excellence", "kaizen"]

# --- Award settings: defaults + what staff changed -------------------------

EDITABLE_SETTINGS = ["round_types", "blind", "judges_per_entry", "applicant_type", "fee_amount", "deadline"]


def award_overrides(request=None):
    """
    Settings staff saved on the Award settings screen, read from the Award
    tables, so every user (staff, judges, the public site) sees the same settings.
    `request` is kept for callers that pass it; it isn't needed any more.
    """
    from apps.awards.services import screen_overrides
    return screen_overrides()


def blind_possible(round_types):
    """Blind judging needs at least one round where judges don't meet the applicant."""
    return any(t in BLIND_POSSIBLE for t in round_types)


def get_award(slug, request=None):
    """One award with staff's saved settings applied. Returns None if not found."""
    base = next((a for a in AWARDS if a["slug"] == slug), None)
    if base is None:
        return None
    award = {**base, **award_overrides(request).get(slug, {})}
    award["fee"] = f"₹{award['fee_amount']:,} entry fee" if award["fee_amount"] else "No entry fee"
    award["rounds"] = len(award["round_types"])
    award["blind_possible"] = blind_possible(award["round_types"])
    # Safety net: blind can never be on for an award judged only in person.
    award["blind"] = award["blind"] and award["blind_possible"]
    award["rounds_info"] = [
        {
            "number": n,
            "type": t,
            "label": ROUND_TYPES[t],
            "is_blind": award["blind"] and t in BLIND_POSSIBLE,
        }
        for n, t in enumerate(award["round_types"], start=1)
    ]
    return award


def round_type(award, round_name):
    """'Round 2' -> the type of that round for this award, e.g. 'site'. None if the award has no such round."""
    number = int(round_name.split()[-1])
    if not 1 <= number <= len(award["round_types"]):
        return None
    return award["round_types"][number - 1]


def is_blind_round(award, round_name):
    """Rule 1 applies only in blind awards, and only in rounds judged at a desk."""
    return award["blind"] and round_type(award, round_name) in BLIND_POSSIBLE


def all_awards(request=None):
    return [get_award(a["slug"], request) for a in AWARDS]


def built_awards(request=None):
    return [get_award(slug, request) for slug in BUILT_AWARDS]


# --- Website content --------------------------------------------------------

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

GENERIC_ELIGIBILITY = [
    "Operating in India for at least 3 years",
    "Open to members and non-members equally",
    "One entry per organisation per cycle",
]

GENERIC_CRITERIA = [
    {"name": "Approach", "weight": 30},
    {"name": "Implementation", "weight": 30},
    {"name": "Results", "weight": 40},
]


def award_details(award):
    """Content for an award's public detail page, built from its settings."""
    steps = [
        {"title": "Check eligibility", "text": f"Confirm you fit the award. Applicant: {award['applicant_type']}."},
        {"title": "Submit your application", "text": f"{award['form_length']}. Save as you go and submit before the deadline."},
    ]
    judges = award["judges_per_entry"]
    for r in award["rounds_info"]:
        who = "shortlisted entries" if r["number"] > 1 else "every entry"
        if r["type"] == "desk":
            text = f"{judges} jury members read and score {who} online, each on their own."
            if r["is_blind"]:
                text += " Judging is blind: they don't see who applied."
        elif r["type"] == "site":
            text = f"{judges} jury members visit the site of {who} to see the work in action and talk to the people behind it."
        else:
            text = f"{who.capitalize()} present to {judges} jury members in person, followed by questions."
        steps.append({"title": f"Round {r['number']}: {r['label'].lower()}", "text": text})
    steps.append({"title": "Results", "text": "Leadership approves the winners, then results are announced."})

    round_months = ["Jan 2027", "Feb 2027"]
    timeline = [
        {"date": "Sep 2026", "label": "Applications open"},
        {"date": award["deadline"], "label": "Applications close"},
    ] + [
        {"date": round_months[i], "label": f"Round {r['number']}: {r['label'].lower()}"}
        for i, r in enumerate(award["rounds_info"][:2])
    ] + [{"date": "Mar 2027", "label": "Winners announced"}]

    faqs = [
        {"q": "Is there an entry fee?", "a": award["fee"] + "."},
        {"q": "Can I save and finish later?", "a": "Yes. Your form saves automatically and you can come back any time before the deadline."},
        {"q": "Who are the jury?", "a": "Senior people from industry and academia. Each one declares their links to organisations, so no one judges an entry they are connected to."},
    ] + award["extra_faqs"]

    return {
        "eligibility": award["eligibility"] or GENERIC_ELIGIBILITY,
        "steps": steps,
        "timeline": timeline,
        "criteria": award["criteria"] or GENERIC_CRITERIA,
        "round2_criteria": award["round2_criteria"] if award["rounds"] == 2 else [],
        "round2_label": award["rounds_info"][1]["label"] if award["rounds"] == 2 else "",
        "faqs": faqs,
    }


# --- Entries (applications) ------------------------------------------------

ENTRIES = {
    "A-0042": {"award": "business-excellence", "org": "Acme Precision Components Pvt Ltd"},
    "A-0051": {"award": "business-excellence", "org": "Shri Ganesh Polymers Ltd"},
    "A-0038": {"award": "business-excellence", "org": "Northstar Auto Components"},
    "K-0007": {"award": "kaizen", "org": "Acme Precision Components, Chakan plant"},
    "K-0012": {"award": "kaizen", "org": "Ganga Textiles, Unit 3"},
    "K-0003": {"award": "kaizen", "org": "Deccan Forge, Plant 2"},           # shortlisted for site visit
    "A-0029": {"award": "business-excellence", "org": "Vertex Pharma Labs"},  # shortlisted for live round
}


def entry_answers(entry_id):
    """Sample answers for an entry, in form order: list of sections with questions and values."""
    entry = ENTRIES[entry_id]
    award = get_award(entry["award"])
    sections = []
    for section in award["form_sections"]:
        questions = []
        for q in section["questions"]:
            value = entry["org"] if q.get("key") == "org" else q.get("sample", "")
            questions.append({**q, "value": value})
        sections.append({"name": section["name"], "questions": questions})
    return sections


def answers_for_judge(entry_id, award, round_name):
    """
    What a judge is allowed to see.                                   [Rule 1]

    In a blind award's desk-review rounds, identifying answers are removed
    and file names replaced HERE, before anything reaches the page. The
    template never receives the hidden values, so they can't leak through
    the HTML. Site visits and live presentations are never blind: the judge
    meets the applicant there.
    """
    hide = is_blind_round(award, round_name)
    sections = []
    file_no = 0
    for section in entry_answers(entry_id):
        questions = []
        for q in section["questions"]:
            value = q["value"]
            if hide and q["identifying"]:
                value = None
            elif hide and q["type"] == "file" and value:
                file_no += 1
                value = f"file-{file_no}.{value.rsplit('.', 1)[-1]} (name hidden)"
            questions.append({"label": q["label"], "type": q["type"], "value": value, "hidden": hide and q["identifying"]})
        sections.append({"name": section["name"], "questions": questions})
    return sections, hide


# --- Applicant portal -------------------------------------------------------

# The sample application data below belongs to this demo applicant only.
# Any other applicant who signs up starts with no applications (RBAC: an
# applicant sees only their own data).
SAMPLE_APPLICANT_EMAIL = "priya@acme.example"


def owns_sample_data(user):
    return user.email.lower() == SAMPLE_APPLICANT_EMAIL

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
     "status": "Draft", "progress": 40, "deadline": "30 Nov 2026", "form_version": "v2026.1"},
    {"id": "K-0007", "award": "Kaizen Competition", "slug": "kaizen",
     "status": "Submitted", "progress": 100, "deadline": "15 Dec 2026", "form_version": "v2026.1"},
    {"id": "A-0019", "award": "Business Excellence Award 2025", "slug": "business-excellence",
     "status": "Result: Finalist", "progress": 100, "deadline": "Closed", "form_version": "v2025.1"},
]

APPLICATION_TIMELINE = [
    {"label": "Submitted", "date": "2 Oct 2026", "state": "done"},
    {"label": "Eligibility checked", "date": "4 Oct 2026", "state": "done"},
    {"label": "Under review by jury", "date": "In progress", "state": "current"},
    {"label": "Results", "date": "Mar 2027", "state": "todo"},
]

# --- Judge portal -----------------------------------------------------------

# Demo judges, by login email. Each assignment below belongs to one judge;
# a judge only sees and opens their own assignments.
JUDGES = {
    "kapoor@judges.example": {"name": "Dr. R. Kapoor", "expertise": "Manufacturing, Quality"},
    "rao@judges.example": {"name": "Prof. N. Rao", "expertise": "Quality, Academia"},
}
JUDGE = JUDGES["kapoor@judges.example"]

ASSIGNMENTS = [
    {"judge": "kapoor@judges.example", "entry": "A-0042", "round": "Round 1", "status": "In progress", "progress": 67, "due": "15 Jan 2027"},
    {"judge": "kapoor@judges.example", "entry": "K-0007", "round": "Round 1", "status": "In progress", "progress": 50, "due": "20 Jan 2027"},
    {"judge": "kapoor@judges.example", "entry": "A-0051", "round": "Round 1", "status": "Awaiting response", "progress": 0, "due": "15 Jan 2027"},
    {"judge": "rao@judges.example", "entry": "K-0012", "round": "Round 1", "status": "Not started", "progress": 0, "due": "20 Jan 2027"},
    {"judge": "kapoor@judges.example", "entry": "A-0038", "round": "Round 1", "status": "Submitted", "progress": 100, "due": "15 Jan 2027"},
    {"judge": "kapoor@judges.example", "entry": "K-0003", "round": "Round 2", "status": "Visit scheduled", "progress": 0, "due": "5 Feb 2027",
     "visit": "5 Feb 2027, 10:00 · Deccan Forge, Plant 2, Hosur"},
    {"judge": "kapoor@judges.example", "entry": "A-0029", "round": "Round 2", "status": "Presentation scheduled", "progress": 0, "due": "12 Feb 2027",
     "visit": "12 Feb 2027, 14:30 · Awards Platform office, New Delhi"},
]

# Sample scores already entered, per entry (criterion name -> score, comment)
SAMPLE_SCORES = {
    "A-0042": {"Leadership and strategy": (8, "Clear, well-communicated strategy."), "Processes and people": (7, "")},
    "K-0007": {"Problem clarity": (9, "Problem measured precisely."), "Root cause found": (8, "")},
}

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

JUDGE_POOL = [
    {"name": "Dr. R. Kapoor", "expertise": "Manufacturing, Quality", "load": "5 / 15", "match": "Strong"},
    {"name": "Prof. N. Rao", "expertise": "Quality, Academia", "load": "3 / 15", "match": "Strong"},
    {"name": "Ms. A. Iyer", "expertise": "Strategy, Finance", "load": "7 / 15", "match": "Good"},
    {"name": "Mr. S. Bose", "expertise": "Operations", "load": "12 / 15", "match": "Good"},
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
     "detail": "Judge scores 4.1, 8.6 and 7.9: a gap of 4.5 points.", "action": "Add an extra judge"},
    {"type": "Tie", "award": "Safety Excellence Award", "entry": "S-0004 / S-0019",
     "detail": "Both entries average 8.20 for 3rd place.", "action": "Decide tie-break"},
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
        ("Awards", "awards:award_list"),
        ("Award settings", "awards:settings"),
        ("Form builder", "awards:form_builder"),
        ("Entries", "awards:entries"),
        ("Duplicate review", "awards:duplicates"),
        ("Assign judges", "awards:assign"),
    ],
    "leader": [
        ("Overview", "dashboard:overview"),
        ("All applications", "dashboard:review"),
        ("Approve results", "dashboard:results"),
        ("People", "dashboard:people"),
        ("Audit log", "dashboard:audit"),
    ],
}

ROLE_LABELS = {
    "applicant": "Applicant",
    "judge": "Judge",
    "staff": "Programme staff",
    "leader": "Leadership",
}


def assignments_for(user):
    """Only the assignments that belong to this judge."""
    return [a for a in ASSIGNMENTS if a["judge"] == user.email.lower()]


def blank_answers(slug):
    """An award's form with no answers yet (for an applicant starting fresh)."""
    award = get_award(slug)
    return [{"name": s["name"], "questions": [{**q, "value": ""} for q in s["questions"]]}
            for s in award["form_sections"]]
