import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Finance Job Finder", page_icon="💼", layout="wide")

st.title("💼 Finance Job Finder")
st.markdown("Search remote finance & accounting jobs across multiple boards — no signup required")

DAYS_OPTIONS = {"Any time": None, "Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30}

REMOTIVE_CATEGORIES = ["finance-legal", "business"]


def fetch_remotive(search_term, job_type, limit):
    rows = []
    seen = set()
    for cat in REMOTIVE_CATEGORIES:
        params = {"limit": limit, "category": cat}
        if search_term:
            params["search"] = search_term
        try:
            r = requests.get("https://remotive.com/api/remote-jobs", params=params, timeout=15)
            r.raise_for_status()
            jobs = r.json().get("jobs", [])
            if job_type:
                jobs = [j for j in jobs if j.get("job_type") == job_type]
            for j in jobs:
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
    if search_term:
        kw = search_term.lower()
        jobs = [j for j in jobs if kw in j.get("title", "").lower() or kw in " ".join(j.get("tags", [])).lower()]
    else:
        finance_kw = ["finance", "accounting", "accountant", "cfo", "controller", "bookkeeper", "auditor", "tax"]
        jobs = [j for j in jobs if any(kw in j.get("title", "").lower() or kw in " ".join(j.get("tags", [])).lower() for kw in finance_kw)]
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
        try:
            r = requests.get("https://jobicy.com/api/v2/remote-jobs", params=params, timeout=15)
            r.raise_for_status()
            jobs = r.json().get("jobs", [])
            for j in jobs:
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
        except Exception:
            pass
    return rows


def fetch_remoteok(search_term, limit):
    headers = {"User-Agent": "FinanceJobFinder/1.0"}
    r = requests.get("https://remoteok.com/api?tags=finance,accounting", timeout=15, headers=headers)
    r.raise_for_status()
    data = r.json()
    jobs = [j for j in data if isinstance(j, dict) and j.get("position")]
    if search_term:
        kw = search_term.lower()
        jobs = [j for j in jobs if kw in j.get("position", "").lower() or kw in " ".join(j.get("tags", [])).lower()]
    rows = []
    for j in jobs[:limit]:
        sal_min = j.get("salary_min")
        sal_max = j.get("salary_max")
        if sal_min and sal_max:
            salary = f"${int(sal_min):,} – ${int(sal_max):,}"
        elif sal_min:
            salary = f"${int(sal_min):,}+"
        else:
            salary = ""
        rows.append({
            "Title": j.get("position", ""),
            "Company": j.get("company", ""),
            "Location": j.get("location") or "Worldwide",
            "Type": "Full Time",
            "Salary": salary,
            "Posted": str(j.get("date", ""))[:10],
            "Source": "RemoteOK",
            "Apply": j.get("url", ""),
        })
    return rows


def fetch_adzuna(search_term, limit):
    app_id = st.secrets.get("ADZUNA_APP_ID", "")
    app_key = st.secrets.get("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        return []
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": min(limit, 50),
        "what": search_term or "finance accounting",
        "content-type": "application/json",
    }
    r = requests.get("https://api.adzuna.com/v1/api/jobs/us/search/1", params=params, timeout=15)
    r.raise_for_status()
    jobs = r.json().get("results", [])
    rows = []
    for j in jobs:
        sal = ""
        sal_min = j.get("salary_min")
        sal_max = j.get("salary_max")
        if sal_min and sal_max:
            sal = f"${int(sal_min):,} – ${int(sal_max):,}"
        elif sal_min:
            sal = f"${int(sal_min):,}+"
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
    return rows


with st.sidebar:
    st.header("Search Filters")
    search_term = st.text_input("Job Title / Keyword", value="finance manager")

    with st.expander("Job Type"):
        job_type = st.selectbox(
            "Job Type", ["", "full_time", "part_time", "contract", "freelance"],
            format_func=lambda x: "Any" if x == "" else x.replace("_", " ").title(),
            label_visibility="collapsed"
        )

    with st.expander("Max Results"):
        limit = st.slider("Max Results per Source", 10, 100, 30, label_visibility="collapsed")

    with st.expander("Date Posted"):
        days_label = st.selectbox("Posted Within", list(DAYS_OPTIONS.keys()), label_visibility="collapsed")
        days_filter = DAYS_OPTIONS[days_label]

    with st.expander("Salary"):
        salary_only = st.checkbox("Only jobs with salary listed")

    search_btn = st.button("Search Jobs", use_container_width=True)


if search_btn:
    with st.spinner("Fetching finance & accounting jobs..."):
        all_rows = []
        errors = []

        for name, fn, args in [
            ("Remotive", fetch_remotive, (search_term, job_type, limit)),
            ("Arbeitnow", fetch_arbeitnow, (search_term, limit)),
            ("Jobicy", fetch_jobicy, (search_term, limit)),
            ("RemoteOK", fetch_remoteok, (search_term, limit)),
            ("Adzuna", fetch_adzuna, (search_term, limit)),
        ]:
            try:
                all_rows.extend(fn(*args))
            except Exception as e:
                errors.append(f"{name}: {e}")

        for err in errors:
            st.warning(f"Could not fetch from {err}")

        if not all_rows:
            st.warning("No jobs found. Try different keywords or filters.")
        else:
            df = pd.DataFrame(all_rows)

            if days_filter:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days_filter)).date()
                df["_posted_dt"] = pd.to_datetime(df["Posted"], errors="coerce").dt.date
                df = df[df["_posted_dt"].notna() & (df["_posted_dt"] >= cutoff)]
                df = df.drop(columns=["_posted_dt"])

            if salary_only:
                df = df[df["Salary"].str.strip() != ""]

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Jobs", len(df))
            c2.metric("With Salary", (df["Salary"].str.strip() != "").sum())
            c3.metric("Sources", df["Source"].nunique())

            st.markdown("---")

            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                loc_filter = st.text_input("Filter by Location", placeholder="e.g. USA, Pakistan, UK")
            with fc2:
                company_filter = st.text_input("Filter by Company", placeholder="e.g. Deloitte, KPMG")
            with fc3:
                source_options = df["Source"].unique().tolist()
                source_filter = st.multiselect("Filter by Source", source_options, default=source_options)

            if loc_filter:
                df = df[df["Location"].str.contains(loc_filter, case=False, na=False)]
            if company_filter:
                df = df[df["Company"].str.contains(company_filter, case=False, na=False)]
            if source_filter:
                df = df[df["Source"].isin(source_filter)]

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
    st.info("Set your filters in the sidebar and click **Search Jobs** to get started.")
