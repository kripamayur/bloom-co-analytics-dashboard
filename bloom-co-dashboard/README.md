# 🌸 Bloom & Co. — E-commerce Analytics Dashboard

A pastel-themed interactive business intelligence dashboard built with **Python, Pandas, SQL (SQLite), Streamlit, and Plotly**.

## Features
- Filter completed order metrics by region, category and date
- Revenue, completed orders, average order value, repeat customer rate
- Monthly revenue, category and regional revenue charts, top products
- SQL joins across customers, products and orders
- Reproducible synthetic data (no private business data)

## Run locally
```bash
python -m pip install -r requirements.txt
python generate_data.py
streamlit run app.py
```

## Data model
`customers.csv` (customer_id, region, signup_date), `products.csv` (product_id, category, unit_price), `orders.csv` (order_id, order_date, customer_id, product_id, quantity, discount_pct, status).

## Metric definitions
- **Revenue**: completed orders only; quantity × price × (1 − discount).
- **Average order value**: completed revenue / number of completed orders.
- **Repeat customer rate**: share of customers with at least 2 completed orders within the currently filtered view.

## Notes
All data is fictional. Charts and observations are descriptive, not causal. No costs or margins are modeled.
