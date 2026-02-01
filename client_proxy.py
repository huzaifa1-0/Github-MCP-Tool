from fastmcp import FastMCP

# 1. PASTE YOUR SESSION ID HERE
SESSION_ID = "PASTE_THE_SESSION_ID_YOU_COPIED_HERE"

# 2. YOUR RENDER URL
# IMPORTANT: Ensure this matches your deployment URL and ends with /sse
BASE_URL = "https://your-app-name.onrender.com" 

# We construct the full URL with the session ID
REMOTE_URL = f"{BASE_URL}/sse?session_id={SESSION_ID}"

# 3. Create the Proxy
# Passing REMOTE_URL as the first positional argument
mcp = FastMCP.as_proxy(
    REMOTE_URL,
    name="Render GitHub Tool"
)

if __name__ == "__main__":
    mcp.run()