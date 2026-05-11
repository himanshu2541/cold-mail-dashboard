import json
import os
import pandas as pd
from copy import deepcopy

# Directories
DATA_DIR = "data"
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
ATTACHMENTS_DIR = os.path.join(DATA_DIR, "attachments")

DEFAULT_TRACKING_STATUS = "active"
FOLLOW_UP_READY_STATUSES = {"active"}


def _default_follow_up_selected(delivery_status, manual_status):
    return delivery_status == "success" and manual_status in FOLLOW_UP_READY_STATUSES


def _extract_email_from_row(row):
    for key, value in row.items():
        if isinstance(key, str) and "email" in key.lower():
            return value or ""
    return ""


def normalize_sent_history(sent_history):
    normalized = []
    for item in sent_history or []:
        entry = dict(item)
        status = str(entry.get("status", "")).lower()
        delivery = "success" if status == "success" else "failed"

        if "delivery_status" not in entry:
            entry["delivery_status"] = delivery
        if "manual_status" not in entry:
            entry["manual_status"] = DEFAULT_TRACKING_STATUS if delivery == "success" else "failed"
        if "follow_up_stage" not in entry:
            entry["follow_up_stage"] = 0
        if "selected_for_follow_up" not in entry:
            entry["selected_for_follow_up"] = _default_follow_up_selected(
                entry["delivery_status"],
                entry["manual_status"],
            )
        if "thread_root_message_id" not in entry:
            entry["thread_root_message_id"] = entry.get("message_id")
        if "last_message_id" not in entry:
            entry["last_message_id"] = entry.get("message_id")
        if "references" not in entry:
            entry["references"] = entry.get("message_id")
        if "last_error" not in entry:
            entry["last_error"] = "" if delivery == "success" else str(entry.get("status", ""))

        normalized.append(entry)
    return normalized


def build_tracking_state(df, sent_history, tracking_state=None):
    records = {}

    if df is not None and "_id" in df.columns:
        for row in df.to_dict(orient="records"):
            uid = row.get("_id")
            if not uid:
                continue
            records[uid] = {
                "id": uid,
                "email": _extract_email_from_row(row),
                "delivery_status": "pending",
                "manual_status": DEFAULT_TRACKING_STATUS,
                "follow_up_stage": 0,
                "selected_for_follow_up": False,
                "thread_root_message_id": None,
                "last_message_id": None,
                "references": None,
                "last_sent_at": None,
                "last_error": "",
            }

    for item in normalize_sent_history(sent_history):
        uid = item.get("id")
        if not uid:
            continue
        base = records.get(uid, {"id": uid})
        base["email"] = item.get("email", base.get("email", ""))
        base["delivery_status"] = item.get("delivery_status", "pending")
        base["manual_status"] = item.get("manual_status", base.get("manual_status", DEFAULT_TRACKING_STATUS))
        base["follow_up_stage"] = item.get("follow_up_stage", base.get("follow_up_stage", 0))
        base["selected_for_follow_up"] = item.get(
            "selected_for_follow_up",
            base.get(
                "selected_for_follow_up",
                _default_follow_up_selected(base["delivery_status"], base["manual_status"]),
            ),
        )
        base["thread_root_message_id"] = item.get("thread_root_message_id") or base.get("thread_root_message_id")
        base["last_message_id"] = item.get("last_message_id") or base.get("last_message_id")
        base["references"] = item.get("references") or base.get("references")
        base["last_sent_at"] = item.get("timestamp", base.get("last_sent_at"))
        base["last_error"] = item.get("last_error", base.get("last_error", ""))
        records[uid] = base

    # Tracking state contains the latest manual decisions from the UI, so it must
    # override older values reconstructed from send history.
    for uid, item in (tracking_state or {}).items():
        base = records.get(uid, {"id": uid})
        base.update(item)
        records[uid] = base

    return records


