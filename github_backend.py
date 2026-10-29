
import sqlite3
from datetime import datetime, timezone

# ------------------------------------------
# CONFIGURATION
# ------------------------------------------

DB_NAME = "github_portfolio.db"
USERNAME = "chakraborty-soumyo-18"


# ------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------

def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# ------------------------------------------
# CREATE DATABASE TABLES
# ------------------------------------------

def initialize_database():
    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS repository_cache (
                username TEXT NOT NULL,
                repo_name TEXT NOT NULL,
                stars INTEGER NOT NULL DEFAULT 0,
                forks INTEGER NOT NULL DEFAULT 0,
                language TEXT,
                description TEXT,
                updated_at TEXT,
                cached_at TEXT NOT NULL,
                PRIMARY KEY (username, repo_name)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                username TEXT PRIMARY KEY,
                job_description TEXT,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS contribution_cache (
                username TEXT NOT NULL,
                contribution_date TEXT NOT NULL,
                contribution_count INTEGER NOT NULL DEFAULT 0,
                cached_at TEXT NOT NULL,
                PRIMARY KEY (username, contribution_date)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_repo_username
            ON repository_cache(username)
        """)

    print("Database initialized successfully.")


# ------------------------------------------
# SAVE REPOSITORIES TO SQLITE
# ------------------------------------------

def save_repositories(username, repositories):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        for repo in repositories:
            conn.execute("""
                INSERT INTO repository_cache (
                    username, repo_name, stars, forks,
                    language, description, updated_at, cached_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username, repo_name)
                DO UPDATE SET
                    stars = excluded.stars,
                    forks = excluded.forks,
                    language = excluded.language,
                    description = excluded.description,
                    updated_at = excluded.updated_at,
                    cached_at = excluded.cached_at
            """, (
                username,
                repo.get("name", ""),
                repo.get("stargazers_count", 0),
                repo.get("forks_count", 0),
                repo.get("language"),
                repo.get("description"),
                repo.get("updated_at"),
                now
            ))

    print(f"Saved {len(repositories)} repositories to SQLite.")


# ------------------------------------------
# READ CACHED REPOSITORIES
# ------------------------------------------

def get_cached_repositories(username):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT repo_name, stars, forks, language,
                   description, updated_at, cached_at
            FROM repository_cache
            WHERE username = ?
            ORDER BY stars DESC, repo_name ASC
        """, (username,)).fetchall()

    return [dict(row) for row in rows]


# ------------------------------------------
# SAVE AND READ JOB DESCRIPTION
# ------------------------------------------

def save_job_description(username, job_description):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO user_settings (
                username, job_description, updated_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(username)
            DO UPDATE SET
                job_description = excluded.job_description,
                updated_at = excluded.updated_at
        """, (username, job_description, now))

    print("Job description saved.")


def get_job_description(username):
    with get_connection() as conn:
        row = conn.execute("""
            SELECT job_description
            FROM user_settings
            WHERE username = ?
        """, (username,)).fetchone()

    return row["job_description"] if row else None


# ------------------------------------------
# BASIC TECH STACK COMPATIBILITY
# ------------------------------------------

SKILLS = [
    "python", "java", "javascript", "typescript",
    "c++", "c#", "go", "rust", "sql", "r",
    "php", "ruby", "html", "css", "react",
    "angular", "vue", "node.js", "django",
    "flask", "fastapi", "streamlit",
    "machine learning", "deep learning",
    "data analysis", "pandas", "numpy",
    "tensorflow", "pytorch", "docker",
    "kubernetes", "aws", "azure", "git",
    "postgresql", "mysql", "mongodb", "sqlite"
]


def calculate_compatibility(username, job_description):
    repositories = get_cached_repositories(username)

    if not repositories:
        return {
            "score": 0,
            "matched": [],
            "missing": [],
            "message": "No cached repositories found. Sync repositories first."
        }

    # Primary repository languages only.
    repo_languages = {
        repo["language"].lower()
        for repo in repositories
        if repo.get("language")
    }

    jd = job_description.lower()

    # Find skills explicitly mentioned in the job description.
    required_skills = [
        skill for skill in SKILLS
        if skill in jd
    ]

    if not required_skills:
        return {
            "score": 0,
            "matched": [],
            "missing": [],
            "message": "No recognized skills found in the job description."
        }

    matched = [
        skill for skill in required_skills
        if skill in repo_languages
    ]

    missing = [
        skill for skill in required_skills
        if skill not in repo_languages
    ]

    score = round(len(matched) / len(required_skills) * 100, 2)

    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "message": (
            "Basic estimate based on primary repository languages; "
            "it does not verify every skill used inside a repository."
        )
    }


# ------------------------------------------
# DATABASE SUMMARY
# ------------------------------------------

def show_database_summary(username):
    repositories = get_cached_repositories(username)

    print("\n========== DATABASE SUMMARY ==========")
    print("GitHub username:", username)
    print("Cached repositories:", len(repositories))

    total_stars = sum(repo["stars"] for repo in repositories)
    total_forks = sum(repo["forks"] for repo in repositories)

    print("Total cached stars:", total_stars)
    print("Total cached forks:", total_forks)

    print("\nRepository list:")

    if not repositories:
        print("No repositories cached yet.")

    for repo in repositories:
        print(
            f"- {repo['repo_name']} | "
            f"Stars: {repo['stars']} | "
            f"Forks: {repo['forks']} | "
            f"Language: {repo['language'] or 'Not specified'}"
        )


# ------------------------------------------
# RUN BACKEND TESTS
# ------------------------------------------

def main():
    initialize_database()

    show_database_summary(USERNAME)

    print("\n========== COMPATIBILITY TEST ==========")

    sample_jd = """
    We are looking for a developer with Python, SQL,
    Git, and machine learning skills.
    """

    save_job_description(USERNAME, sample_jd)

    saved_jd = get_job_description(USERNAME)

    result = calculate_compatibility(USERNAME, saved_jd)

    print("Compatibility score:", result["score"], "%")
    print("Matched skills:", result["matched"])
    print("Missing skills:", result["missing"])
    print("Note:", result["message"])

    print("\nBackend test completed.")


if __name__ == "__main__":
    main()



import requests


def sync_github_repositories(username):
    """Fetch public GitHub repositories and cache them in SQLite."""

    api_url = f"https://api.github.com/users/{username}/repos"
    params = {
        "per_page": 100,
        "sort": "updated"
    }

    headers = {
        "Accept": "application/vnd.github+json"
    }

    all_repositories = []

    try:
        while api_url:
            response = requests.get(
                api_url,
                headers=headers,
                params=params,
                timeout=20
            )

            response.raise_for_status()
            page_data = response.json()

            all_repositories.extend(page_data)

            # Follow GitHub pagination when another page exists.
            next_url = None
            link_header = response.headers.get("Link", "")

            for link in link_header.split(","):
                if 'rel="next"' in link:
                    next_url = link.split(";")[0].strip().strip("<>")
                    break

            api_url = next_url
            params = None

        save_repositories(username, all_repositories)

        print(f"GitHub sync successful: {len(all_repositories)} repositories.")

    except requests.RequestException as error:
        print("GitHub API request failed:", error)
        print("Existing cached repository data has not been deliberately cleared.")


if __name__ == "__main__":
    print("\n========== GITHUB API SYNC ==========")
    sync_github_repositories(USERNAME)
    show_database_summary(USERNAME)



import os
import sqlite3
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ---------------- CONFIGURATION ----------------
USERNAME = "chakraborty-soumyo-18"
DB_NAME = "github_portfolio.db"
API = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

st.set_page_config(
    page_title="GitHub Developer Portfolio",
    page_icon="💻",
    layout="wide"
)


# ---------------- DATABASE ----------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS repository_cache (
                username TEXT NOT NULL,
                repo_name TEXT NOT NULL,
                stars INTEGER DEFAULT 0,
                forks INTEGER DEFAULT 0,
                language TEXT,
                description TEXT,
                updated_at TEXT,
                cached_at TEXT NOT NULL,
                PRIMARY KEY (username, repo_name)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                username TEXT PRIMARY KEY,
                job_description TEXT,
                updated_at TEXT NOT NULL
            )
        """)


def cached_repositories():
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(
            """SELECT repo_name, stars, forks, language,
                      description, updated_at, cached_at
               FROM repository_cache
               WHERE username = ?
               ORDER BY stars DESC""",
            conn,
            params=(USERNAME,)
        )


# ---------------- GITHUB API ----------------
def github_get(endpoint, params=None):
    response = requests.get(
        f"{API}/{endpoint}",
        headers=HEADERS,
        params=params,
        timeout=15
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, show_spinner=False)
def get_profile(username):
    return github_get(f"users/{username}")


@st.cache_data(ttl=300, show_spinner=False)
def get_repositories(username):
    repos = []
    page = 1

    while page <= 3:
        batch = github_get(
            f"users/{username}/repos",
            {"per_page": 100, "page": page, "sort": "updated"}
        )
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return repos


def sync_database(username, repos):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_NAME) as conn:
        for repo in repos:
            conn.execute("""
                INSERT INTO repository_cache
                (username, repo_name, stars, forks, language,
                 description, updated_at, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username, repo_name) DO UPDATE SET
                    stars=excluded.stars,
                    forks=excluded.forks,
                    language=excluded.language,
                    description=excluded.description,
                    updated_at=excluded.updated_at,
                    cached_at=excluded.cached_at
            """, (
                username,
                repo["name"],
                repo.get("stargazers_count", 0),
                repo.get("forks_count", 0),
                repo.get("language"),
                repo.get("description"),
                repo.get("updated_at"),
                now
            ))


