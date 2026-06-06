"""Human-readable schema string injected into model prompts and exposed by the API."""

from __future__ import annotations

SCHEMA_DESCRIPTION = """Tables:
categories(category_id, name, description)
customers(customer_id, first_name, last_name, email, city, country, created_at)
products(product_id, name, category_id, price, stock)
orders(order_id, customer_id, order_date, status, total)
order_items(order_item_id, order_id, product_id, quantity, unit_price)
reviews(review_id, product_id, customer_id, rating, comment, review_date)

Relationships:
products.category_id -> categories.category_id
orders.customer_id -> customers.customer_id
order_items.order_id -> orders.order_id
order_items.product_id -> products.product_id
reviews.product_id -> products.product_id
reviews.customer_id -> customers.customer_id"""
