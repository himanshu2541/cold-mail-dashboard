import json
import os
import pandas as pd

# Create a folder for sessions if it doesn't exist
SESSIONS_DIR = "sessions"

def init_session_dir():
    """Ensures the sessions directory exists"""
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR)

def list_sessions():
    """Returns a list of available session names"""
    init_session_dir()
    files = [f.replace('.json', '') for f in os.listdir(SESSIONS_DIR) if f.endswith('.json')]
    return sorted(files)

def save_session(session_name, template_data, mapping, df, sent_ids):
    """Saves the specific session to a JSON file"""
    init_session_dir()
    
    # Clean/Prepare data for JSON
    state = {
        "template": template_data,   # {subject, body, is_html}
        "mapping": mapping,          # {var: column}
        "sent_ids": list(sent_ids),  # Convert set to list
        "data": df.to_dict(orient='records') if df is not None else None
    }
    
    filepath = os.path.join(SESSIONS_DIR, f"{session_name}.json")
    try:
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving session: {e}")
        return False

def load_session(session_name):
    """Loads a specific session by name"""
    filepath = os.path.join(SESSIONS_DIR, f"{session_name}.json")
    
    if not os.path.exists(filepath):
        return None
        
    try:
        with open(filepath, 'r') as f:
            state = json.load(f)
            
        # Reconstruct DataFrame
        if state.get('data'):
            state['data'] = pd.DataFrame(state['data'])
        else:
            state['data'] = None
            
        # Reconstruct Set
        state['sent_ids'] = set(state.get('sent_ids', []))
        
        # Ensure template defaults
        if not state.get('template'):
            state['template'] = {'subject': '', 'body': '', 'is_html': False}
            
        if not state.get('mapping'):
            state['mapping'] = {}
            
        return state
    except Exception as e:
        print(f"Error loading session: {e}")
        return None

def delete_session(session_name):
    """Deletes a session file"""
    filepath = os.path.join(SESSIONS_DIR, f"{session_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False