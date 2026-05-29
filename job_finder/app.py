import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Finance Job Finder", page_icon="💼", layout="wide")

st.title("💼 Finance Job Finder")
st.markdown("Search remote finance jobs across multiple boards — no signup required")

DAYS_OPTIONS = {"Any time": None, "Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30}

REMOTIVE_CATEGORY = "finance-legal"


def fetch_remotive(search_term, job_type, limit):
    params = {"limit": limit, "category": REMOTIVE_CATEGORY}
    if search_term:
        params["search"] = search_term
    r = requests.get("https://remotive.com/api/remote-jobs", params=params, timeout=15)
    r.raise_for_status()
    jobs = r.json().get("jobs", [])
    if job_type:
        jobs = [j for j in jobs if j.get("job_type") == job_type]
    rows = []
    for j in jobs:
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
    return rows


def fetch_arbeitnow(search_term, limit):
    r = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
    r.raise_for_status()
    jobs = r.json().get("data", [])
    jobs = [j for j in jobs if j.get("remote")]
    if search_term:
        kw = search_term.lower()
        jobs = [j for j in jobs if kw in j.get("title", "").lower() or kw in " ".join(j.get("tags", [])).lower()]
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
    params = {"count": min(limit, 50), "industry": "finance"}
    if search_term:
        params["tag"] = search_term
    r = requests.get("https://jobicy.com/api/v2/remote-jobs", params=params, timeout=15)
    r.raise_for_status()
    jobs = r.json().get("jobs", [])
    rows = []
    for j in jobs:
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


with st.sidebar:
    st.header("Search Filters")
    search_term = st.text_input("Job Title / Keyword", value="finance manager")
    job_type = st.selectbox(
        "Job Type", ["", "full_time", "part_time", "contract", "freelance"],
        format_func=lambda x: "Any" if x == "" else x.replace("_", " ").title()
    )

    st.markdown("---")
    st.subheader("Job Sources")
    use_remotive = st.checkbox("Remotive", value=True)
    use_arbeitnow = st.checkbox("Arbeitnow", value=True)
    use_jobicy = st.checkbox("Jobicy", value=True)
    limit = st.slider("Max Results per Source", 10, 100, 30)

    st.markdown("---")
    st.subheader("Date Posted")
    days_label = st.selectbox("Posted Within", list(DAYS_OPTIONS.keys()))
    days_filter = DAYS_OPTIONS[days_label]

    st.markdown("---")
    st.subheader("Salary")
    salary_only = st.checkbox("Only jobs with salary listed")

    search_btn = st.button("Search Jobs", use_container_width=True)


if search_btn:
    with st.spinner("Fetching jobs from selected sources..."):
        all_rows = []
        errors = []

        if use_remotive:
            try:
                all_rows.extend(fetch_remotive(search_term, job_type, limit))
            except Exception as e:
                errors.append(f"Remotive: {e}")

        if use_arbeitnow:
            try:
                all_rows.extend(fetch_arbeitnow(search_term, limit))
            except Exception as e:
                errors.append(f"Arbeitnow: {e}")

        if use_jobicy:
            try:
                all_rows.extend(fetch_jobicy(search_term, limit))
            except Exception as e:
                errors.append(f"Jobicy: {e}")

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
            c3.metric("Sources Active", df["Source"].nunique())

            st.markdown("---")

            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                loc_filter = st.text_input("Filter by Region / Location", placeholder="e.g. USA, Europe, UK")
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
