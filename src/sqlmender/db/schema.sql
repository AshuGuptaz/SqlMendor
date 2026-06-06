-- E-commerce schema (6 tables) for text-to-SQL evaluation.
PRAGMA foreign_keys = ON;

CREATE TABLE categories (
    category_id   INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    description   TEXT
);

CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    city          TEXT NOT NULL,
    country       TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE products (
    product_id    INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    category_id   INTEGER NOT NULL,
    price         REAL NOT NULL,
    stock         INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL,
    order_date    TEXT NOT NULL,
    status        TEXT NOT NULL,
    total         REAL NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL,
    product_id    INTEGER NOT NULL,
    quantity      INTEGER NOT NULL,
    unit_price    REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE reviews (
    review_id     INTEGER PRIMARY KEY,
    product_id    INTEGER NOT NULL,
    customer_id   INTEGER NOT NULL,
    rating        INTEGER NOT NULL,
    comment       TEXT,
    review_date   TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
