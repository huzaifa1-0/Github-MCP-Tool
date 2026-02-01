import os
import secrets
import httpx
import uvicorn
from typing import Any
from fastapi import FastAPI, Request, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Standard MCP SDK
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types 

# --- CONFIGURATION ---
CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
# On Render, this will be your https://....onrender.com URL
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

# Use a file-based DB (Note: On Render Free Tier, this resets on redeploy)
DATABASE_URL = "sqlite:///./github_tool.db"

# --- DATABASE SETUP ---
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    session_id = Column(String, primary_key=True, index=True)
    access_token = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- MCP SERVER LOGIC ---
mcp = Server("github-manager")

async def call_github(endpoint: str, token: str, method="GET", json_data=None):
    async with httpx.AsyncClient() as client:
        return await client.request(
            method, f"https://api.github.com{endpoint}",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "Huzaifa-MCP-Tool"},
            json=json_data
        )

@mcp.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_repositories", 
            description="Lists your recent GitHub repositories.", 
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="create_issue", 
            description="Creates a GitHub issue.", 
            inputSchema={
                "type": "object", 
                "properties": {
                    "owner": {"type": "string"}, "repo": {"type": "string"},
                    "title": {"type": "string"}, "body": {"type": "string"}
                },
                "required": ["owner", "repo", "title", "body"]
            }
        ),
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: Any) -> list[types.TextContent]:
    # 1. Get Session ID from the request context
    session_id = None
    if mcp.request_context and mcp.request_context.meta:
        session_id = mcp.request_context.meta.get("session_id")

    if not session_id:
        return [types.TextContent(type="text", text="❌ Error: No session ID found.")]

    # 2. Look up User
    db = SessionLocal()
    user = db.query(User).filter(User.session_id == session_id).first()
    db.close()
    
    if not user:
        return [types.TextContent(type="text", text="❌ Unauthorized. Please login via the Web Interface.")]

    # 3. Execute Tool
    if name == "list_repositories":
        resp = await call_github("/user/repos?sort=updated&per_page=5", user.access_token)
        if resp.status_code != 200: return [types.TextContent(type="text", text=f"GitHub API Error: {resp.text}")]
        repos = resp.json()
        return [types.TextContent(type="text", text="\n".join([f"- {r['name']} ({r['html_url']})" for r in repos]))]
    
    elif name == "create_issue":
        url = f"/repos/{arguments['owner']}/{arguments['repo']}/issues"
        resp = await call_github(url, user.access_token, "POST", {"title": arguments['title'], "body": arguments['body']})
        return [types.TextContent(type="text", text=f"✅ Issue Created: {resp.json().get('html_url')}")]

    return [types.TextContent(type="text", text="Tool not found.")]

# --- WEB SERVER (FastAPI) ---
app = FastAPI()
sse = SseServerTransport("/sse")

@app.get("/login")
def login():
    state = secrets.token_urlsafe(16)
    return RedirectResponse(f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&state={state}&scope=repo,user")

@app.get("/callback")
async def callback(code: str, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://github.com/login/oauth/access_token", 
            headers={"Accept": "application/json"},
            data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "code": code})
        token = resp.json().get("access_token")
    
    if not token: return f"Error logging in: {resp.text}"

    session_id = secrets.token_hex(16)
    db.add(User(session_id=session_id, access_token=token))
    db.commit()
    
    return HTMLResponse(f"""
    <div style='font-family: sans-serif; text-align: center; padding: 50px;'>
        <h1>✅ Login Successful!</h1>
        <p>Your Session ID is:</p>
        <code style='background: #eee; padding: 10px; font-size: 1.2em;'>{session_id}</code>
        <p>Copy this ID into your client_proxy.py file.</p>
    </div>
    """)

@app.get("/sse")
async def handle_sse(session_id: str, request: Request):
    async with sse.connect_sse(request, response_writer=Response, meta={"session_id": session_id}) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

@app.post("/sse")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.json(), request)

if __name__ == "__main__":
    # Render uses the PORT env var, defaulting to 10000
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)