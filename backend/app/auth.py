import os
from fastapi import Header, HTTPException

# Set EDITOR_PASSWORD in Render's environment variables.
# Viewing the calendar/tracker needs no login at all (supervisor just opens the link).
# Marking a task done requires this key, sent as header "X-Editor-Key".
EDITOR_PASSWORD = os.environ.get("EDITOR_PASSWORD", "changeme")


def require_editor(x_editor_key: str = Header(default="")):
    if x_editor_key != EDITOR_PASSWORD:
        raise HTTPException(401, "Invalid or missing editor key")
    return True
