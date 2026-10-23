from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Bloom & Co. | Analytics', page_icon='🌸', layout='wide')
ROOT = Path(__file__).parent
PINK = '#C96E91'
PALETTE = ['#C96E91','#B6A1D5','#E5B77E','#93BDB0']


def style_chart(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Arial",
            color="#663C50",
            size=13,
        ),
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20,
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            font_color="#663C50",
        ),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F3E5EA",
        zeroline=False,
    )

    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
    )

    return fig

st.markdown("""
<style>
    .stApp {
        background-color: #FFF8F7;
    }

    h1, h2, h3 {
        color: #663C50 !important;
        letter-spacing: -0.5px;
    }

    h1 {
        font-weight: 750 !important;
    }

    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #F1DDE5;
        padding: 20px;
        border-radius: 18px;
        box-shadow: 0 4px 16px rgba(150, 80, 110, 0.06);
    }

    [data-testid="stMetricLabel"] {
        color: #9F7183;
    }

    [data-testid="stMetricValue"] {
        color: #663C50;
    }

    [data-testid="stSidebar"] {
        background-color: #FBEAF0;
    }

    div.stButton > button {
        border-radius: 12px;
        background-color: #C96E91;
        color: white;
        border: none;
    }

    div.stButton > button:hover {
        background-color: #B65D82;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    conn = sqlite3.connect(':memory:')
    for name in ['customers','products','orders']:
        pd.read_csv(ROOT / 'data' / f'{name}.csv').to_sql(name, conn, index=False)
    query = '''SELECT o.order_id, o.order_date, o.customer_id, c.region,
                      p.product_name, p.category, o.quantity, p.unit_price,
                      o.discount_pct, o.status,
                      ROUND(o.quantity * p.unit_price * (1 - o.discount_pct), 2) AS revenue
               FROM orders o JOIN customers c ON o.customer_id = c.customer_id
               JOIN products p ON o.product_id = p.product_id'''
    df = pd.read_sql_query(query, conn, parse_dates=['order_date'])
    conn.close()
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error('Dataset missing. Run `python generate_data.py` first.')
    st.stop()

st.title("✿ bloom & co.")
st.markdown(
    "### Your business, in full bloom."
)
st.caption(
    "Explore sales, customers, product performance, and more."
)
regions = st.sidebar.multiselect('Regions', sorted(df.region.unique()), default=sorted(df.region.unique()))
categories = st.sidebar.multiselect('Categories', sorted(df.category.unique()), default=sorted(df.category.unique()))
dates = st.sidebar.date_input('Order date range', (df.order_date.min().date(), df.order_date.max().date()), min_value=df.order_date.min().date(), max_value=df.order_date.max().date())
if len(dates) != 2:
    st.info('Select a start and end date.')
    st.stop()
start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1])

filtered = df[
    df.region.isin(regions)
    & df.category.isin(categories)
    & (df.order_date >= start)
    & (df.order_date < end + pd.Timedelta(days=1))
]

completed = filtered[filtered.status == 'Completed'].copy()


st.sidebar.divider()

st.sidebar.download_button(
    label="📥 Download filtered data",
    data=completed.to_csv(index=False).encode("utf-8"),
    file_name="bloom_co_filtered_orders.csv",
    mime="text/csv",
)


# Monthly revenue for the selected filters
monthly_revenue = (
    completed
    .groupby(completed.order_date.dt.to_period("M"))
    ["revenue"]
    .sum()
    .sort_index()
)

# Compare the last two complete calendar months.
last_complete_month = pd.Timestamp.today().to_period("M") - 1
previous_month = last_complete_month - 1

current_revenue = monthly_revenue.get(last_complete_month, 0)
previous_revenue = monthly_revenue.get(previous_month, 0)

if previous_revenue > 0:
    mom_growth = (
        (current_revenue - previous_revenue)
        / previous_revenue
    ) * 100
else:
    mom_growth = None

revenue = completed.revenue.sum()
orders = completed.order_id.nunique()
aov = revenue / orders if orders else 0
customer_orders = completed.groupby('customer_id').order_id.nunique()
repeat_rate = 100 * customer_orders.ge(2).mean() if len(customer_orders) else 0

overview_tab, customers_tab, insights_tab = st.tabs(
    ["🌸 Overview", "🪻 Customers", "✨ Insights"]
)

with overview_tab:
    # Your existing revenue metrics and charts go here
    cols = st.columns(4)
    for col, label, value in zip(cols, ['Revenue','Completed orders','Avg. order value','Repeat customer rate'], [f'${revenue:,.0f}', f'{orders:,}', f'${aov:,.2f}', f'{repeat_rate:.1f}%']):
        col.metric(label, value)

    left, right = st.columns([1.6,1])
    with left:
        st.subheader('Revenue over time')
        monthly = completed.assign(month=completed.order_date.dt.to_period('M').dt.to_timestamp()).groupby('month',as_index=False).revenue.sum()
        fig = px.line(monthly,x='month',y='revenue',markers=True, color_discrete_sequence=[PINK], labels={'month':'Month','revenue':'Revenue ($)'})
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font_color='#663C50')
        st.plotly_chart(style_chart(fig), use_container_width=True)
    with right:
        st.subheader('Revenue by category')
        by_category = completed.groupby('category',as_index=False).revenue.sum().sort_values('revenue',ascending=False)
        fig = px.bar(by_category,x='revenue',y='category',orientation='h',color='category',color_discrete_sequence=PALETTE,labels={'revenue':'Revenue ($)','category':''})
        fig.update_layout(showlegend=False,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font_color='#663C50',yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(style_chart(fig), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader('Revenue by region')
        region_data = completed.groupby('region',as_index=False).revenue.sum()
        fig = px.pie(region_data,names='region',values='revenue',hole=.55,color_discrete_sequence=PALETTE)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',font_color='#663C50')
        st.plotly_chart(style_chart(fig), use_container_width=True)
    with right:
        st.subheader('Top products')
        top = completed.groupby('product_name',as_index=False).agg(revenue=('revenue','sum'),units_sold=('quantity','sum')).sort_values('revenue',ascending=False).head(8)
        st.dataframe(top,hide_index=True,use_container_width=True,column_config={'revenue':st.column_config.NumberColumn('Revenue',format='$%.2f')})

with insights_tab:
    st.subheader('What the numbers tell us')
    if len(completed):
        best = completed.groupby('category').revenue.sum().idxmax()
        st.info(f'✨ **{best}** generated the most revenue in the selected period. The repeat-customer rate is **{repeat_rate:.1f}%** among customers with completed orders in this filtered view. Investigate category-level margins and retention cohorts before making budget decisions.')
    else:
        st.warning('No completed orders match these filters. Try widening your selection.')
    st.caption('Portfolio demonstration • Synthetic data generated with a fixed random seed • Revenue excludes cancelled and refunded orders • Repeat rate uses customers with completed orders in the selected view')


# ------------------------------------------
# CUSTOMER ANALYTICS
# ------------------------------------------
with customers_tab:
    st.divider()

    st.header("🌷 Getting to know our customers")
    st.caption(
        "Understanding who shops with us, "
        "how often they return, and what they spend."
    )

    # Count each customer's unique completed orders
    customer_summary = (
        completed.groupby("customer_id")
        .agg(
            total_orders=("order_id", "nunique"),
            total_spent=("revenue", "sum"),
        )
        .reset_index()
    )

    # Segment customers based on their order history
    customer_summary["segment"] = customer_summary["total_orders"].apply(
        lambda n: "Returning" if n >= 2 else "One-time"
    )

    # Calculate customer metrics
    total_customers = len(customer_summary)

    returning_customers = (
        customer_summary["segment"] == "Returning"
    ).sum()

    returning_rate = (
        returning_customers / total_customers * 100
        if total_customers else 0
    )

    avg_customer_value = (
        customer_summary["total_spent"].mean()
        if total_customers else 0
    )

    # Display KPI cards
    col1, col2, col3 = st.columns(3)

    col1.metric("Unique customers", f"{total_customers:,}")
    col2.metric("Returning customers", f"{returning_customers:,}")
    col3.metric("Avg. customer spend", f"${avg_customer_value:,.2f}")

    # Customer segment visualization
    st.subheader("Customer segments")

    segment_counts = (
        customer_summary["segment"]
        .value_counts()
        .reset_index()
    )

    segment_counts.columns = ["Segment", "Customers"]

    fig = px.pie(
        segment_counts,
        names="Segment",
        values="Customers",
        hole=0.65,
        color="Segment",
        color_discrete_map={
            "Returning": "#C96E91",
            "One-time": "#B6A1D5",
        },
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#663C50",
        margin=dict(t=20, b=20, l=20, r=20),
    )

    st.plotly_chart(style_chart(fig), use_container_width=True)

    # Customer spending distribution
    st.subheader("Customer spending distribution")

    fig = px.histogram(
        customer_summary,
        x="total_spent",
        nbins=20,
        color_discrete_sequence=["#93BDB0"],
        labels={
            "total_spent": "Total customer spend ($)"
        },
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#663C50",
    )

    st.plotly_chart(style_chart(fig), use_container_width=True)

    # Dynamic customer insight
    if total_customers:
        st.info(
            f"🌸 **{returning_rate:.1f}%** of customers placed "
            f"multiple completed orders within the selected filters. "
            f"Average customer spend was "
            f"**${avg_customer_value:,.2f}**."
        )
    else:
        st.warning("No customers match the current filters.")
