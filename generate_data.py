from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).parent / 'data'
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(42)

categories = {'Home & Living': (22, 85), 'Accessories': (12, 65), 'Stationery': (5, 30), 'Wellness': (15, 75)}
products = []
for category, (low, high) in categories.items():
    for i in range(1, 9):
        products.append({'product_id': f'P{len(products)+1:03d}', 'product_name': f'{category} Item {i}', 'category': category, 'unit_price': round(float(rng.uniform(low, high)), 2)})
products = pd.DataFrame(products)
products.to_csv(OUT / 'products.csv', index=False)

n_customers = 850
customers = pd.DataFrame({'customer_id': [f'C{i:04d}' for i in range(1, n_customers+1)], 'region': rng.choice(['West','South','Midwest','Northeast'], n_customers, p=[.35,.25,.20,.20]), 'signup_date': pd.to_datetime('2024-09-01') + pd.to_timedelta(rng.integers(0, 470, n_customers), unit='D')})
customers.to_csv(OUT / 'customers.csv', index=False)

n_orders = 2600
rows=[]
for i in range(n_orders):
    date = pd.Timestamp('2025-01-01') + pd.Timedelta(days=int(rng.integers(0,365)))
    eligible = customers.loc[customers.signup_date <= date, 'customer_id'].to_numpy()
    customer = rng.choice(eligible) if len(eligible) else customers.customer_id.iloc[0]
    product = products.iloc[int(rng.integers(len(products)))]
    quantity = int(rng.choice([1,2,3],p=[.72,.23,.05]))
    rows.append({'order_id': f'O{i+1:05d}', 'order_date': date.date().isoformat(), 'customer_id': customer, 'product_id': product.product_id, 'quantity': quantity, 'discount_pct': float(rng.choice([0,.05,.1,.15],p=[.65,.15,.15,.05])), 'status': str(rng.choice(['Completed','Cancelled','Refunded'],p=[.91,.05,.04]))})
orders = pd.DataFrame(rows).sort_values('order_date')
orders.to_csv(OUT / 'orders.csv', index=False)
print(f'Created {len(customers)} customers, {len(products)} products and {len(orders)} orders in {OUT}')
