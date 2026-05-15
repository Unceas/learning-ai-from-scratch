import re

# ---------- REQUIRED SKILLS ----------
required_skills = {
    "python",
    "machine",
    "learning",
    "sql",
    "react",
    "fastapi",
    "git"
}

# ---------- PREPROCESS ----------
def preprocess(text):

    text = text.lower()

    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

    words = text.split()

    return words

# ---------- ANALYZE ----------
def analyze_resume(text):

    words = preprocess(text)

    found = set()

    for word in words:
        if word in required_skills:
            found.add(word)

    missing = required_skills - found

    score = int((len(found) / len(required_skills)) * 100)

    return {
        "score": score,
        "found": sorted(list(found)),
        "missing": sorted(list(missing))
    }