import json
import os
import pandas as pd
import shutil

# Directories
DATA_DIR = "data"
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
# Unified Attachment Pool
ATTACHMENTS_DIR = os.path.join(DATA_DIR, "attachments")

def init_dirs():
    """Ensures all necessary directories exist"""
    for d in [SESSIONS_DIR, TEMPLATES_DIR, ATTACHMENTS_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

# --- HELPER: SMART DELETE ---
def _get_all_used_attachments(ignore_file_path=None):
    """
    Scans ALL sessions and templates to find which attachment paths are currently in use.
    Returns a set of file paths.
    """
    used_paths = set()
    
    # 1. Scan Sessions
    for f in os.listdir(SESSIONS_DIR):
        if f.endswith(".json"):
            full_p = os.path.join(SESSIONS_DIR, f)
            if full_p == ignore_file_path: continue # Skip the file we are about to delete
            try:
                with open(full_p, 'r') as jf:
                    data = json.load(jf)
                    # Check template dict inside session
                    if data.get('template') and data['template'].get('attachment_path'):
                        used_paths.add(os.path.normpath(data['template']['attachment_path']))
            except: pass

    # 2. Scan Templates
    for f in os.listdir(TEMPLATES_DIR):
        if f.endswith(".json"):
            full_p = os.path.join(TEMPLATES_DIR, f)
            if full_p == ignore_file_path: continue # Skip the file we are about to delete
            try:
                with open(full_p, 'r') as jf:
                    data = json.load(jf)
                    if data.get('attachment_path'):
                        used_paths.add(os.path.normpath(data['attachment_path']))
            except: pass
            
    return used_paths

def _delete_attachment_safely(att_path, current_json_path):
    """
    Deletes the attachment file ONLY if no other session/template uses it.
    """
    if not att_path or not os.path.exists(att_path):
        return

    # Normalize for comparison
    target_path = os.path.normpath(att_path)
    
    # Get all other paths being used
    used_paths = _get_all_used_attachments(ignore_file_path=current_json_path)
    
    if target_path not in used_paths:
        try:
            os.remove(target_path)
            print(f"Cleaned up unused attachment: {target_path}")
        except Exception as e:
            print(f"Error deleting file: {e}")
    else:
        print(f"Skipped deletion: Attachment is used by other sessions/templates.")

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

def delete_session(session_name):
    """Deletes a session and checks if its attachment can be cleaned up"""
    filepath = os.path.join(SESSIONS_DIR, f"{session_name}.json")
    
    if os.path.exists(filepath):
        # 1. Check for attachment to cleanup
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if data.get('template'):
                    att_path = data['template'].get('attachment_path')
                    _delete_attachment_safely(att_path, filepath)
        except: pass
        
        # 2. Delete JSON
        os.remove(filepath)
        return True
    return False

# --- TEMPLATE LIBRARY MANAGEMENT ---
def list_templates():
    init_dirs()
    files = [f.replace('.json', '') for f in os.listdir(TEMPLATES_DIR) if f.endswith('.json')]
    return sorted(files)

def save_template_file(name, subject, body, is_html, attachment_path=None, attachment_name=None):
    init_dirs()

    data = {
        "subject": subject,
        "body": body,
        "is_html": is_html,
        "attachment_path": attachment_path, # Just save the path reference
        "attachment_name": attachment_name
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

def delete_template_file(name):
    """Deletes a template and checks if its attachment can be cleaned up"""
    filepath = os.path.join(TEMPLATES_DIR, f"{name}.json")
    
    if os.path.exists(filepath):
        # 1. Check for attachment to cleanup
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                att_path = data.get('attachment_path')
                _delete_attachment_safely(att_path, filepath)
        except: pass
        
        # 2. Delete JSON
        os.remove(filepath)
        return True
    return False