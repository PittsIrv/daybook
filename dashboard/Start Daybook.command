#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Daybook needs Python 3.9+. Install it from https://www.python.org/downloads/macos/ and try again.'
  read -r -p 'Press Return to close.'
  exit 1
fi
python3 launch.py
result=$?
if [ "$result" -ne 0 ]; then read -r -p 'Press Return to close.'; fi
exit "$result"
