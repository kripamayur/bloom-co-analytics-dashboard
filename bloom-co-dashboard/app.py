from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Bloom & Co. | Analytics', page_icon='🌸', layout='wide')
ROOT = Path(__file__).parent
PINK = '#C96E91'
PALETTE = ['#C96E91','#B6A1D5','#E5B77E','#93BDB0']

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
cols = st.columns(4)
for col, label, value in zip(cols, ['Revenue','Completed orders','Avg. order value','Repeat customer rate'], [f'${revenue:,.0f}', f'{orders:,}', f'${aov:,.2f}', f'{repeat_rate:.1f}%']):
    col.metric(label, value)

left, right = st.columns([1.6,1])
with left:
    st.subheader('Revenue over time')
    monthly = completed.assign(month=completed.order_date.dt.to_period('M').dt.to_timestamp()).groupby('month',as_index=False).revenue.sum()
    fig = px.line(monthly,x='month',y='revenue',markers=True, color_discrete_sequence=[PINK], labels={'month':'Month','revenue':'Revenue ($)'})
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font_color='#663C50')
    st.plotly_chart(fig,use_container_width=True)
with right:
    st.subheader('Revenue by category')
    by_category = completed.groupby('category',as_index=False).revenue.sum().sort_values('revenue',ascending=False)
    fig = px.bar(by_category,x='revenue',y='category',orientation='h',color='category',color_discrete_sequence=PALETTE,labels={'revenue':'Revenue ($)','category':''})
    fig.update_layout(showlegend=False,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font_color='#663C50',yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig,use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader('Revenue by region')
    region_data = completed.groupby('region',as_index=False).revenue.sum()
    fig = px.pie(region_data,names='region',values='revenue',hole=.55,color_discrete_sequence=PALETTE)
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',font_color='#663C50')
    st.plotly_chart(fig,use_container_width=True)
with right:
    st.subheader('Top products')
    top = completed.groupby('product_name',as_index=False).agg(revenue=('revenue','sum'),units_sold=('quantity','sum')).sort_values('revenue',ascending=False).head(8)
    st.dataframe(top,hide_index=True,use_container_width=True,column_config={'revenue':st.column_config.NumberColumn('Revenue',format='$%.2f')})

st.subheader('What the numbers tell us')
if len(completed):
    best = completed.groupby('category').revenue.sum().idxmax()
    st.info(f'✨ **{best}** generated the most revenue in the selected period. The repeat-customer rate is **{repeat_rate:.1f}%** among customers with completed orders in this filtered view. Investigate category-level margins and retention cohorts before making budget decisions.')
else:
    st.warning('No completed orders match these filters. Try widening your selection.')
st.caption('Portfolio demonstration • Synthetic data generated with a fixed random seed • Revenue excludes cancelled and refunded orders • Repeat rate uses customers with completed orders in the selected view')
