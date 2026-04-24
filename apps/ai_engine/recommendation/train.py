import os
import sys
import django
import pandas as pd
import pickle
from mlxtend.frequent_patterns import apriori, association_rules
from pathlib import Path


# ── Django Setup ──
BASE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()


# Import AFTER setup
from apps.orders.models import Order
from django.conf import settings

MODEL_PATH = settings.AI_RECOMMENDATION_MODEL_PATH


def load_data():
    transactions = []

    # Include all completed or active orders to build rules quickly
    orders = Order.objects.filter(status__in=["confirmed", "ready", "delivered"]).prefetch_related("items__product")

    for order in orders:
        product_names = [item.product.name for item in order.items.all()]
        if product_names:
            transactions.append(product_names)

    if not transactions:
        print("(No delivered orders found, using synthetic data)")
        transactions = [
            ["Fresh Fuji Apple", "Cavendish Banana", "Fresh Tomato"],
            ["Fresh Tomato", "Organic Carrot"],
            ["Cavendish Banana", "Fresh Tomato"],
            ["Fresh Fuji Apple", "Cavendish Banana"],
        ]

    return transactions


def preprocess(transactions):
    all_items = sorted(set(item for t in transactions for item in t))

    encoded = []
    for t in transactions:
        row = {item: (item in t) for item in all_items}
        encoded.append(row)

    return pd.DataFrame(encoded)


def train():
    transactions = load_data()
    df = preprocess(transactions)

    freq = apriori(df, min_support=0.01, use_colnames=True)
    rules = association_rules(freq, metric="lift", min_threshold=1.0)

    return rules


def save_model(rules):
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(rules, f)


if __name__ == "__main__":
    rules = train()
    save_model(rules)
    print(f"Model saved at: {MODEL_PATH}")