# ---------------- JOB MATCH ----------------
SKILLS = [
    "python", "java", "javascript", "typescript", "c++",
    "sql", "r", "go", "rust", "html", "css", "react",
    "node.js", "django", "flask", "streamlit", "pandas",
    "numpy", "machine learning", "deep learning",
    "tensorflow", "pytorch", "docker", "kubernetes",
    "aws", "azure", "git", "mysql", "postgresql",
    "mongodb", "sqlite", "data analysis"
]


def compatibility(jd, repos):
    jd = jd.lower()
    required = [s for s in SKILLS if s in jd]

    # Language fields provide evidence only for repository
    # primary languages, not every technology used.
    languages = {
        str(r.get("language")).lower()
        for r in repos if r.get("language")
    }

    matched = [s for s in required if s in languages]
    missing = [s for s in required if s not in languages]
    score = round(100 * len(matched) / len(required), 1) if required else 0

    return score, matched, missing


# ---------------- DASHBOARD ----------------
init_db()

st.title("💻 GitHub Developer Portfolio")
st.caption(
    "Repository analytics • Public GitHub data • "
    "SQLite caching • Job skill matching"
)

with st.sidebar:
    st.header("Profile Settings")
    username = st.text_input("GitHub username", USERNAME).strip()
    st.caption("Data is retrieved from the public GitHub REST API.")
    refresh = st.button("🔄 Refresh GitHub data", use_container_width=True)

