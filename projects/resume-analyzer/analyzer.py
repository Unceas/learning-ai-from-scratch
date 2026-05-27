import re

# ---------- REQUIRED SKILLS ----------
skill_map = {

    "python": [
        "python"
    ],

    "machine learning": [
        "machine learning",
        "ml",
        "scikit",
        "tensorflow",
        "pytorch"
    ],

    "sql": [
        "sql",
        "mysql",
        "postgresql"
    ],

    "react": [
        "react",
        "reactjs"
    ],

    "fastapi": [
        "fastapi",
        "api"
    ],

    "git": [
        "git",
        "github"
    ]
}


# ---------- JOB ROLES ----------
job_roles = {

    "ML Engineer": [
        "python",
        "machine learning",
        "sql",
        "git"
    ],

    "Backend Developer": [
        "python",
        "fastapi",
        "sql",
        "git"
    ],

    "Frontend Developer": [
        "react",
        "git"
    ]
}


# ---------- PREPROCESS ----------
def preprocess(text):

    cleaned_text = re.sub(
        r"[^a-zA-Z0-9+#.\s]",
        " ",
        text.lower()
    )

    cleaned_text = re.sub(
        r"\s+",
        " ",
        cleaned_text
    ).strip()

    return cleaned_text


# ---------- SKILL CHECK ----------
def has_skill(text, aliases):

    return any(
        re.search(
            rf"\b{re.escape(alias)}\b",
            text
        )
        for alias in aliases
    )

def keyword_density(text, aliases):

    total = 0

    for alias in aliases:

        matches = re.findall(
            rf"\b{re.escape(alias)}\b",
            text
        )

        total += len(matches)

    return total

# ---------- GENERIC ANALYSIS ----------
def analyze_resume(text):

    text = preprocess(text)

    found = []

    for skill, aliases in skill_map.items():

        if has_skill(text, aliases):
            found.append(skill)

    found = sorted(list(set(found)))

    missing = sorted(
        list(set(skill_map.keys()) - set(found))
    )

    score = int(
        (len(found) / len(skill_map)) * 100
    )

    return {
        "score": score,
        "found": found,
        "missing": missing
    }


# ---------- ROLE-BASED ANALYSIS ----------
def analyze_for_role(text, role):

    text = preprocess(text)

    required = job_roles[role]

    found = []

    keyword_scores = {}

    total_density = 0

    for skill in required:

        aliases = skill_map[skill]

        density = keyword_density(
            text,
            aliases
        )

        keyword_scores[skill] = density

        total_density += density

        if density > 0:
            found.append(skill)

    found = sorted(list(set(found)))

    missing = sorted(
        list(set(required) - set(found))
    )

    base_score = (
        len(found) / len(required)
    ) * 100

    # ATS optimization bonus
    density_bonus = min(total_density * 2, 20)

    score = int(
        min(base_score + density_bonus, 100)
    )

    return {
        "role": role,
        "score": score,
        "found": found,
        "missing": missing,
        "keyword_scores": keyword_scores
    }


# ---------- FEEDBACK GENERATION ----------
def generate_feedback(result):

    score = result["score"]
    missing = result["missing"]
    role = result["role"]

    feedback = []

    if score >= 80:

        feedback.append(
            f"Strong alignment for {role} roles."
        )

    elif score >= 50:

        feedback.append(
            f"Moderate match for {role}. Resume can be improved."
        )

    else:

        feedback.append(
            f"Weak match for {role}. Major skill gaps detected."
        )

    if missing:

        feedback.append(
            "Recommended skills to improve:"
        )

        for skill in missing:
            feedback.append(f"- {skill}")

    return feedback


def match_job_description(
    resume_text,
    job_description
):

    resume_text = preprocess(resume_text)
    job_description = preprocess(job_description)

    resume_words = set(resume_text.split())
    jd_words = set(job_description.split())

    common = resume_words.intersection(jd_words)

    missing = jd_words - resume_words

    if len(jd_words) == 0:
        score = 0
    else:
        score = int(
            (len(common) / len(jd_words)) * 100
        )

    return {
        "score": score,
        "matched": sorted(list(common)),
        "missing": sorted(list(missing))[:20]
    }