import os
from dotenv import load_dotenv
import argparse
import pandas as pd
import psycopg2
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def parse_filename(filename: str) -> Tuple[str, str]:
    try:
        bank, account = filename.split('_')
        return bank, account.replace('.csv', '')
    except ValueError:
        raise ValueError(f"Invalid filename format: {filename}. Expected: bankname_accountname.csv")

def clean_transaction_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    required_cols = ['Date', 'Description', 'Category', 'Tags', 'Amount']
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Convert amount
    df['amount'] = pd.to_numeric(df['Amount'].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce')
    
    # Convert date and clean text fields
    df['transaction_date'] = pd.to_datetime(df['Date']).dt.date
    df['description'] = df['Description'].str.strip()
    df['category'] = df['Category'].str.strip()
    df['tags'] = df['Tags'].fillna('')
    
    # Determine transaction type based on amount sign
    df['transaction_type'] = df['amount'].apply(lambda x: 'credit' if x > 0 else 'debit')

    # Validate required fields
    invalid_amounts = df['amount'].isna()
    
    if invalid_amounts.any():
        logger.warning(f"Dropping {invalid_amounts.sum()} rows with invalid amounts")
        
    df = df.dropna(subset=['amount'])

    return df

def transform_to_parquet(input_path: Path) -> Path:
    logger.info(f"Processing {input_path}")
    bank, account = parse_filename(input_path.name)
    
    df = pd.read_csv(input_path)
    df = clean_transaction_data(df)
    
    df['account_name'] = account
    df['bank_name'] = bank
    
    output_cols = [
        'transaction_date', 'description', 'category', 'tags',
        'amount', 'account_name', 'bank_name', 'transaction_type'
    ]
    
    df = df[output_cols]
    output_path = input_path.with_suffix('.parquet')
    df.to_parquet(output_path, index=False)
    
    logger.info(f"Saved Parquet file: {output_path}")
    return output_path

def load_to_postgres(parquet_path: Path, db_params: Dict[str, str]) -> None:
    logger.info(f"Loading {parquet_path} to PostgreSQL")
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()
        
        sql = f"""
        COPY bank_transactions (
            transaction_date, description, category, tags,
            amount, account_name, bank_name, transaction_type
        ) FROM '{parquet_path.absolute()}' (FORMAT 'parquet');
        """
        
        cur.execute(sql)
        conn.commit()
        logger.info("Data loaded successfully")
        
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def main():
    parser = argparse.ArgumentParser()
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
        
    csv_files = list(input_dir.glob('*.csv'))
    logger.info(f"Found {len(csv_files)} CSV files to process")
    
    for csv_file in csv_files:
        try:
            parquet_file = transform_to_parquet(csv_file)
            load_to_postgres(parquet_file, db_params)
        except Exception as e:
            logger.error(f"Error processing {csv_file}: {str(e)}")
            continue

if __name__ == '__main__':
    main()