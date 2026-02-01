# Remote GitHub Manager

**Tagline:** A secure, remote MCP tool to manage GitHub repositories and issues via AI.

## Overview
The Remote GitHub Manager is a powerful MCP tool that bridges your AI assistant (Claude) with your GitHub account. Unlike simple local tools, this runs as a secure cloud service. It handles authentication via OAuth, allowing you to perform actions like listing repositories and creating issues without exposing your raw API keys to the chat interface.

**Deployment Status:** ✅ Live on Render

## Key Features
* **📂 List Repositories:** Instantly fetch a list of your most recently updated repositories (`list_repositories`).
* **🐛 Create Issues:** Open new issues in any repository with a title and body directly from the chat (`create_issue`).
* **🔒 Secure Auth:** Uses GitHub OAuth to generate a temporary Session ID, keeping your credentials safe.

---

## 🚀 How to Connect (For Users)

Because this tool accesses your private GitHub data, it requires a secure login step before you can connect it to Claude Desktop.

### Prerequisites
* Python 3.10 or higher installed.
* [Claude Desktop](https://claude.ai/download) installed.

### Step 1: Authenticate & Get Session ID
1. Open your web browser and visit the **Login URL** provided by the tool host:
   > `https://<YOUR-APP-NAME>.onrender.com/login`
2. Authorize the application with your GitHub account.
3. Once successful, you will see a **Session ID** (e.g., `a1b2c3d4...`). **Copy this ID.**

### Step 2: Configure the Connection Script
Save the code below as `client_proxy.py` on your computer.

```python
from fastmcp import FastMCP

# --- CONFIGURATION ---
# 1. Paste the Session ID you copied from the browser
SESSION_ID = "PASTE_YOUR_SESSION_ID_HERE"

# 2. The URL of the deployed tool
BASE_URL = "https://<YOUR-APP-NAME>.onrender.com" 
# ---------------------

# Construct the secure URL
REMOTE_URL = f"{BASE_URL}/sse?session_id={SESSION_ID}"

# Initialize the proxy
mcp = FastMCP.as_proxy(
    REMOTE_URL,
    name="GitHub Manager"
)

if __name__ == "__main__":
    mcp.run()
