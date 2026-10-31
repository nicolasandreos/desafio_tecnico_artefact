CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER,
    price_brl TEXT,
    stock_quantity INTEGER,
    status TEXT CHECK (
        status IS NULL
        OR status IN ('active', 'discontinued', 'coming_soon')
    ),
    description TEXT,
    specs TEXT,
    created_at TEXT,
    FOREIGN KEY (category_id) REFERENCES categories (category_id)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT,
    phone TEXT,
    email TEXT,
    city TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id INTEGER,
    order_date TEXT,
    status TEXT,
    total_brl TEXT,
    payment_method TEXT,
    tracking_code TEXT,
    estimated_delivery TEXT,
    notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id TEXT,
    product_id INTEGER,
    quantity INTEGER,
    FOREIGN KEY (order_id) REFERENCES orders (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INTEGER PRIMARY KEY,
    product_id INTEGER,
    discount_percent INTEGER,
    description TEXT,
    is_active INTEGER,
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

CREATE TABLE IF NOT EXISTS ownership_codes (
    code_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    replaced INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS order_grants (
    session_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    granted_at TEXT NOT NULL,
    PRIMARY KEY (session_id, order_id)
);
