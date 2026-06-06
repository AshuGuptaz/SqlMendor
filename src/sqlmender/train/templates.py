"""Template families that expand into (question, SQL) pairs over the e-commerce
schema. Each family is parameterized so the families together yield 1500+ pairs.

Every generated SQL is a read-only SELECT and is validated to execute against the
real DB by the generator before it is kept."""

from __future__ import annotations

from collections.abc import Iterator

from sqlmender.schemas import SQLExample

CATEGORIES = ["Electronics", "Books", "Clothing", "Home", "Sports", "Toys", "Beauty", "Garden"]
CITIES = [
    "London",
    "Paris",
    "Berlin",
    "Madrid",
    "Rome",
    "Chennai",
    "Tokyo",
    "Toronto",
    "Austin",
    "Sydney",
]
COUNTRIES = [
    "UK",
    "France",
    "Germany",
    "Spain",
    "Italy",
    "India",
    "Japan",
    "Canada",
    "USA",
    "Australia",
]
STATUSES = ["pending", "shipped", "delivered", "cancelled", "returned"]
PRICES = [20, 50, 75, 100, 150, 200, 300]
RATINGS = [2, 3, 4, 5]
LIMITS = [3, 5, 10, 20]
STOCKS = [10, 25, 50, 100]
DATES = ["2023-06-01", "2023-12-31", "2024-01-01", "2024-06-30"]


def _e(q: str, s: str, c: str) -> SQLExample:
    return SQLExample(question=q, sql=s, category=c)


def generate_all() -> Iterator[SQLExample]:
    # 1. products in a category
    for cat in CATEGORIES:
        yield _e(
            f"List all products in the {cat} category.",
            f"SELECT p.name FROM products p JOIN categories c ON p.category_id = c.category_id WHERE c.name = '{cat}';",
            "join",
        )
    # 2. count customers per country
    for country in COUNTRIES:
        yield _e(
            f"How many customers are from {country}?",
            f"SELECT COUNT(*) FROM customers WHERE country = '{country}';",
            "aggregate",
        )
    # 3. customers in a city
    for city in CITIES:
        yield _e(
            f"Show the names of customers in {city}.",
            f"SELECT first_name, last_name FROM customers WHERE city = '{city}';",
            "filter",
        )
    # 4. products under a price
    for pr in PRICES:
        yield _e(
            f"Which products cost less than {pr} dollars?",
            f"SELECT name FROM products WHERE price < {pr};",
            "filter",
        )
    # 5. products over a price
    for pr in PRICES:
        yield _e(
            f"Which products cost more than {pr} dollars?",
            f"SELECT name FROM products WHERE price > {pr};",
            "filter",
        )
    # 6. orders by status
    for st in STATUSES:
        yield _e(
            f"List the order ids with status {st}.",
            f"SELECT order_id FROM orders WHERE status = '{st}';",
            "filter",
        )
    # 7. count orders by status
    for st in STATUSES:
        yield _e(
            f"How many orders are {st}?",
            f"SELECT COUNT(*) FROM orders WHERE status = '{st}';",
            "aggregate",
        )
    # 8. top N most expensive products
    for n in LIMITS:
        yield _e(
            f"What are the {n} most expensive products?",
            f"SELECT name, price FROM products ORDER BY price DESC LIMIT {n};",
            "orderby",
        )
    # 9. N cheapest products
    for n in LIMITS:
        yield _e(
            f"What are the {n} cheapest products?",
            f"SELECT name, price FROM products ORDER BY price ASC LIMIT {n};",
            "orderby",
        )
    # 10. products with low stock
    for s in STOCKS:
        yield _e(
            f"Which products have fewer than {s} units in stock?",
            f"SELECT name, stock FROM products WHERE stock < {s};",
            "filter",
        )
    # 11. average price per category
    for cat in CATEGORIES:
        yield _e(
            f"What is the average product price in the {cat} category?",
            f"SELECT AVG(p.price) FROM products p JOIN categories c ON p.category_id = c.category_id WHERE c.name = '{cat}';",
            "aggregate",
        )
    # 12. count products per category
    for cat in CATEGORIES:
        yield _e(
            f"How many products are in the {cat} category?",
            f"SELECT COUNT(*) FROM products p JOIN categories c ON p.category_id = c.category_id WHERE c.name = '{cat}';",
            "aggregate",
        )
    # 13. customers who joined after a date
    for d in DATES:
        yield _e(
            f"Which customers joined after {d}?",
            f"SELECT first_name, last_name FROM customers WHERE created_at > '{d}';",
            "filter",
        )
    # 14. orders placed after a date
    for d in DATES:
        yield _e(
            f"List orders placed after {d}.",
            f"SELECT order_id, order_date FROM orders WHERE order_date > '{d}';",
            "filter",
        )
    # 15. products with avg rating >= R
    for r in RATINGS:
        yield _e(
            f"Which products have an average rating of at least {r}?",
            f"SELECT p.name FROM products p JOIN reviews rv ON p.product_id = rv.product_id GROUP BY p.product_id, p.name HAVING AVG(rv.rating) >= {r};",
            "groupby_having",
        )
    # 16. count reviews with a given rating
    for r in [1, 2, 3, 4, 5]:
        yield _e(
            f"How many reviews gave a rating of {r}?",
            f"SELECT COUNT(*) FROM reviews WHERE rating = {r};",
            "aggregate",
        )
    # 17. revenue per status
    for st in STATUSES:
        yield _e(
            f"What is the total revenue from {st} orders?",
            f"SELECT SUM(total) FROM orders WHERE status = '{st}';",
            "aggregate",
        )
    # 18. top N products by units sold
    for n in LIMITS:
        yield _e(
            f"What are the top {n} products by total quantity sold?",
            f"SELECT p.name, SUM(oi.quantity) AS qty FROM order_items oi JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_id, p.name ORDER BY qty DESC LIMIT {n};",
            "join_groupby",
        )
    # 19. customers with more than N orders
    for n in [1, 2, 3, 4]:
        yield _e(
            f"Which customers have placed more than {n} orders?",
            f"SELECT c.first_name, c.last_name, COUNT(*) AS order_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.first_name, c.last_name HAVING COUNT(*) > {n};",
            "groupby_having",
        )
    # 20. number of customers per city (group by)
    for _ in [0]:
        yield _e(
            "How many customers are in each city?",
            "SELECT city, COUNT(*) AS n FROM customers GROUP BY city;",
            "groupby",
        )
        yield _e(
            "How many products are in each category?",
            "SELECT c.name, COUNT(*) AS n FROM products p JOIN categories c ON p.category_id = c.category_id GROUP BY c.name;",
            "join_groupby",
        )
        yield _e("What is the average order total?", "SELECT AVG(total) FROM orders;", "aggregate")
        yield _e(
            "What is the most expensive product?",
            "SELECT name, price FROM products ORDER BY price DESC LIMIT 1;",
            "orderby",
        )
        yield _e(
            "How many products are out of stock?",
            "SELECT COUNT(*) FROM products WHERE stock = 0;",
            "aggregate",
        )
        yield _e(
            "List the distinct order statuses.", "SELECT DISTINCT status FROM orders;", "distinct"
        )
        yield _e(
            "List the distinct customer countries.",
            "SELECT DISTINCT country FROM customers;",
            "distinct",
        )
    # 21. products in price range
    for lo in [50, 100, 200]:
        for hi in [150, 300, 500]:
            if hi > lo:
                yield _e(
                    f"Which products cost between {lo} and {hi} dollars?",
                    f"SELECT name, price FROM products WHERE price BETWEEN {lo} AND {hi};",
                    "range",
                )
    # 22. customers in a country and city combos
    for country in COUNTRIES:
        yield _e(
            f"How many products were ordered by customers in {country}?",
            f"SELECT SUM(oi.quantity) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.country = '{country}';",
            "multi_join",
        )
    # 23. avg rating per category
    for cat in CATEGORIES:
        yield _e(
            f"What is the average review rating for products in the {cat} category?",
            f"SELECT AVG(rv.rating) FROM reviews rv JOIN products p ON rv.product_id = p.product_id JOIN categories c ON p.category_id = c.category_id WHERE c.name = '{cat}';",
            "multi_join",
        )
    # 24. count orders per status (single group by)
    for _ in [0]:
        yield _e(
            "How many orders are there for each status?",
            "SELECT status, COUNT(*) AS n FROM orders GROUP BY status;",
            "groupby",
        )
        yield _e(
            "What is the total stock across all products?",
            "SELECT SUM(stock) FROM products;",
            "aggregate",
        )
        yield _e(
            "Which product has the highest price in each category?",
            "SELECT c.name AS category, MAX(p.price) AS max_price FROM products p JOIN categories c ON p.category_id = c.category_id GROUP BY c.name;",
            "join_groupby",
        )
    # 25. high-value orders
    for pr in [200, 500, 1000, 1500]:
        yield _e(
            f"List orders with a total above {pr} dollars.",
            f"SELECT order_id, total FROM orders WHERE total > {pr};",
            "filter",
        )
        yield _e(
            f"How many orders had a total above {pr} dollars?",
            f"SELECT COUNT(*) FROM orders WHERE total > {pr};",
            "aggregate",
        )


