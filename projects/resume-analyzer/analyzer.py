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
    cleaned_text = re.sub(r"[^a-zA-Z0-9+#.\s]", " ", text.lower())
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

    return cleaned_text


def has_skill(text, aliases):
    return any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases)


# ---------- ANALYZE ----------
def analyze_resume(text):

    text = text.lower()

    found = []

    for skill, keywords in skill_map.items():

        for keyword in keywords:

            if keyword in text:
                found.append(skill)
                break

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

def analyze_for_role(text, role):

    text = text.lower()

    required = job_roles[role]

    found = []

    for skill in required:

        keywords = skill_map[skill]

        for keyword in keywords:

            if keyword in text:
                found.append(skill)
                break

    found = sorted(list(set(found)))

    missing = sorted(
        list(set(required) - set(found))
    )

    score = int(
        (len(found) / len(required)) * 100
    )

    return {
        "role": role,
        "score": score,
        "found": found,
        "missing": missing
    }