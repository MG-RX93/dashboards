import os
from dotenv import load_dotenv
import argparse
import pandas as pd
import psycopg2
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Dict, Tuple, Literal, Any
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

SourceType = Literal['bank', 'credit']

def parse_filename(filename: str) -> Tuple[str, str, SourceType]:
    """Parse filename to extract institution name, account name, and determine source type."""
    try:
        parts = filename.replace('.csv', '').split('_')
        if len(parts) != 3:
            raise ValueError("Filename must be in format: type_institution_account.csv")
            
        file_type, institution, account = parts
        if file_type.lower() not in ('bank', 'credit'):
            raise ValueError("File type must be 'bank' or 'credit'")
            
        return institution, account, file_type.lower()
    except Exception as e:
        raise ValueError(f"Invalid filename format: {filename}. Error: {str(e)}")

def determine_fiscal_periods(date: pd.Timestamp) -> Dict[str, Any]:
    """Calculate calendar periods and month information from date."""    
    return {
        'fiscal_year': date.year,  # Simply use calendar year
        'fiscal_quarter': (date.month - 1) // 3 + 1,  # Calendar quarter (1-4)
        'month': date.strftime('%B')
    }

def preprocess_transaction_data(df: pd.DataFrame, source_type: SourceType, filename: str) -> pd.DataFrame:
    """Comprehensively preprocess transaction data with all required fields."""
    df = df.copy()
    
    required_cols = ['Date', 'Description', 'Category', 'Tags', 'Amount']
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Clean amount first to handle NaN values early
    df['amount'] = (df['Amount'].astype(str)
                   .str.replace('$', '')
                   .str.replace(',', '')
                   .astype(float))
    
    # Handle transaction types and amounts
    if source_type == 'credit':
        # Credit card payments (positive amounts) remain positive
        # Credit card charges (negative amounts) remain negative
        df['transaction_type'] = df['amount'].apply(lambda x: 'credit' if x > 0 else 'debit')
    else:
        df['transaction_type'] = df['amount'].apply(lambda x: 'credit' if x > 0 else 'debit')
    
    # Drop rows with invalid amounts
    invalid_amounts = df['amount'].isna()
    if invalid_amounts.any():
        logger.warning(f"Dropping {invalid_amounts.sum()} rows with invalid amounts")
        df = df.dropna(subset=['amount'])
    
    # Process other fields
    df['transaction_date'] = pd.to_datetime(df['Date'])
    df['description'] = df['Description'].str.strip()
    df['category'] = df['Category'].str.strip()
    df['tags'] = df['Tags'].fillna('')
    
    # Calculate fiscal periods and month
    fiscal_data = df['transaction_date'].apply(determine_fiscal_periods)
    df['fiscal_year'] = fiscal_data.apply(lambda x: x['fiscal_year'])
    df['fiscal_quarter'] = fiscal_data.apply(lambda x: x['fiscal_quarter'])
    df['month'] = fiscal_data.apply(lambda x: x['month'])
    
    # Additional fields with empty strings for nullable text fields
    df['original_filename'] = filename
    df['is_recurring'] = False
    df['subcategory'] = ''
    df['budget_category'] = ''
    
    return df

def transform_to_parquet(input_path: Path) -> Path:
    """Transform CSV to Parquet with unified schema."""
    logger.info(f"Processing {input_path}")
    
    institution_name, account_name, source_type = parse_filename(input_path.name)
    
    df = pd.read_csv(input_path)
    df = preprocess_transaction_data(df, source_type, input_path.name)
    
    # Add institutional information
    df['institution_name'] = institution_name
    df['account_name'] = account_name
    df['source_type'] = source_type
    
    # Select and order columns to match database schema
    output_cols = [
        'transaction_date', 'description', 'amount', 'category',
        'subcategory', 'tags', 'account_name', 'institution_name',
        'source_type', 'transaction_type', 'is_recurring', 'month',
        'fiscal_year', 'fiscal_quarter', 'budget_category',
        'original_filename'
    ]
    
    df = df[output_cols]
    
    output_path = input_path.with_suffix('.parquet')
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved Parquet file: {output_path}")
    
    return output_path

def load_to_postgres(parquet_path: Path, db_params: Dict[str, str]) -> None:
    """Load Parquet file to PostgreSQL transactions table."""
    logger.info(f"Loading {parquet_path} to PostgreSQL")
    
    try:
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()
        
        sql = f"""
        COPY transactions (
            transaction_date, description, amount, category,
            subcategory, tags, account_name, institution_name,
            source_type, transaction_type, is_recurring, month,
            fiscal_year, fiscal_quarter, budget_category,
            original_filename
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
    parser = argparse.ArgumentParser(description='Load transaction data into unified database')
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