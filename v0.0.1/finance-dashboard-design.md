# Financial Dashboard System Design Document

## 1. System Overview
- Primary database: PostgreSQL with TimescaleDB extension
- Data source: Weekly Parquet files from 10 financial institutions
- Visualization: Grafana dashboards
- Deployment: Local Mac machine
- Update frequency: Weekly batch processing
- Data volume: ~1000 transactions/month across 10 accounts

## 2. Database Schema

### Core Tables

#### transactions
```sql
CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    transaction_date TIMESTAMPTZ NOT NULL,  -- For TimescaleDB functionality
    post_date TIMESTAMPTZ,                 -- Actual posting date if different
    account_id INTEGER NOT NULL,
    transaction_type VARCHAR(50),
    amount DECIMAL(15,2) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    merchant VARCHAR(255),
    labels TEXT[],                         -- Array for multiple labels/tags
    metadata JSONB,                        -- For bank-specific fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    batch_id UUID                          -- For tracking import batches
);
-- Note for implementation: Add TimescaleDB hypertable conversion
```

#### accounts
```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    institution_name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL,     -- checking/savings/credit
    account_name VARCHAR(255) NOT NULL,
    last_four VARCHAR(4),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB
);
```

#### import_history
```sql
CREATE TABLE import_history (
    batch_id UUID PRIMARY KEY,
    import_date TIMESTAMPTZ DEFAULT NOW(),
    file_name VARCHAR(255),
    account_id INTEGER,
    start_date DATE,
    end_date DATE,
    record_count INTEGER,
    status VARCHAR(50),
    error_message TEXT
);
```

### Materialized Views

#### monthly_summary
- Transaction counts and totals by account
- Running balances
- Category breakdowns
- Note: Refresh schedule needed

#### quarterly_metrics
- Spending patterns
- Category trends
- YoY comparisons

## 3. Data Processing Pipeline

### Initial Load Process
1. CSV to Parquet conversion
2. Schema validation
3. Data cleaning and standardization
4. Bulk load to transactions table

### Weekly Update Process
1. Parquet file validation
2. Deduplication check
3. Transaction insert
4. Materialized view refresh

### Data Validation Rules
- Date range checks
- Amount format validation
- Required field validation
- Duplicate transaction detection

## 4. Implementation Notes

### Phase 1: Setup
- PostgreSQL installation and configuration
- TimescaleDB extension setup
- Initial schema creation
- Test data loading

### Phase 2: Core Functions
- Parquet processing utilities
- Database operations wrapper
- Validation functions
- Error handling and logging

### Phase 3: Automation
- Weekly import automation
- View refresh scheduling
- Monitoring setup

## 5. Query Patterns

### Common Queries to Support
1. Current month spending by category
2. Week-over-week comparison
3. Monthly trend analysis
4. Year-to-date summaries
5. Cross-account analytics

### Performance Considerations
- Index on (account_id, transaction_date)
- Partial index for recent transactions
- TimescaleDB chunk interval optimization

## 6. Grafana Integration

### Dashboard Panels
1. Current Month Overview
   - Total spending
   - Category breakdown
   - Daily trend

2. Historical Analysis
   - Monthly trends
   - Year-over-year comparison
   - Category evolution

3. Account Health
   - Balance trends
   - Large transactions
   - Spending patterns

### Query Optimization
- Use materialized views for common patterns
- Pre-calculate expensive aggregations
- Implement efficient date filtering

## Implementation Tips for Future Reference

1. CSV Processing:
   - Look for 'Date' field variations
   - Handle different currency formats
   - Check for bank-specific transaction codes

2. Database:
   - Start with 1-month chunks in TimescaleDB
   - Create indexes after bulk load
   - Implement upsert patterns for duplicates

3. Error Handling:
   - Track failed imports separately
   - Implement transaction rollback
   - Log validation failures

4. Performance:
   - Batch size recommendations
   - Index usage monitoring
   - View refresh optimization

## Future Enhancements
1. Category prediction
2. Anomaly detection
3. Budget tracking
4. Export capabilities
5. Multi-currency support

---
Note: This document will be used as input for generating implementation code. Each section contains specific details needed for accurate code generation.