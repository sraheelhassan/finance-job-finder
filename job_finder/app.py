import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Finance Job Finder", page_icon="💼", layout="wide")

st.title("💼 Accounting & Finance Job Finder")
st.markdown("Search remote & freelance finance and accounting jobs — no signup required")

REMOTIVE_CATEGORIES = ["finance-legal"]

REMOTIVE_SWEEP_TERMS = ["finance", "accounting", "accountant", "tax", "auditor", "cfo", "controller", "payroll", "bookkeeper", "treasury", "fp&a", "compliance"]

ADZUNA_COUNTRIES = ["us", "gb", "au", "ca", "in"]

FINANCE_KEYWORDS = [
    "finance", "financial", "accounting", "accountant", "cfo", "controller",
    "bookkeeper", "auditor", "tax", "payroll", "budget", "treasury", "analyst",
    "fp&a", "accounts", "billing", "invoice", "revenue", "compliance", "audit",
    "actuar", "cpa", "cma", "acca", "ifrs", "gaap", "reconcil", "forecas",
]

def is_finance_job(title):
    t = title.lower()
    return any(kw in t for kw in FINANCE_KEYWORDS)


def fetch_remotive(search_term, limit):
    rows = []
    seen = set()
    terms = [search_term] if search_term else REMOTIVE_SWEEP_TERMS
    for term in terms:
        params = {"limit": limit, "category": "finance-legal", "search": term}
        try:
            r = requests.get("https://remotive.com/api/remote-jobs", params=params, timeout=15)
            r.raise_for_status()
            for j in r.json().get("jobs", []):
                if j.get("id") not in seen:
                    seen.add(j.get("id"))
                    rows.append({
                        "Title": j.get("title", ""),
                        "Company": j.get("company_name", ""),
                        "Location": j.get("candidate_required_location") or "Worldwide",
                        "Type": j.get("job_type", "").replace("_", " ").title(),
                        "Salary": j.get("salary") or "",
                        "Posted": j.get("publication_date", "")[:10],
                        "Source": "Remotive",
                        "Apply": j.get("url", ""),
                    })
        except Exception:
            pass
    return rows


def fetch_arbeitnow(search_term, limit):
    r = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
    r.raise_for_status()
    jobs = r.json().get("data", [])
    jobs = [j for j in jobs if j.get("remote")]
    finance_kw = ["finance", "accounting", "accountant", "cfo", "controller", "bookkeeper", "auditor", "tax", "payroll", "budget"]
    if search_term:
        kw = search_term.lower()
        jobs = [j for j in jobs if kw in j.get("title", "").lower() or kw in " ".join(j.get("tags", [])).lower()]
    else:
        jobs = [j for j in jobs if any(k in j.get("title", "").lower() or k in " ".join(j.get("tags", [])).lower() for k in finance_kw)]
    rows = []
    for j in jobs[:limit]:
        created = j.get("created_at", "")
        posted = datetime.utcfromtimestamp(created).strftime("%Y-%m-%d") if isinstance(created, (int, float)) else str(created)[:10]
        rows.append({
            "Title": j.get("title", ""),
            "Company": j.get("company_name", ""),
            "Location": j.get("location") or "Worldwide",
            "Type": ", ".join(j.get("job_types", [])) or "Full Time",
            "Salary": "",
            "Posted": posted,
            "Source": "Arbeitnow",
            "Apply": j.get("url", ""),
        })
    return rows


def fetch_jobicy(search_term, limit):
    rows = []
    seen = set()
    for industry in ["finance", "accounting"]:
        params = {"count": min(limit, 50), "industry": industry}
        if search_term:
            params["tag"] = search_term
        r = requests.get("https://jobicy.com/api/v2/remote-jobs", params=params, timeout=15)
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            uid = j.get("id") or j.get("url", "")
            if uid not in seen:
                seen.add(uid)
                sal_min = j.get("annualSalaryMin")
                sal_max = j.get("annualSalaryMax")
                if sal_min and sal_max:
                    salary = f"${int(sal_min):,} – ${int(sal_max):,}"
                elif sal_min:
                    salary = f"${int(sal_min):,}+"
                else:
                    salary = ""
                rows.append({
                    "Title": j.get("jobTitle", ""),
                    "Company": j.get("companyName", ""),
                    "Location": j.get("jobGeo") or "Worldwide",
                    "Type": j.get("jobType", "").replace("-", " ").title(),
                    "Salary": salary,
                    "Posted": str(j.get("pubDate", ""))[:10],
                    "Source": "Jobicy",
                    "Apply": j.get("url", ""),
                })
    return rows