if not username:
    st.error("Enter a GitHub username.")
    st.stop()

try:
    with st.spinner("Loading GitHub profile and repositories..."):
        profile = get_profile(username)

        if refresh:
            get_profile.clear()
            get_repositories.clear()
            profile = get_profile(username)

        repos = get_repositories(username)

        if refresh or username == USERNAME:
            sync_database(username, repos)

except requests.RequestException as exc:
    st.error(f"GitHub API request failed: {exc}")
    st.info("Check the username, internet connection, or GitHub API rate limit.")
    st.stop()

df = pd.DataFrame(repos)

if df.empty:
    st.warning("No public repositories were found.")
    st.stop()

total_stars = int(df["stargazers_count"].fillna(0).sum())
total_forks = int(df["forks_count"].fillna(0).sum())

st.subheader(f"{profile.get('name') or username}")
if profile.get("bio"):
    st.write(profile["bio"])

st.markdown(f"[Open GitHub profile](https://github.com/{username})")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Public repositories", profile.get("public_repos", 0))
c2.metric("Followers", profile.get("followers", 0))
c3.metric("Total repository stars", total_stars)
c4.metric("Total forks", total_forks)

st.divider()

# Repository cards
st.subheader("📁 Repository Explorer")
search = st.text_input("Search repositories")
filtered = df.copy()

if search:
    filtered = filtered[
        filtered["name"].str.contains(search, case=False, na=False)
        | filtered["description"].fillna("").str.contains(
            search, case=False, na=False
        )
    ]

