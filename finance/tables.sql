CREATE TABLE purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id TEXT NOT NULL,
    stock_id TEXT NOT NULL,
    name TEXT NOT NULL,
    shares TEXT NOT NULL,
    amount TEXT NOT NULL,
    purchasedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);





)