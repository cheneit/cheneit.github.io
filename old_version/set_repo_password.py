#!/usr/bin/env python3
from __future__ import annotations
import argparse
import getpass
import hashlib
import re
from pathlib import Path

PATTERN = re.compile(r"const PASSWORD_HASH = '[0-9a-fA-F]{64}';")

def main():
    ap = argparse.ArgumentParser(description='Set Repo Library page password by replacing PASSWORD_HASH in an HTML file.')
    ap.add_argument('html', help='Path to Repo Library HTML, e.g. index_v3.3_private.html')
    ap.add_argument('--password', help='New password. If omitted, prompt securely.')
    args = ap.parse_args()

    p = Path(args.html)
    if not p.is_file():
        raise SystemExit(f'File not found: {p}')

    password = args.password
    if password is None:
        p1 = getpass.getpass('New page password: ')
        p2 = getpass.getpass('Confirm password: ')
        if p1 != p2:
            raise SystemExit('Passwords do not match.')
        password = p1

    if not password:
        raise SystemExit('Password cannot be empty.')

    text = p.read_text(encoding='utf-8')
    digest = hashlib.sha256(password.encode('utf-8')).hexdigest()
    replacement = f"const PASSWORD_HASH = '{digest}';"
    updated, n = PATTERN.subn(replacement, text, count=1)
    if n != 1:
        raise SystemExit('Could not find exactly one PASSWORD_HASH constant in the HTML.')

    backup = p.with_suffix(p.suffix + '.bak')
    backup.write_text(text, encoding='utf-8')
    p.write_text(updated, encoding='utf-8')
    print(f'Updated: {p}')
    print(f'Backup : {backup}')
    print('Existing browser authorizations will be invalidated automatically because the stored auth marker includes the password hash.')

if __name__ == '__main__':
    main()
