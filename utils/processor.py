import pandas as pd
import hashlib
import uuid

def process_data(df, email_col_name):
    """
    1. Splits rows with multiple emails (comma separated).
    2. Generates a stable Unique ID for each row.
    """
    processed_rows = []
    
    # Iterate through the raw data
    for idx, row in df.iterrows():
        raw_email = str(row[email_col_name]) if pd.notna(row[email_col_name]) else ""
        
        # Skip empty
        if not raw_email or raw_email.lower() == 'nan':
            continue
            
        # Split by comma (handle "email1, email2")
        emails = [e.strip() for e in raw_email.split(',') if e.strip()]
        
        for email in emails:
            # Create a copy of the row data
            new_row = row.to_dict()
            
            # Update with the specific single email
            new_row[email_col_name] = email
            
            # Generate a Unique ID
            # specific combination of email + original index ensures uniqueness
            unique_str = f"{idx}-{email}"
            new_row['_id'] = hashlib.md5(unique_str.encode()).hexdigest()[:12]
            
            processed_rows.append(new_row)
            
    return pd.DataFrame(processed_rows)