import pandas as pd
import hashlib
import re

def process_data(df, email_col_name):
    """
    1. Splits rows with multiple emails (comma or whitespace separated).
    2. Generates a stable Unique ID for each row.
    """
    processed_rows = []

    for idx, row in df.iterrows():
        raw_email = str(row[email_col_name]).strip() if pd.notna(row[email_col_name]) else ""

        # Skip empty / nan-like
        if not raw_email or raw_email.lower() == "nan":
            continue

        # Split by comma OR any whitespace
        emails = [e for e in re.split(r"[,\s]+", raw_email) if e]

        for email in emails:
            new_row = row.to_dict()
            new_row[email_col_name] = email

            unique_str = f"{idx}-{email}"
            new_row["_id"] = hashlib.md5(unique_str.encode()).hexdigest()[:12]

            processed_rows.append(new_row)

    return pd.DataFrame(processed_rows)
