import json
import os
import pandas as pd

STATE_FILE = "project_state.json"

def save_state(template_data, mapping, df, sent_ids):
    """Saves the current session to disk."""
    state = {
        "template": template_data, # {subject, body, is_html}
        "mapping": mapping,        # {var: column}
        "sent_ids": list(sent_ids), # List of IDs already processed
        "data": df.to_dict(orient='records') if df is not None else None
    }
    
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    return True

def load_state():
    """Loads the previous session if it exists."""
    if not os.path.exists(STATE_FILE):
        return None
        
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            
        # Convert data back to DataFrame
        if state['data']:
            state['data'] = pd.DataFrame(state['data'])
            
        # Convert sent_ids back to set
        state['sent_ids'] = set(state['sent_ids'])
        
        return state
    except Exception as e:
        print(f"Error loading state: {e}")
        return None