#!/usr/bin/env python3
"""Block destructive git commands from agent shell execution."""

import json
import re
import sys

DENY_PATTERNS = [
    re.compile(r"git push(\s|$).*(-f|--force)"),
    re.compile(r"git push -f\b"),
    re.compile(r"git reset --hard"),
    re.compile(r"git clean -f"),
    re.compile(r"git branch -D"),
]

DENY_RESPONSE = {
    "permission": "deny",
    "user_message": "Destructive git command blocked by project hook.",
    "agent_message": (
        "This git command was blocked by .cursor/hooks/block_destructive_git.py. "
        "Ask the user to run it manually if needed."
    ),
}

ALLOW_RESPONSE = {"permission": "allow"}


def main():
    data = json.load(sys.stdin)
    command = data.get("command", "")

    for pattern in DENY_PATTERNS:
        if pattern.search(command):
            print(json.dumps(DENY_RESPONSE))
            return 0

    print(json.dumps(ALLOW_RESPONSE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
