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
        <title>Frigate Backup Manager - Google Drive Token</title>
        <style>
          body {{
            background: #101010;
            color: #f0f0f0;
            font-family: system-ui, sans-serif;
            padding: 1.5rem;
          }}
          textarea {{
            width: 100%;
            height: 300px;
            background: #181818;
            color: #f0f0f0;
            border-radius: 8px;
            border: 1px solid #444;
            padding: 0.5rem;
            font-family: monospace;
            font-size: 0.85rem;
          }}
          .box {{
            max-width: 800px;
            margin: 0 auto;
          }}
          button {{
            margin-top: 0.5rem;
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            border: none;
            background: #18b09f;
            color: #000;
            font-weight: 600;
            cursor: pointer;
          }}
        </style>
      </head>
      <body>
        <div class="box">
          <h1>Google Drive Token Ready</h1>
          <p>Step 1: Click the button below to download <code>token.json</code>, or copy the content.</p>
          <p>Step 2: In your Frigate Backup Manager UI, open <strong>Google Drive Configuration</strong>.</p>
          <p>Step 3: Paste this JSON into the token box or upload the file.</p>

          <textarea readonly onclick="this.select();">{token_json}</textarea>

          <form method="post" action="data:application/json;base64,{token_json.encode('utf-8').hex()}">
            <!-- NOTE: in practice you'd generate a downloadable blob via JS;
                 here we focus on the copy-paste UX. -->
          </form>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(html)
