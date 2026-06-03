import re


# ---------- REQUIRED SKILLS ----------
skill_map = {
    "python": ["python"],
    "machine learning": ["machine learning", "ml", "mlops"],
    "data analysis": ["data analysis", "analytics"],
    "sql": ["sql", "mysql", "postgres", "postgresql"],
    "react": ["react", "reactjs", "react.js"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "azure": ["azure", "microsoft azure"],
    "mongodb": ["mongodb", "mongo db", "mongo"],
    "postgresql": ["postgresql", "postgres", "postgre sql"],
    "redis": ["redis"],
    "nodejs": ["nodejs", "node js", "node.js", "node"],
    "express": ["express", "expressjs", "express.js"],
    "numpy": ["numpy"],
    "pandas": ["pandas"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch", "torch"],
    "langchain": ["langchain"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "git": ["git", "github", "gitlab"],
}


# ---------- JOB ROLES ----------
job_roles = {
    "ML Engineer": [
        "python",
        "machine learning",
        "numpy",
        "pandas",
        "scikit-learn",
        "tensorflow",
        "pytorch",
        "docker",
        "fastapi",
        "git",
    ],
    "Data Analyst": [
        "python",
        "data analysis",
        "sql",
        "pandas",
        "numpy",
        "postgresql",
        "git",
    ],
    "Data Scientist": [
        "python",
        "machine learning",
        "numpy",
        "pandas",
        "scikit-learn",
        "sql",
        "tensorflow",
        "pytorch",
    ],
    "Backend Developer": [
        "python",
        "fastapi",
        "django",
        "flask",
        "nodejs",
        "express",
        "sql",
        "postgresql",
        "redis",
        "mongodb",
        "docker",
        "git",
    ],
    "Frontend Developer": [
        "react",
        "nodejs",
        "express",
        "git",
        "docker",
    ],
    "Full Stack Developer": [
        "react",
        "python",
        "nodejs",
        "express",
        "fastapi",
        "django",
        "flask",
        "sql",
        "postgresql",
        "mongodb",
        "redis",
        "docker",
        "git",
    ],
    "DevOps Engineer": [
        "docker",
        "kubernetes",
        "aws",
        "gcp",
        "azure",
        "git",
        "python",
    ],
    "AI Engineer": [
        "python",
        "machine learning",
        "langchain",
        "fastapi",
        "docker",
        "tensorflow",
        "pytorch",
        "scikit-learn",
        "aws",
    ],
}


# ---------- MATCH CATEGORY ----------
def classify_match(score):
    if score >= 90:
        return "Excellent Match"
    if score >= 75:
        return "Strong Match"
    if score >= 60:
        return "Moderate Match"
    return "Weak Match"


# ---------- PREPROCESS ----------
def preprocess(text):
    cleaned_text = re.sub(r"[^a-zA-Z0-9+#.\s]", " ", text.lower())
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()
    return cleaned_text


def _alias_pattern(alias):
    tokens = re.findall(r"[a-z0-9+#]+", alias.lower())
    if not tokens:
        return None
    return r"\b" + r"[\W_]*".join(map(re.escape, tokens)) + r"\b"


# ---------- SKILL CHECK ----------
def has_skill(text, aliases):
    return any(
        re.search(_alias_pattern(alias), text)
        for alias in aliases
        if _alias_pattern(alias)
    )


def keyword_density(text, aliases):
    total = 0
    for alias in aliases:
        pattern = _alias_pattern(alias)
        if not pattern:
            continue
        matches = re.findall(pattern, text)
        total += len(matches)
    return total


def _build_strengths(found, keyword_scores=None):
    if keyword_scores:
        ranked = sorted(
            ((skill, density) for skill, density in keyword_scores.items() if density > 0),
            key=lambda item: (-item[1], item[0]),
        )
        if ranked:
            return [f"{skill} ({density} mentions)" for skill, density in ranked]
    return sorted(found)


def _build_recommendations(missing, role=None):
    if not missing:
        if role:
            return [f"Keep tailoring the resume to {role} responsibilities and project keywords."]
        return ["Keep reinforcing the strongest keywords with project evidence."]

    recs = [f"Add clearer evidence for {skill}." for skill in missing]
    if role:
        recs.append(f"Reframe one project to highlight {role} impact.")
    return recs


# ---------- GENERIC ANALYSIS ----------
def analyze_resume(text):
    text = preprocess(text)
    found = []

    for skill, aliases in skill_map.items():
        if has_skill(text, aliases):
            found.append(skill)

    found = sorted(set(found))
    missing = sorted(set(skill_map.keys()) - set(found))
    score = int((len(found) / len(skill_map)) * 100)

    return {
        "score": score,
        "label": classify_match(score),
        "found": found,
        "strengths": _build_strengths(found),
        "missing": missing,
        "recommendations": _build_recommendations(missing),
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
        density = keyword_density(text, aliases)
        keyword_scores[skill] = density
        total_density += density
        if density > 0:
            found.append(skill)

    found = sorted(set(found))
    missing = sorted(set(required) - set(found))
    base_score = (len(found) / len(required)) * 100

    # ATS optimization bonus
    density_bonus = min(total_density * 2, 20)
    score = int(min(base_score + density_bonus, 100))

    return {
        "role": role,
        "score": score,
        "label": classify_match(score),
        "found": found,
        "strengths": _build_strengths(found, keyword_scores),
        "missing": missing,
        "recommendations": _build_recommendations(missing, role),
        "keyword_scores": keyword_scores,
    }


# ---------- FEEDBACK GENERATION ----------
def generate_feedback(result):
    score = result["score"]
    missing = result["missing"]
    strengths = result.get("strengths", [])
    role = result.get("role", "this role")

    feedback = [f"{classify_match(score)} for {role}."]

    if strengths:
        feedback.append("Strengths detected:")
        feedback.extend([f"- {skill}" for skill in strengths[:8]])

    if missing:
        feedback.append("Recommended skills to improve:")
        feedback.extend([f"- {skill}" for skill in missing[:8]])

    return feedback


def match_job_description(resume_text, job_description):
    resume_text = preprocess(resume_text)
    job_description = preprocess(job_description)

    resume_words = set(resume_text.split())
    jd_words = set(job_description.split())

    common = resume_words.intersection(jd_words)
    missing = jd_words - resume_words

    if len(jd_words) == 0:
        score = 0
    else:
        score = int((len(common) / len(jd_words)) * 100)

    return {
        "score": score,
        "label": classify_match(score),
        "matched": sorted(list(common)),
        "strengths": sorted(list(common)),
        "missing": sorted(list(missing))[:20],
        "recommendations": _build_recommendations(sorted(list(missing))[:20]),
    }