def fetch_remoteok(search_term, limit):
    headers = {"User-Agent": "FinanceJobFinder/1.0"}
    r = requests.get("https://remoteok.com/api?tags=finance,accounting", timeout=15, headers=headers)
    r.raise_for_status()
    jobs = [j for j in r.json() if isinstance(j, dict) and j.get("position")]
    if search_term:
        kw = search_term.lower()
        jobs = [j for j in jobs if kw in j.get("position", "").lower() or kw in " ".join(j.get("tags", [])).lower()]
    rows = []
    for j in jobs[:limit]:
        sal_min = j.get("salary_min")
        sal_max = j.get("salary_max")
        salary = f"${int(sal_min):,} – ${int(sal_max):,}" if sal_min and sal_max else (f"${int(sal_min):,}+" if sal_min else "")
        url = j.get("url", "")
        if url.startswith("/"):
            url = f"https://remoteok.com{url}"
        rows.append({
            "Title": j.get("position", ""),
            "Company": j.get("company", ""),
            "Location": j.get("location") or "Worldwide",
            "Type": "Remote",
            "Salary": salary,
            "Posted": str(j.get("date", ""))[:10],
            "Source": "RemoteOK",
            "Apply": url,
        })
    return rows


def fetch_adzuna(search_term, limit):
    app_id = st.secrets.get("ADZUNA_APP_ID", "")
    app_key = st.secrets.get("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        return []
    what = f"remote {search_term}" if search_term else "remote finance accounting"
    rows = []
    seen = set()
    for country in ADZUNA_COUNTRIES:
        try:
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": min(limit, 50),
                "what": what,
            }
            r = requests.get(f"https://api.adzuna.com/v1/api/jobs/{country}/search/1", params=params, timeout=15)
            r.raise_for_status()
            for j in r.json().get("results", []):
                uid = j.get("id", j.get("redirect_url", ""))
                if uid not in seen:
                    seen.add(uid)
                    sal_min = j.get("salary_min")
                    sal_max = j.get("salary_max")
                    sal = f"${int(sal_min):,} – ${int(sal_max):,}" if sal_min and sal_max else (f"${int(sal_min):,}+" if sal_min else "")
                    rows.append({
                        "Title": j.get("title", ""),
                        "Company": j.get("company", {}).get("display_name", ""),
                        "Location": j.get("location", {}).get("display_name", "Worldwide"),
                        "Type": j.get("contract_time", "").replace("_", " ").title(),
                        "Salary": sal,
                        "Posted": str(j.get("created", ""))[:10],
                        "Source": "Adzuna",
                        "Apply": j.get("redirect_url", ""),
                    })
        except Exception:
            pass
    return rows


def fetch_jooble(search_term, limit):
    api_key = st.secrets.get("JOOBLE_API_KEY", "")
    if not api_key:
        return []
    keywords = f"remote {search_term}" if search_term else "remote finance accounting"
    payload = {"keywords": keywords, "location": "", "resultsOnPage": min(limit, 20)}
    r = requests.post(f"https://jooble.org/api/{api_key}", json=payload, timeout=15)
    r.raise_for_status()
    rows = []
    for j in r.json().get("jobs", []):
        rows.append({
            "Title": j.get("title", ""),
            "Company": j.get("company", ""),
            "Location": j.get("location") or "Worldwide",
            "Type": j.get("type", "").replace("_", " ").title(),
            "Salary": j.get("salary", ""),
            "Posted": str(j.get("updated", ""))[:10],
            "Source": "Jooble",
            "Apply": j.get("link", ""),
        })
    return rows


col_search, col_btn = st.columns([5, 1])
with col_search:
    search_term = st.text_input("Job Title / Keyword", placeholder="e.g. CFO, accountant, financial analyst", label_visibility="collapsed")
with col_btn:
    search_btn = st.button("Search Jobs", use_container_width=True)

limit = 50

if search_btn:
    all_rows = []
    source_status = {}

    sources = [
        ("Remotive", fetch_remotive, (search_term, limit)),
        ("Arbeitnow", fetch_arbeitnow, (search_term, limit)),
        ("Jobicy", fetch_jobicy, (search_term, limit)),
        ("RemoteOK", fetch_remoteok, (search_term, limit)),
        ("Adzuna", fetch_adzuna, (search_term, limit)),
        ("Jooble", fetch_jooble, (search_term, limit)),
    ]

    with st.spinner("Fetching remote finance & accounting jobs..."):
        for name, fn, args in sources:
            try:
                results = fn(*args)
                all_rows.extend(results)
                source_status[name] = f"✅ {len(results)}"
            except Exception as e:
                source_status[name] = f"❌ {str(e)[:60]}"

    st.caption("  |  ".join([f"**{k}**: {v}" for k, v in source_status.items()]))

    if not all_rows:
        st.warning("No jobs found. Try a different keyword.")
    else:
        df = pd.DataFrame(all_rows)
        df = df[df["Title"].str.strip() != ""]
        if not search_term:
            df = df[df["Title"].apply(is_finance_job)]
        df = df.reset_index(drop=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Jobs", len(df))
        c2.metric("With Salary", (df["Salary"].str.strip() != "").sum())
        c3.metric("Sources", df["Source"].nunique())

        st.markdown(f"**Showing {len(df)} results**")

        st.dataframe(
            df,
            column_config={"Apply": st.column_config.LinkColumn("Apply", display_text="Apply")},
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "finance_jobs.csv", "text/csv", use_container_width=True)

else:
    st.info("Type a job title or keyword above and click **Search Jobs** to get started.")
