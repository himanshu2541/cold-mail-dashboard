# Cold Mail Dashboard

## Overview

This project is a streamlined, locally hosted dashboard for managing and executing cold email campaigns. It allows you to create reusable templates, manage recipient lists, and send emails with customizable delays and batching controls. All data and metadata are stored locally on your machine.

## Features

- **Smart Duplicate Prevention:** Each data entry is assigned a unique ID based on the email and row index. The system checks a local history to ensure emails are never sent twice to the same recipient ID.
- **Local Data Security:** All metadata, session logs, and templates are stored locally on your device.
- **Traffic Control:** Customizable delay times, batch sizes, and daily sending limits to mimic human activity and avoid spam filters.
- **Session Management:** Save and resume campaigns without losing progress.

## Installation

### 1) Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2) Sync Dependencies

```bash
uv sync
```

### 3) Configure Credentials

Create a `.env` file in the project root and add:

```env
SENDER_EMAIL=name@example.com
APP_PASSWORD=xxxx xxxx xxxx xxxx
```

**Note:** For Gmail, generate an App Password in your Google Account settings (Security → 2-Step Verification → App passwords). Do not use your standard login password.

### 4) Run the Application

```bash
# Activate virtual environment
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Run the app
streamlit run app.py
```

## Usage

### 1) Create Session

Start by creating a new session in the sidebar. This isolates your campaign data and history.

### 2) Create and Save Template

Write your email **Subject** and **Body** in the editor.

- Use placeholders like `{Name}` or `{Company}` to personalize emails.
- Save your template with a specific name so it is not lost when you close the app.
- If sending an attachment, upload the file and provide a display name (rename) for the recipient.

### 3) Upload and Map Data]

Upload your processed (cleaned) `.xlsx` or `.csv` recipient list. Map the columns in the dashboard to match the variables in your template.

### 4) Preview

Scroll down to the **Preview** section. Verify that the emails look correct and variables are populating properly.

### 5) Launch Campaign

Select the **Launch** tab, confirm the email column is correct, and click **Start Campaign**. The system will begin processing the queue.

## Settings

You can customize sending behavior in the sidebar:

- **Min/Max Delay:** Random interval (seconds) between individual emails.
- **Batch Size:** Number of emails to send before a longer pause.
- **Batch Pause:** Duration of the pause between batches.
- **Daily Limit:** Maximum number of emails to send per day.