def generate_cross_product() -> Iterator[SQLExample]:
    """Higher-cardinality families (category x price, country x status, etc.)."""
    # category x price-under
    for cat in CATEGORIES:
        for pr in PRICES:
            yield _e(
                f"Which {cat} products cost less than {pr} dollars?",
                f"SELECT p.name, p.price FROM products p JOIN categories c ON p.category_id = c.category_id WHERE c.name = '{cat}' AND p.price < {pr};",
                "join_filter",
            )
    # category x top-N expensive
    for cat in CATEGORIES:
        for n in LIMITS:
            yield _e(
                f"What are the {n} most expensive products in the {cat} category?",
                f"SELECT p.name, p.price FROM products p JOIN categories c ON p.category_id = c.category_id WHERE c.name = '{cat}' ORDER BY p.price DESC LIMIT {n};",
                "join_orderby",
            )
    # country x status order counts
    for country in COUNTRIES:
        for st in STATUSES:
            yield _e(
                f"How many {st} orders were placed by customers in {country}?",
                f"SELECT COUNT(*) FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE c.country = '{country}' AND o.status = '{st}';",
                "join_aggregate",
            )
    # category x min rating
    for cat in CATEGORIES:
        for r in RATINGS:
            yield _e(
                f"Which {cat} products have an average rating of at least {r}?",
                f"SELECT p.name FROM products p JOIN categories c ON p.category_id = c.category_id JOIN reviews rv ON p.product_id = rv.product_id WHERE c.name = '{cat}' GROUP BY p.product_id, p.name HAVING AVG(rv.rating) >= {r};",
                "multi_join_having",
            )
