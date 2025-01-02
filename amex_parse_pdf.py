import os
import re
import pandas as pd
from PyPDF2 import PdfReader
import argparse

def extract_transactions_from_pdf(folder_path, output_csv="transactions.csv"):
    # Updated patterns for better matching
    date_pattern = r"^\d{2}/\d{2}/\d{4}"
    id_pattern = r"ID\s+\d{9,}"
    amount_pattern = r'\(?\$[\d,]+\.\d{2}\)?'  # Matches both ($XX.XX) and $XX.XX
    
    # Patterns for rows to exclude
    exclude_patterns = [
        r"Beginning Balance",
        r"Ending Balance",
        r"Important Notice",
        r"Member FDIC",
        r"Direct inquiries",
        r"Accounts offered by"
    ]
    exclude_regex = re.compile('|'.join(exclude_patterns), re.IGNORECASE)

    transaction_data = []
    
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".pdf"):
            file_path = os.path.join(folder_path, file_name)
            reader = PdfReader(file_path)
            
            for page in reader.pages:
                content = page.extract_text()
                
                # Remove everything after and including "Important Notice"
                if "Important Notice" in content:
                    content = content.split("Important Notice")[0]
                
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                
                # Filter out lines with exclude patterns
                lines = [line for line in lines if not exclude_regex.search(line)]
                
                current_transaction = {
                    'date': None,
                    'description': [],
                    'credits': None,
                    'debits': None,
                    'balance': None
                }

                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    
                    # Skip header lines
                    if any(header in line for header in ['Date', 'Description', 'Credits', 'Debits', 'Balance']):
                        i += 1
                        continue

                    # Check for date and description
                    date_match = re.match(fr"({date_pattern})\s*(.*)", line)
                    if date_match:
                        # Save previous transaction if exists
                        if current_transaction['date'] and (current_transaction['description'] or 
                           current_transaction['credits'] or current_transaction['debits']):
                            transaction_data.append([
                                current_transaction['date'],
                                ' '.join(current_transaction['description']).strip(),
                                current_transaction['credits'],
                                current_transaction['debits'],
                                current_transaction['balance']
                            ])
                        
                        # Start new transaction
                        current_transaction = {
                            'date': date_match.group(1),
                            'description': [],
                            'credits': None,
                            'debits': None,
                            'balance': None
                        }
                        
                        # Add description part if it exists
                        desc_part = date_match.group(2).strip()
                        if desc_part:
                            if "Important Notice" in desc_part:
                                desc_part = desc_part.split("Important Notice")[0].strip()
                            if desc_part:
                                current_transaction['description'].append(desc_part)
                        
                        # Check next line for continuation of description and amounts
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            amounts = re.findall(amount_pattern, next_line)
                            
                            if amounts:
                                # Remove amounts from description
                                desc_text = re.sub(amount_pattern, '', next_line).strip()
                                if desc_text:
                                    current_transaction['description'].append(desc_text)
                                
                                # Process amounts
                                for amount in reversed(amounts):  # Process in reverse to handle balance last
                                    if current_transaction['balance'] is None:
                                        current_transaction['balance'] = amount
                                    elif '(' in amount:
                                        current_transaction['debits'] = amount
                                    else:
                                        current_transaction['credits'] = amount
                                i += 1  # Skip next line since we've processed it
                        
                        i += 1
                        continue

                    # Handle lines with amounts
                    amounts = re.findall(amount_pattern, line)
                    if amounts:
                        # Remove amounts from description and split at Important Notice
                        desc_text = re.sub(amount_pattern, '', line).strip()
                        if "Important Notice" in desc_text:
                            desc_text = desc_text.split("Important Notice")[0].strip()
                        if desc_text:
                            current_transaction['description'].append(desc_text)
                        
                        # Process amounts
                        for amount in reversed(amounts):
                            if current_transaction['balance'] is None:
                                current_transaction['balance'] = amount
                            elif '(' in amount:
                                current_transaction['debits'] = amount
                            else:
                                current_transaction['credits'] = amount
                    else:
                        # Line with no amounts - add to description
                        current_transaction['description'].append(line)
                    
                    i += 1

                # Add last transaction from the page if it's not in excluded patterns
                if current_transaction['date'] and (current_transaction['description'] or 
                   current_transaction['credits'] or current_transaction['debits']):
                    desc = ' '.join(current_transaction['description']).strip()
                    if not exclude_regex.search(desc):
                        transaction_data.append([
                            current_transaction['date'],
                            desc,
                            current_transaction['credits'],
                            current_transaction['debits'],
                            current_transaction['balance']
                        ])

    # Create DataFrame and clean up
    df = pd.DataFrame(transaction_data, columns=["Date", "Description", "Credits", "Debits", "Balance"])
    
    # Additional filter to remove any remaining unwanted rows
    df = df[~df['Description'].str.contains('|'.join(exclude_patterns), case=False, na=False)]
    
    # Clean up description - remove multiple spaces and trailing/leading spaces
    df["Description"] = df["Description"].apply(lambda x: ' '.join(x.split()))
    
    # Remove any remaining amount patterns from description
    df["Description"] = df["Description"].apply(lambda x: re.sub(amount_pattern, '', x).strip())
    
    # Ensure amounts are properly formatted
    df["Credits"] = df["Credits"].fillna("")
    df["Debits"] = df["Debits"].fillna("")
    df["Balance"] = df["Balance"].fillna("")

    # Sort by date
    df = df.sort_values("Date")

    # Save to CSV
    output_path = os.path.join(folder_path, output_csv)
    df.to_csv(output_path, index=False)
    print(f"Transactions extracted and saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Extract transactions from PDF files and save to a CSV.")
    parser.add_argument("--inputdir", required=True, help="Path to the folder containing PDF files")
    parser.add_argument("--outputcsv", default="transactions.csv", help="Name of the output CSV file (optional)")
    args = parser.parse_args()
    extract_transactions_from_pdf(args.inputdir, args.outputcsv)

if __name__ == "__main__":
    main()