cols = st.columns(3)
for i, (_, repo) in enumerate(filtered.iterrows()):
    with cols[i % 3]:
        st.markdown(f"### [{repo['name']}]({repo['html_url']})")
        st.write(repo.get("description") or "No description provided.")
        st.caption(f"Language: {repo.get('language') or 'Not specified'}")
        st.write(
            f"⭐ {repo.get('stargazers_count', 0)}  "
            f"🍴 {repo.get('forks_count', 0)}"
        )

# Language chart
st.divider()
st.subheader("📊 Top Languages")

lang_df = df.dropna(subset=["language"])
if not lang_df.empty:
    counts = lang_df["language"].value_counts().rename_axis(
        "Language"
    ).reset_index(name="Repositories")
    fig = px.pie(
        counts,
        names="Language",
        values="Repositories",
        hole=0.45
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No primary language metadata is available.")

# Public activity proxy
st.divider()
st.subheader("🔥 Recent Public Activity")

st.caption(
    "This chart uses GitHub's public events API, which is limited "
    "and is not the complete contribution calendar."
)

try:
    events = github_get(f"users/{username}/events/public", {"per_page": 100})
    event_dates = [e["created_at"][:10] for e in events if e.get("created_at")]

    if event_dates:
        activity = pd.Series(event_dates).value_counts().to_dict()
        today = date.today()
        days = [
            (today - timedelta(days=i)).isoformat()
            for i in range(89, -1, -1)
        ]
        activity_df = pd.DataFrame({
            "Date": days,
            "Public events": [activity.get(d, 0) for d in days]
        })
        activity_df["Week"] = pd.to_datetime(
            activity_df["Date"]
        ).dt.isocalendar().week.astype(int)
        activity_df["Weekday"] = pd.to_datetime(
            activity_df["Date"]
        ).dt.day_name()

        fig = px.scatter(
            activity_df,
            x="Week",
            y="Weekday",
            color="Public events",
            hover_data=["Date"],
            color_continuous_scale="Greens",
            title="Public events by day (available recent events)"
        )
        fig.update_traces(marker={"symbol": "square", "size": 12})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("GitHub returned no recent public events.")
except requests.RequestException:
    st.info("Public activity data could not be loaded.")

# Compatibility analyzer
st.divider()
st.subheader("🎯 Tech Stack Compatibility Analyzer")

jd = st.text_area(
    "Paste the job description",
    placeholder="Paste required skills and technologies here...",
    height=180
)

if st.button("Calculate compatibility"):
    if not jd.strip():
        st.warning("Paste a job description first.")
    else:
        score, matched, missing = compatibility(jd, repos)
        st.metric("Estimated match", f"{score}%")
        st.caption(
            "This preliminary score matches recognized JD keywords "
            "against repository primary languages. It does not verify "
            "all skills used in code."
        )

        left, right = st.columns(2)
        left.markdown("**Matched primary languages**")
        left.write(", ".join(matched) if matched else "None identified")
        right.markdown("**Other recognized JD skills**")
        right.write(", ".join(missing) if missing else "None")

        from datetime import datetime, timezone
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                INSERT INTO user_settings
                (username, job_description, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    job_description=excluded.job_description,
                    updated_at=excluded.updated_at
            """, (
                username, jd,
                datetime.now(timezone.utc).isoformat()
            ))
        st.success("Job description saved in SQLite.")

# Extra feature 1: repository spotlight
st.divider()
st.subheader("🌟 Repository Spotlight")
top = df.sort_values("stargazers_count", ascending=False).iloc[0]
st.markdown(f"**[{top['name']}]({top['html_url']})**")
st.write(top.get("description") or "Add a repository description to improve your profile.")
st.caption("Tip: add a clear README, installation steps, screenshots, and example usage.")

# Extra feature 2: profile improvement checklist
st.subheader("🚀 Profile Improvement Assistant")
checks = {
    "Add a professional profile bio": bool(profile.get("bio")),
    "Add a portfolio website": bool(profile.get("blog")),
    "Add a profile location": bool(profile.get("location")),
    "Pin or showcase your best repositories": total_stars > 0,
    "Write useful repository descriptions": df["description"].notna().any()
}
for task, done in checks.items():
    st.write(f"{'✅' if done else '⬜'} {task}")

# Database status
st.divider()
with st.expander("Backend / SQLite status"):
    st.write("Database file:", DB_NAME)
    st.write("Cached repository rows:", len(cached_repositories()))
    st.write("Cache and profile API data may refresh independently.")
