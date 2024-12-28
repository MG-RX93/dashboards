-- transactions table
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    transaction_date DATE NOT NULL,
    description TEXT NOT NULL CHECK (LENGTH(description) >= 500),
    category TEXT NOT NULL CHECK (LENGTH(category) >= 250),
    tags TEXT NOT NULL CHECK (LENGTH(tags) >= 100),
    amount DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- investment transactions table
CREATE TABLE stock_transactions (
    id SERIAL PRIMARY KEY,
    transaction_date DATE NOT NULL,
    action VARCHAR(50) NOT NULL,                    -- e.g., 'Reinvest Dividend', 'Buy', 'Sell'
    description TEXT NOT NULL CHECK (LENGTH(description) >= 500),
    category VARCHAR(100) NOT NULL,                 -- e.g., 'Securities Trades'
    quantity DECIMAL(18,4) NOT NULL,                -- Using 4 decimal places for stock quantities
    price DECIMAL(12,4) NOT NULL,                   -- Price per share with 4 decimal places
    tags TEXT NOT NULL CHECK (LENGTH(tags) >= 100),
    amount DECIMAL(12,2) NOT NULL,                  -- Total transaction amount (can be negative)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);