#!/usr/bin/env bash
# Block destructive git commands from agent shell execution.
set -euo pipefail

input=$(cat)

command=$(python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('command', ''))
" <<< "$input")

deny() {
  python3 -c 'import json; print(json.dumps({"permission": "deny", "user_message": "Destructive git command blocked by project hook.", "agent_message": "This git command was blocked by .cursor/hooks/block-destructive-git.sh. Ask the user to run it manually if needed."}))'
  exit 0
}

allow() {
  echo '{"permission": "allow"}'
  exit 0
}

# Force push (including to main/master)
if echo "$command" | grep -qE 'git push(\s|$).*(-f|--force)'; then
  deny
fi
if echo "$command" | grep -qE 'git push -f\b'; then
  deny
fi

# Hard reset and destructive clean
if echo "$command" | grep -qE 'git reset --hard'; then
  deny
fi
if echo "$command" | grep -qE 'git clean -f'; then
  deny
fi

# Force branch delete
if echo "$command" | grep -qE 'git branch -D'; then
  deny
fi

allow
