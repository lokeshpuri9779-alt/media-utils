from pathlib import Path
import json, os, sys
from cryptography.fernet import Fernet

base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "AstraYouTubeAutopilot"
key_path = base / ".astra_key"
oauth_path = base / "youtube_oauth.enc"
token_path = base / "youtube_token.enc"

missing = [str(p) for p in (key_path, oauth_path, token_path) if not p.exists()]
if missing:
    print("Existing Astra YouTube login was not found in the expected location.")
    print("Missing:")
    for p in missing:
        print(" -", p)
    sys.exit(1)

f = Fernet(key_path.read_bytes())
oauth = json.loads(f.decrypt(oauth_path.read_bytes()).decode("utf-8"))
token = json.loads(f.decrypt(token_path.read_bytes()).decode("utf-8"))

print("Copy these ONLY into GitHub repository secrets. Do not paste them into chat.")
print()
print("YOUTUBE_CLIENT_ID=" + str(oauth.get("client_id") or ""))
print("YOUTUBE_CLIENT_SECRET=" + str(oauth.get("client_secret") or ""))
print("YOUTUBE_REFRESH_TOKEN=" + str(token.get("refresh_token") or ""))
