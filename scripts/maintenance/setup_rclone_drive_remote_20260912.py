"""Repair the rclone Drive token value in the local rclone config.

Purpose: rclone 1.75 stores OAuth tokens as a JSON string. The non-interactive
`config create` path left the raw base64 blob in place, so every command failed
with "invalid character 'e' looking for beginning of value". This script writes
the correctly quoted JSON string form so the remote works.

Security boundary: reads the authorize blob from the local log and rewrites only
the machine-local rclone config; it never prints the token and never copies it
into the repository.
"""

import base64
import json
import pathlib
import re
import sys

AUTHORIZE_LOG = r"D:\Project\.tools\rclone-authorize.log"
CONFIG = pathlib.Path(r"C:\Users\550ACW\AppData\Roaming\rclone\rclone.conf")


def decoded_inner_token() -> dict:
    text = pathlib.Path(AUTHORIZE_LOG).read_text(encoding="utf-8", errors="replace")
    match = re.search(r"machine --->\s*(\S+)\s*<---End paste", text, re.DOTALL)
    if not match:
        raise SystemExit("token blob not found")
    blob = re.sub(r"\s+", "", match.group(1))
    blob += "=" * (-len(blob) % 4)
    outer = json.loads(base64.b64decode(blob))
    inner = outer["token"]
    return json.loads(inner) if isinstance(inner, str) else inner


def main() -> int:
    inner = decoded_inner_token()
    if not inner.get("refresh_token"):
        raise SystemExit("decoded token has no refresh_token")

    quoted = json.dumps(inner)  # one JSON object, in the form rclone expects
    lines = CONFIG.read_text(encoding="utf-8").splitlines()
    out = []
    replaced = 0
    for line in lines:
        if line.startswith("token =") or line.startswith("token="):
            out.append(f"token = {quoted}")
            replaced += 1
        else:
            out.append(line)
    if replaced != 1:
        raise SystemExit(f"expected exactly one token line, found {replaced}")
    CONFIG.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("token line rewritten; config lines:", len(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
