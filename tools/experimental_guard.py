#!/usr/bin/env python3
"""Fail closed if an experimental benchmark is accidentally given production publishing credentials."""
import os
import sys

FORBIDDEN = (
    "YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_CLIENT_ID",
    "GOOGLE_OAUTH", "UPLOAD_TOKEN", "PUBLISH_TOKEN",
)

def main():
    exposed = sorted(key for key, value in os.environ.items()
                     if value and any(key.upper().startswith(prefix) for prefix in FORBIDDEN))
    if exposed:
        print("Experimental environment has production-like credential variables: " + ", ".join(exposed), file=sys.stderr)
        return 1
    print("Experimental credential isolation preflight passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
