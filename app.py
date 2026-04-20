import textwrap

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Freelance Capital Finder",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: #f6f8fc;
    }
    .block-container {
        max-width: 1350px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #214fc6;
        font-weight: 800;
    }
    .hero {
        background: linear-gradient(135deg, #ffffff 0%, #eef4ff 100%);
        border: 1px solid #d8e4ff;
        border-radius: 24px;
        padding: 1.4rem 1.4rem 1rem 1.4rem;
        box-shadow: 0 10px 30px rgba(33,79,198,0.08);
        margin-bottom: 1rem;
    }
    .metric-card {
        background: white;
        border: 1px solid #e4e9f5;
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 6px 20px rgba(17, 24, 39, 0.05);
    }
    .section-card {
        background: white;
        border: 1px solid #e4e9f5;
        border-radius: 20px;
        padding: 1rem 1rem 0.6rem 1rem;
        box-shadow: 0 6px 18px rgba(17,24,39,0.05);
        margin-bottom: 1rem;
    }
    .step-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin-top: 0.75rem;
        margin-bottom: 0.25rem;
    }
    .step-card {
        background: linear-gradient(135deg, #4a86f2 0%, #3f79e4 100%);
        color: white;
        border-radius: 18px;
        padding: 0.9rem;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 10px 20px rgba(63,121,228,0.18);
    }
    .step-badge {
        display: inline-flex;
        width: 38px;
        height: 38px;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        background: #31c7be;
        color: white;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .small-note {
        color: #5b6476;
        font-size: 0.92rem;
    }
    @media (max-width: 900px) {
        .step-grid { grid-template-columns: 1fr 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Data loading
# -----------------------------
@st.cache_data

def load_data():
    df = pd.read_csv("freelance_zip_data.csv")

    df["zip"] = (
        df["zip"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.replace(r"\D", "", regex=True)
        .str.zfill(5)
    )

    numeric_cols = [
        "returns",
        "wages",
        "self_employed_income",
        "freelance_ratio",
        "freelance_score",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=numeric_cols).copy()
    return df


def classify_zip(ratio: float) -> str:
    if ratio >= 0.10:
        return "Freelance Heavy"
    if ratio >= 0.05:
        return "Balanced"
    return "Salary Heavy"



def format_money(value: float) -> str:
    if value >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value/1_000:.1f}K"
    return f"${value:,.0f}"



def build_zip_summary(row: pd.Series) -> str:
    reasons = []
    if row["freelance_ratio"] >= 0.10:
        reasons.append("very high self-employment share")
    elif row["freelance_ratio"] >= 0.05:
        reasons.append("healthy mix of salaried and self-employed activity")
    else:
        reasons.append("more salary-heavy than freelance-heavy")

    if row["freelance_score"] >= row.get("score_q75", row["freelance_score"]):
        reasons.append("strong overall freelance score")

    if row["returns"] >= row.get("returns_q75", row["returns"]):
        reasons.append("large tax return volume")

    if row["self_employed_income"] >= row.get("sei_q75", row["self_employed_income"]):
        reasons.append("strong self-employment income base")

    reasons_text = ", ".join(reasons[:3])
    return (
        f"ZIP **{row['zip']}** is classified as **{row['category']}** because it has a "
        f"freelance ratio of **{row['freelance_ratio']:.2%}**, a freelance score of "
        f"**{row['freelance_score']:.3f}**, and approximately **{int(row['returns']):,}** returns. "
        f"That suggests {reasons_text}."
    )



def recommend_targets(data: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    rec = data.copy()
    rec["target_priority"] = (
        rec["freelance_score"].rank(pct=True) * 0.45
        + rec["freelance_ratio"].rank(pct=True) * 0.35
        + rec["returns"].rank(pct=True) * 0.20
    )
    return rec.sort_values("target_priority", ascending=False).head(n).copy()



def answer_question(question: str, data: pd.DataFrame, top_zip: pd.DataFrame) -> str:
    q = question.lower().strip()
    if not q:
        return "Type a question to generate an answer from the dashboard data."

    if "best" in q or "target" in q or "recommend" in q:
        rec = recommend_targets(data, n=3)
        lines = []
        for _, row in rec.iterrows():
            lines.append(
                f"ZIP {row['zip']} stands out with freelance ratio {row['freelance_ratio']:.2%}, "
                f"freelance score {row['freelance_score']:.3f}, and {int(row['returns']):,} returns."
            )
        return "Top marketing targets based on the current filters:\n\n- " + "\n- ".join(lines)

    if "hotspot" in q or "why" in q:
        row = top_zip.iloc[0]
        return build_zip_summary(row)

    if "how many" in q and ("zip" in q or "zips" in q):
        return (
            f"The current filtered dataset contains **{len(data):,} ZIP codes**. "
            f"Out of these, **{(data['category'] == 'Freelance Heavy').sum():,}** are Freelance Heavy, "
            f"**{(data['category'] == 'Balanced').sum():,}** are Balanced, and "
            f"**{(data['category'] == 'Salary Heavy').sum():,}** are Salary Heavy."
        )

    if "average" in q and "ratio" in q:
        return (
            f"The average freelance ratio in the current filtered view is "
            f"**{data['freelance_ratio'].mean():.2%}**."
        )

    if "income" in q:
        top_income = data.sort_values("self_employed_income", ascending=False).head(3)
        bullets = [
            f"ZIP {r['zip']} with {format_money(r['self_employed_income'])} in self-employment income"
            for _, r in top_income.iterrows()
        ]
        return "Top ZIP codes by self-employment income:\n\n- " + "\n- ".join(bullets)

    return (
        "I can answer questions about top target ZIPs, hotspot reasons, counts, categories, "
        "freelance ratio, and income patterns from the current filtered dataset."
    )



def step_section(title: str, items: list[str]):
    st.markdown(f"<div class='section-card'><h2 style='margin-bottom:0.3rem;'>{title}</h2>", unsafe_allow_html=True)
    cards = []
    for i, item in enumerate(items, start=1):
        cards.append(
            f"<div><div class='step-badge'>{i}</div><div class='step-card'>{item}</div></div>"
        )
    st.markdown(f"<div class='step-grid'>{''.join(cards)}</div></div>", unsafe_allow_html=True)


# -----------------------------
# Main app
# -----------------------------
df = load_data()
df["category"] = df["freelance_ratio"].apply(classify_zip)

score_q75 = df["freelance_score"].quantile(0.75)
returns_q75 = df["returns"].quantile(0.75)
sei_q75 = df["self_employed_income"].quantile(0.75)

st.markdown(
    """
    <div class='hero'>
        <h1 style='margin-bottom:0.4rem;'>Team 8 – Freelance Capital Finder</h1>
        <p style='font-size:1.05rem; margin-bottom:0.25rem;'>Identify ZIP codes with stronger self-employment activity for targeted freelancer tax app marketing.</p>
        <p class='small-note'>This dashboard combines ZIP-level economic indicators, market segmentation, map visualization, and AI-style insight generation for presentation-ready storytelling.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar
st.sidebar.header("Filters")
min_returns = st.sidebar.slider(
    "Minimum number of returns",
    int(df["returns"].min()),
    int(df["returns"].max()),
    max(100, int(df["returns"].min())),
)

top_n = st.sidebar.slider("Top N ZIP codes", 5, 25, 10)

all_categories = sorted(df["category"].unique())
selected_categories = st.sidebar.multiselect(
    "ZIP category",
    options=all_categories,
    default=all_categories,
)

zip_search = st.sidebar.text_input("Search ZIP code", placeholder="Example: 98001")

filtered_df = df[df["returns"] >= min_returns].copy()
filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)].copy()
if zip_search.strip():
    filtered_df = filtered_df[filtered_df["zip"].str.contains(zip_search.strip())].copy()

if filtered_df.empty:
    st.warning("No rows match the current filters. Reduce the minimum returns or change the selected categories.")
    st.stop()

filtered_df["score_q75"] = score_q75
filtered_df["returns_q75"] = returns_q75
filtered_df["sei_q75"] = sei_q75

top_zip = filtered_df.sort_values("freelance_score", ascending=False).head(top_n).copy()
target_df = recommend_targets(filtered_df, n=min(5, len(filtered_df)))

# KPI row
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Filtered ZIP Codes", f"{len(filtered_df):,}")
with c2:
    st.metric("Avg Freelance Ratio", f"{filtered_df['freelance_ratio'].mean():.2%}")
with c3:
    st.metric("Top ZIP", top_zip.iloc[0]["zip"])
with c4:
    st.metric("Highest Score", f"{top_zip.iloc[0]['freelance_score']:.3f}")

# Charts
left, right = st.columns((1.15, 0.85))
with left:
    st.subheader("Top ZIP Codes by Freelance Score")
    fig_bar, ax_bar = plt.subplots(figsize=(10, 5.5))
    ax_bar.barh(top_zip["zip"].astype(str), top_zip["freelance_score"])
    ax_bar.set_xlabel("Freelance Score")
    ax_bar.set_ylabel("ZIP Code")
    ax_bar.invert_yaxis()
    ax_bar.grid(axis="x", linestyle="--", alpha=0.3)
    st.pyplot(fig_bar, clear_figure=True)

with right:
    st.subheader("ZIP Market Segmentation")
    category_counts = filtered_df["category"].value_counts().reindex(all_categories, fill_value=0)
    fig_cat, ax_cat = plt.subplots(figsize=(7, 5.5))
    ax_cat.bar(category_counts.index, category_counts.values)
    ax_cat.set_xlabel("Category")
    ax_cat.set_ylabel("ZIP Count")
    plt.xticks(rotation=20)
    ax_cat.grid(axis="y", linestyle="--", alpha=0.3)
    st.pyplot(fig_cat, clear_figure=True)

st.subheader("Wages vs Self-Employment Income")
fig_scatter, ax_scatter = plt.subplots(figsize=(11, 5.5))
for category in selected_categories:
    cat_df = filtered_df[filtered_df["category"] == category]
    if not cat_df.empty:
        ax_scatter.scatter(
            cat_df["wages"],
            cat_df["self_employed_income"],
            alpha=0.65,
            label=category,
        )
ax_scatter.set_xlabel("Wages (USD)")
ax_scatter.set_ylabel("Self-Employment Income (USD)")
ax_scatter.set_title("ZIP Code Economic Activity")
ax_scatter.legend()
ax_scatter.grid(alpha=0.25)
st.pyplot(fig_scatter, clear_figure=True)

# Map
st.subheader("Map Visualization")
map_tab1, map_tab2 = st.tabs(["US ZIP Map", "Map Notes"])
with map_tab1:
    try:
        import pgeocode
        import pydeck as pdk

        nomi = pgeocode.Nominatim("us")
        coords = nomi.query_postal_code(filtered_df["zip"].tolist())

        map_df = filtered_df.copy()
        map_df["lat"] = coords["latitude"].values
        map_df["lon"] = coords["longitude"].values
        map_df = map_df.dropna(subset=["lat", "lon"]).copy()

        if not map_df.empty:
            st.success(f"Showing {len(map_df):,} ZIP codes on the US map.")
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=map_df,
                get_position="[lon, lat]",
                get_radius=2200,
                get_fill_color="[44, 123, 229, 150]",
                pickable=True,
            )
            tooltip = {
                "html": "<b>ZIP:</b> {zip}<br/><b>Category:</b> {category}<br/><b>Freelance Ratio:</b> {freelance_ratio}<br/><b>Score:</b> {freelance_score}",
                "style": {"backgroundColor": "white", "color": "black"},
            }
            view_state = pdk.ViewState(latitude=39.5, longitude=-98.35, zoom=3.2, pitch=0)
            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))
        else:
            st.warning("No valid ZIP coordinates were found for the current filter selection.")
    except ModuleNotFoundError:
        st.info("Map dependencies are not installed yet. Run: pip install pgeocode pydeck")
    except Exception as e:
        st.error(f"Map could not be rendered: {e}")

with map_tab2:
    st.markdown(
        """
        - This map converts US ZIP codes into latitude and longitude dynamically.
        - It avoids the ZIP mismatch problem caused by small sample `zip_lat_lon.csv` files.
        - For presentation, this is stronger because it scales to the filtered dataset automatically.
        """
    )

# AI-like insight section
st.subheader("AI Insight Studio")
insight_tab1, insight_tab2, insight_tab3, insight_tab4 = st.tabs(
    [
        "Why this ZIP is a hotspot",
        "Recommend target ZIPs",
        "Ask natural-language questions",
        "Which ZIP codes should we target and why?",
    ]
)

with insight_tab1:
    selected_zip = st.selectbox("Select a ZIP code for explanation", options=filtered_df["zip"].tolist(), index=0)
    selected_row = filtered_df[filtered_df["zip"] == selected_zip].iloc[0]
    st.markdown(build_zip_summary(selected_row))

with insight_tab2:
    st.write("Recommended target ZIP codes based on freelance score, freelance ratio, and tax return volume.")
    display_targets = target_df[["zip", "returns", "freelance_ratio", "freelance_score", "category"]].copy()
    display_targets["freelance_ratio"] = display_targets["freelance_ratio"].map(lambda x: f"{x:.2%}")
    display_targets["freelance_score"] = display_targets["freelance_score"].map(lambda x: f"{x:.3f}")
    st.dataframe(display_targets, use_container_width=True)

with insight_tab3:
    question = st.text_input(
        "Ask a question about the current filtered dataset",
        placeholder="Example: Which ZIPs should we target and why?",
    )
    if question:
        st.markdown(answer_question(question, filtered_df, top_zip))
    else:
        st.caption("Try questions about top ZIPs, hotspot reasons, income leaders, averages, and segmentation.")

with insight_tab4:
    st.markdown("### Recommended answer")
    for i, (_, row) in enumerate(target_df.iterrows(), start=1):
        reason = []
        if row["freelance_ratio"] >= filtered_df["freelance_ratio"].median():
            reason.append("above-median freelance concentration")
        if row["returns"] >= filtered_df["returns"].median():
            reason.append("strong filing volume")
        if row["self_employed_income"] >= filtered_df["self_employed_income"].median():
            reason.append("solid self-employment income")
        reason_text = ", ".join(reason[:3]) if reason else "competitive overall profile"
        st.markdown(
            f"**{i}. ZIP {row['zip']}** — score **{row['freelance_score']:.3f}**, ratio **{row['freelance_ratio']:.2%}**, returns **{int(row['returns']):,}**. "
            f"This ZIP is attractive because it shows {reason_text}."
        )
        
# Data table
st.subheader("Top ZIP Data")
display_df = top_zip[[
    "zip",
    "returns",
    "wages",
    "self_employed_income",
    "freelance_ratio",
    "freelance_score",
    "category",
]].copy()
display_df["freelance_ratio"] = display_df["freelance_ratio"].map(lambda x: f"{x:.2%}")
display_df["freelance_score"] = display_df["freelance_score"].map(lambda x: f"{x:.3f}")
st.dataframe(display_df, use_container_width=True)

with st.expander("Project summary for presentation"):
    summary = f"""
    This dashboard analyzes **{len(df):,} ZIP codes** and highlights areas with stronger
    self-employment activity. Under the current filters, the dashboard is showing
    **{len(filtered_df):,} ZIP codes**. The strongest current target is **ZIP {top_zip.iloc[0]['zip']}**
    with a freelance score of **{top_zip.iloc[0]['freelance_score']:.3f}**.

    The app supports market segmentation, hotspot explanation, recommended target ZIPs,
    natural-language question answering, and US map visualization.
    """
    st.write(textwrap.dedent(summary))
