import os
from dotenv import load_dotenv
import argparse
import pandas as pd
import psycopg2
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def determine_fiscal_periods(date: pd.Timestamp) -> dict:
    """Calculate fiscal periods and month information from date."""
    fiscal_year = date.year if date.month < 7 else date.year + 1
    
    if date.month < 7:
        fiscal_quarter = ((date.month + 6) // 3)
    else:
        fiscal_quarter = ((date.month - 6) // 3) + 1
        
    month = date.strftime('%B')
    
    return {
        'fiscal_year': fiscal_year,
        'fiscal_quarter': fiscal_quarter,
        'month': month
    }

def preprocess_data(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    """Preprocess stock transaction data."""
    df = df.copy()
    logger.info(f"Processing file: {filename}")
    
    required_cols = ['Date', 'Action', 'Description', 'Category', 'Quantity', 'Price', 'Tags', 'Amount']
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns in {filename}: {missing_cols}")

    # Clean amount and price fields
    for field in ['Amount', 'Price']:
        df[field.lower()] = (df[field].astype(str)
                           .str.replace('$', '')
                           .str.replace(',', '')
                           .astype(float))
    
    # Convert quantity
    df['quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
    
    # Drop rows with invalid data
    invalid_rows = df['quantity'].isna() | df['price'].isna() | df['amount'].isna()
    if invalid_rows.any():
        logger.warning(f"Dropping {invalid_rows.sum()} rows with invalid data in {filename}")
        df = df.dropna(subset=['quantity', 'price', 'amount'])
    
    # Process dates and text fields - Convert to datetime and then to string format
    df['transaction_date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    df['action'] = df['Action'].str.strip().str.lower()
    df['description'] = df['Description'].str.strip()
    df['category'] = df['Category'].str.strip()
    df['tags'] = df['Tags'].fillna('')
    
    # Calculate fiscal periods using datetime for calculations
    fiscal_data = pd.to_datetime(df['transaction_date']).apply(determine_fiscal_periods)
    df['fiscal_year'] = fiscal_data.apply(lambda x: x['fiscal_year'])
    df['fiscal_quarter'] = fiscal_data.apply(lambda x: x['fiscal_quarter'])
    df['month'] = fiscal_data.apply(lambda x: x['month'])
    
    # Select final columns in correct order
    final_cols = [
        'transaction_date', 'action', 'description', 'category',
        'quantity', 'price', 'tags', 'amount',
        'fiscal_year', 'fiscal_quarter', 'month'
    ]
    
    return df[final_cols]


    """Load DataFrame to PostgreSQL stock_transactions table."""
    logger.info(f"Loading data from {filename} to PostgreSQL")
    
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()
        
        # Create temp table for staging
        cur.execute("""
        CREATE TEMP TABLE temp_stocks (LIKE stock_transactions EXCLUDING CONSTRAINTS)
        ON COMMIT DROP;
        """)
        
        # Convert DataFrame to list of tuples and ensure proper data types
        records = [tuple(row) for row in df.values]
        
        # Bulk insert using execute_values
        from psycopg2.extras import execute_values
        execute_values(
            cur,
            """
            INSERT INTO temp_stocks (
                transaction_date, action, description, category,
                quantity, price, tags, amount,
                fiscal_year, fiscal_quarter, month
            ) VALUES %s
            """,
            records
        )
        
        # Insert from temp table to main table
        cur.execute("""
        INSERT INTO stock_transactions (
            transaction_date, action, description, category,
            quantity, price, tags, amount,
            fiscal_year, fiscal_quarter, month
        )
        SELECT * FROM temp_stocks;
        """)
        
        conn.commit()
        logger.info(f"Successfully loaded {len(records)} records from {filename}")
        
    except Exception as e:
        logger.error(f"Database error while processing {filename}: {str(e)}")
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def load_to_postgres(df: pd.DataFrame, db_params: dict, filename: str) -> None:
    """Load DataFrame to PostgreSQL stock_transactions table."""
    logger.info(f"Loading data from {filename} to PostgreSQL")
    
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()
        
        # Create temp table with explicit columns, excluding id
        cur.execute("""
        CREATE TEMP TABLE temp_stocks (
            transaction_date DATE,
            action VARCHAR(50),
            description TEXT,
            category VARCHAR(50),
            quantity DECIMAL(12,4),
            price DECIMAL(12,2),
            tags TEXT,
            amount DECIMAL(12,2),
            fiscal_year INT,
            fiscal_quarter INT,
            month VARCHAR(20)
        ) ON COMMIT DROP;
        """)
        
        # Convert DataFrame to list of tuples
        records = [tuple(row) for row in df.values]
        
        # Bulk insert using execute_values
        from psycopg2.extras import execute_values
        execute_values(
            cur,
            """
            INSERT INTO temp_stocks (
                transaction_date, action, description, category,
                quantity, price, tags, amount,
                fiscal_year, fiscal_quarter, month
            ) VALUES %s
            """,
            records
        )
        
        # Insert from temp table to main table
        cur.execute("""
        INSERT INTO stock_transactions (
            transaction_date, action, description, category,
            quantity, price, tags, amount,
            fiscal_year, fiscal_quarter, month
        )
        SELECT 
            transaction_date, action, description, category,
            quantity, price, tags, amount,
            fiscal_year, fiscal_quarter, month
        FROM temp_stocks;
        """)
        
        conn.commit()
        logger.info(f"Successfully loaded {len(records)} records from {filename}")
        
    except Exception as e:
        logger.error(f"Database error while processing {filename}: {str(e)}")
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def process_csv_files(input_dir: Path, db_params: dict) -> None:
    """Process all CSV files in the input directory."""
    csv_files = list(input_dir.glob('*.csv'))
    logger.info(f"Found {len(csv_files)} CSV files to process")
    
    for csv_file in csv_files:
        try:
            # Read and process CSV
            df = pd.read_csv(csv_file)
            processed_df = preprocess_data(df, csv_file.name)
            
            # Load to database
            load_to_postgres(processed_df, db_params, csv_file.name)
            
        except Exception as e:
            logger.error(f"Error processing {csv_file}: {str(e)}")
            continue

def main():
    parser = argparse.ArgumentParser(description='Load stock transaction data into database')
    parser.add_argument('--input_dir', type=str, required=True, help='Directory containing CSV files')
    args = parser.parse_args()

    db_params = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST')
    }
    
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    process_csv_files(input_dir, db_params)

if __name__ == '__main__':
    main()