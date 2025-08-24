#!/usr/bin/env python3
"""Lightweight pre-commit secret scanner.

Checks staged files for occurrences of SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET
and long hex-like tokens (28-40 hex chars). Exit code 1 if finds potential secrets.
"""
import argparse
import os
import re
import subprocess
import sys

HEX_RE = re.compile(r"[A-Fa-f0-9]{28,40}")
SPOT_RE = re.compile(r"SPOTIFY_CLIENT_(ID|SECRET)")
SKIP_DIRS = ('venv', '.venv', 'data', 'tests', 'notebooks', '.git')
SKIP_FILES = ('README.md', '.env.template', 'scripts/precommit_check.py')


def get_staged_files():
    # If inside a git repo, scan staged files only. Otherwise scan workspace files.
    if os.path.exists('.git'):
        try:
            out = subprocess.check_output(
                ["git", "diff", "--cached", "--name-only"], text=True)
            return [l.strip() for l in out.splitlines() if l.strip()]
        except Exception:
            pass
    files = []
    for root, _, filenames in os.walk('.'):
        # skip venv and git metadata
        if any(part in (' .venv', '.venv', 'venv') for part in root.split(os.sep)):
            continue
        for fn in filenames:
            if fn.endswith(('.py', '.md', '.env', '.txt', '.json', '.sh')):
                files.append(os.path.join(root, fn))
    return files


def scan_file(path):
    # normalize path and skip known dirs/files
    norm = path.lstrip('./')
    # skip specific files
    if any(norm.endswith(sf) or norm == sf for sf in SKIP_FILES):
        return []
    # skip directories
    first = norm.split(os.sep)[0] if norm else ''
    if first in SKIP_DIRS:
        return []
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return []
    findings = []
    # detect same-line non-empty assignments to SPOTIFY_CLIENT_ID/SECRET
    for i, line in enumerate(content.splitlines()):
        if SPOT_RE.search(line) and '=' in line:
            # ignore code patterns (os.getenv, f.write, function calls)
            if 'os.getenv' in line or 'f.write' in line or 'def ' in line or 'return' in line:
                continue
            # check for literal assignment like SPOTIFY_CLIENT_ID=abcdef123...
            m = re.search(
                r"SPOTIFY_CLIENT_(?:ID|SECRET)\s*=\s*([\"']?)([^\"'\s#]+)\1", line)
            if m:
                rhs = m.group(2)
                # if RHS looks like a token (alphanumeric, dashes, underscores, length>16), flag it
                if re.match(r"^[A-Za-z0-9_\-]{16,}$", rhs):
                    findings.append(
                        (path, 'SPOTIFY literal assignment', line.strip()))
    for m in HEX_RE.finditer(content):
        window = content[max(0, m.start()-50):m.end()+50]
        # ignore Spotify image ids and scdn URLs (common in raw JSON)
        if 'scdn.co' in window or 'ab6761' in window.lower():
            continue
        findings.append((path, 'Hex-like token', window.strip()))
    return findings


def main(staged_only=True):
    files = get_staged_files() if staged_only else None
    if files is None:
        print('Scanning entire workspace...')
        files = get_staged_files()
    findings = []
    for p in files:
        if p.startswith('.git') or p.startswith('.venv'):
            continue
        findings.extend(scan_file(p))
    if findings:
        print('Potential secrets found:')
        for path, kind, snippet in findings:
            print(f'- {path}: {kind}: {snippet}')
        return 1
    print('No potential secrets found.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--staged', dest='staged',
                        action='store_true', help='scan staged files only')
    parser.add_argument('--staged-only', dest='staged', action='store_true')
    args = parser.parse_args()
    rc = main(staged_only=args.staged)
    sys.exit(rc)
