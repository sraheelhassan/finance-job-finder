import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Job Finder", page_icon="💼", layout="wide")

st.title("💼 Job Finder")
st.markdown("Search remote jobs across the web — no signup required")

REMOTIVE_CATEGORIES = [
    "software-dev", "customer-support", "design", "marketing",
    "sales", "product", "business", "data", "devops-sysadmin",
    "finance-legal", "hr", "qa", "writing", "all-other"
]

with st.sidebar:
    st.header("Search Filters")
    search_term = st.text_input("Job Title / Keyword", value="data analyst")
    category = st.selectbox("Category", [""] + REMOTIVE_CATEGORIES, format_func=lambda x: "All Categories" if x == "" else x.replace("-", " ").title())
    job_type = st.selectbox("Job Type", ["", "full_time", "part_time", "contract", "freelance"], format_func=lambda x: "Any" if x == "" else x.replace("_", " ").title())
    limit = st.slider("Max Results", 10, 100, 30)
    search_btn = st.button("Search Jobs", use_container_width=True)

if search_btn:
    with st.spinner("Fetching jobs..."):
        try:
            params = {"limit": limit}
            if category:
                params["category"] = category
            if search_term:
                params["search"] = search_term

            r = requests.get("https://remotive.com/api/remote-jobs", params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            jobs = data.get("jobs", [])

            if job_type:
                jobs = [j for j in jobs if j.get("job_type") == job_type]

            if not jobs:
                st.warning("No jobs found. Try different keywords or filters.")
            else:
                st.success(f"Found **{len(jobs)}** jobs!")

                rows = []
                for j in jobs:
                    rows.append({
                        "Title": j.get("title", ""),
                        "Company": j.get("company_name", ""),
                        "Category": j.get("category", ""),
                        "Type": j.get("job_type", "").replace("_", " ").title(),
                        "Location": j.get("candidate_required_location") or "Worldwide",
                        "Salary": j.get("salary") or "Not listed",
                        "Posted": j.get("publication_date", "")[:10],
                        "Apply": j.get("url", ""),
                    })

                df = pd.DataFrame(rows)

                # Filters
                col1, col2 = st.columns(2)
                with col1:
                    loc_filter = st.text_input("Filter by Location", placeholder="e.g. USA, Europe")
                with col2:
                    company_filter = st.text_input("Filter by Company", placeholder="e.g. Google")

                if loc_filter:
                    df = df[df["Location"].str.contains(loc_filter, case=False, na=False)]
                if company_filter:
                    df = df[df["Company"].str.contains(company_filter, case=False, na=False)]

                st.markdown(f"**Showing {len(df)} results**")

                # Display with clickable links
                st.dataframe(
                    df,
                    column_config={"Apply": st.column_config.LinkColumn("Apply", display_text="Apply")},
                    use_container_width=True,
                    hide_index=True,
                )

                # Export
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, "jobs.csv", "text/csv", use_container_width=True)

        except Exception as e:
            st.error(f"Error fetching jobs: {e}")
else:
    st.info("Set your filters in the sidebar and click **Search Jobs** to get started.")
