import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow

app = FastAPI()

GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REDIRECT_URI = os.environ["GOOGLE_REDIRECT_URI"]  # e.g. https://.../auth/callback

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def build_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

    return flow


@app.get("/auth/start")
async def auth_start():
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # For simplicity we’re not storing state server-side; Google includes it back unchanged.
    response = RedirectResponse(auth_url)
    return response

@app.get("/auth/callback", response_class=HTMLResponse)
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return HTMLResponse(
            "<h2>Missing authorization code.</h2>",
            status_code=400,
        )

    # Exchange code for tokens
    flow = build_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Build token.json-style content for your local app
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
        "type": "authorized_user",
    }

    import json
    token_json = json.dumps(token_data, indent=2)

    # Simple HTML page with instructions
    html = f"""
    <html>
      <head>
        <title>Google Drive Token Ready</title>
        <style>
          body {{
            background:#111;
            color:#eee;
            font-family:system-ui, sans-serif;
            padding:2rem;
            max-width:800px;
            margin:auto;
          }}
          textarea {{
            width:100%;
            height:300px;
            background:#222;
            color:#eee;
            border:1px solid #444;
            border-radius:8px;
            padding:.6rem;
            font-family:monospace;
            font-size:0.9rem;
          }}
          button {{
            padding:0.6rem 1rem;
            margin-top:1rem;
            margin-right:0.5rem;
            border-radius:6px;
            border:none;
            background:#18b09f;
            color:#000;
            font-weight:600;
            cursor:pointer;
          }}
          button:hover {{
            filter:brightness(1.2);
          }}
        </style>
      </head>
      <body>
        <h1>Google Drive Token Ready</h1>
        <p>Download the token.json file or copy the contents below.</p>

        <textarea id="tokenBox" readonly onclick="this.select();">{token_json}</textarea>

        <br/>

        <button onclick="downloadToken()">Download token.json</button>
        <button onclick="copyToken()">Copy to clipboard</button>

        <script>
          function downloadToken() {{
            const data = `{token_json}`;
            const blob = new Blob([data], {{ type: "application/json" }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "token.json";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
          }}

          function copyToken() {{
            const text = document.getElementById("tokenBox").value;
            navigator.clipboard.writeText(text).then(() => {{
              alert("Token copied to clipboard");
            }});
          }}
        </script>
      </body>
    </html>
    """
    return HTMLResponse(html)