def update_tracking_entry(tracking_state, history_item):
    uid = history_item["id"]
    current = deepcopy(tracking_state.get(uid, {"id": uid}))
    current["email"] = history_item.get("email", current.get("email", ""))
    current["delivery_status"] = history_item.get("delivery_status", current.get("delivery_status", "pending"))
    current["manual_status"] = history_item.get("manual_status", current.get("manual_status", DEFAULT_TRACKING_STATUS))
    current["follow_up_stage"] = history_item.get("follow_up_stage", current.get("follow_up_stage", 0))
    current["selected_for_follow_up"] = history_item.get(
        "selected_for_follow_up",
        current.get(
            "selected_for_follow_up",
            _default_follow_up_selected(current["delivery_status"], current["manual_status"]),
        ),
    )
    current["thread_root_message_id"] = history_item.get("thread_root_message_id") or current.get("thread_root_message_id")
    current["last_message_id"] = history_item.get("last_message_id") or current.get("last_message_id")
    current["references"] = history_item.get("references") or current.get("references")
    current["last_sent_at"] = history_item.get("timestamp", current.get("last_sent_at"))
    current["last_error"] = history_item.get("last_error", current.get("last_error", ""))
    tracking_state[uid] = current
    return current


def set_tracking_manual_updates(tracking_state, updates):
    for item in updates:
        uid = item.get("id")
        if not uid or uid not in tracking_state:
            continue

        manual_status = item.get("manual_status", tracking_state[uid].get("manual_status", DEFAULT_TRACKING_STATUS))
        selected = bool(item.get("selected_for_follow_up", tracking_state[uid].get("selected_for_follow_up", False)))

        if manual_status not in FOLLOW_UP_READY_STATUSES:
            selected = False

        tracking_state[uid]["manual_status"] = manual_status
        tracking_state[uid]["selected_for_follow_up"] = selected


def create_follow_up_session(source_session_name, new_session_name, source_state):
    if not new_session_name:
        return False, "Follow-up session name is required."

    target_path = os.path.join(SESSIONS_DIR, f"{new_session_name}.json")
    if os.path.exists(target_path):
        return False, f"Session '{new_session_name}' already exists."

    tracking_state = source_state.get("tracking_state", {})
    selected_ids = [
        uid
        for uid, item in tracking_state.items()
        if item.get("selected_for_follow_up")
        and item.get("delivery_status") == "success"
        and item.get("manual_status") in FOLLOW_UP_READY_STATUSES
    ]

    if not selected_ids:
        return False, "No selected recipients are eligible for follow-up."

    source_df = source_state.get("data")
    if source_df is None or source_df.empty:
        return False, "Current session has no recipient data to build the follow-up list."

    follow_up_df = source_df[source_df["_id"].isin(selected_ids)].copy()
    if follow_up_df.empty:
        return False, "Selected recipients could not be matched to session data."

    next_stage = max((tracking_state[uid].get("follow_up_stage", 0) for uid in selected_ids), default=0) + 1
    next_tracking = {}

    for uid in selected_ids:
        entry = deepcopy(tracking_state[uid])
        entry["delivery_status"] = "pending"
        entry["selected_for_follow_up"] = False
        entry["follow_up_stage"] = next_stage
        entry["last_error"] = ""
        next_tracking[uid] = entry

    ok = save_session(
        new_session_name,
        source_state.get("template", {}),
        source_state.get("mapping", {}),
        follow_up_df,
        set(),
        [],
        tracking_state=next_tracking,
        campaign_stage=next_stage,
        parent_session=source_session_name,
    )
    if not ok:
        return False, "Failed to save follow-up session."

    for uid in selected_ids:
        tracking_state[uid]["selected_for_follow_up"] = False

    return True, f"Created follow-up session '{new_session_name}' with {len(selected_ids)} recipients."

def init_dirs():
    """Ensures all necessary directories exist"""
    for d in [SESSIONS_DIR, TEMPLATES_DIR, ATTACHMENTS_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

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

def save_session(
    session_name,
    template_data,
    mapping,
    df,
    sent_ids,
    sent_history,
    tracking_state=None,
    campaign_stage=0,
    parent_session=None,
):
    init_dirs()
    normalized_history = normalize_sent_history(sent_history)
    merged_tracking = build_tracking_state(df, normalized_history, tracking_state)
    state = {
        "template": template_data,
        "mapping": mapping,
        "sent_ids": list(sent_ids),
        "sent_history": normalized_history,
        "tracking_state": merged_tracking,
        "campaign_stage": campaign_stage,
        "parent_session": parent_session,
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
        state['sent_history'] = normalize_sent_history(state.get('sent_history', []))
        state['tracking_state'] = build_tracking_state(
            state['data'],
            state['sent_history'],
            state.get('tracking_state', {}),
        )
        state['campaign_stage'] = state.get('campaign_stage', 0)
        state['parent_session'] = state.get('parent_session')
        
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
