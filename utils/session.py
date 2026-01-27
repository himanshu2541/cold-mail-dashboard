import json
import os
import pandas as pd
import shutil

# Directories
SESSIONS_DIR = os.path.join("data", "sessions")
TEMPLATES_DIR = os.path.join("data", "templates")
ATTACHMENTS_DIR = os.path.join("data", "attachments")

def init_dirs():
    """Ensures all necessary directories exist"""
    for d in [SESSIONS_DIR, TEMPLATES_DIR, ATTACHMENTS_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

# --- SESSION MANAGEMENT ---
def list_sessions():
    init_dirs()
    files = [f.replace('.json', '') for f in os.listdir(SESSIONS_DIR) if f.endswith('.json')]
    return sorted(files)

def save_session(session_name, template_data, mapping, df, sent_ids):
    init_dirs()
    state = {
        "template": template_data,
        "mapping": mapping,
        "sent_ids": list(sent_ids),
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
    filepath = os.path.join(SESSIONS_DIR, f"{session_name}.json")
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        if state.get('data'):
            state['data'] = pd.DataFrame(state['data'])
        else:
            state['data'] = None
            
        state['sent_ids'] = set(state.get('sent_ids', []))
        
        # Defaults
        if not state.get('template'):
            state['template'] = {'subject': '', 'body': '', 'is_html': False}
        if not state.get('mapping'):
            state['mapping'] = {}
            
        return state
    except Exception as e:
        print(f"Error loading session: {e}")
        return None

# --- TEMPLATE LIBRARY MANAGEMENT ---
def list_templates():
    init_dirs()
    files = [f.replace('.json', '') for f in os.listdir(TEMPLATES_DIR) if f.endswith('.json')]
    return sorted(files)

def save_template_file(name, subject, body, is_html):
    init_dirs()
    data = {
        "subject": subject,
        "body": body,
        "is_html": is_html
    }
    filepath = os.path.join(TEMPLATES_DIR, f"{name}.json")
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving template: {e}")
        return False

def load_template_file(name):
    filepath = os.path.join(TEMPLATES_DIR, f"{name}.json")
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading template: {e}")
        return None