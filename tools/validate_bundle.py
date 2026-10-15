#!/usr/bin/env python3
"""Validate archived syntax, local assets, pricing and the reproducible snapshot.

Runs offline; does not read customer exports or contact merchant services.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'output', 'private'}


def files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file()
                  and not set(p.relative_to(ROOT).parts) & EXCLUDED)


def command(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed: {result.stderr}')
    return result.stdout


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('src', 'href'):
            if key in attrs:
                ref = urlsplit(attrs[key])
                if ref.path and not ref.scheme and not ref.netloc:
                    self.refs.append(unquote(ref.path))


def digest_tree(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}


def main():
    counts = {'python': 0, 'javascript': 0, 'json': 0, 'html': 0}
    node = shutil.which('node')
    for path in files():
        if path.suffix == '.py':
            ast.parse(path.read_text(), filename=str(path))
            counts['python'] += 1
        elif path.suffix == '.json':
            json.loads(path.read_text())
            counts['json'] += 1
        elif path.suffix in ('.js', '.mjs') and node:
            command([node, '--check', str(path)])
            counts['javascript'] += 1
        elif path.suffix == '.html' and 'examples' in path.parts:
            parser = Assets()
            parser.feed(path.read_text())
            for ref in parser.refs:
                asset = path.parent / ref
                if not asset.is_file():
                    raise FileNotFoundError(f'{path.relative_to(ROOT)} -> {ref}')
            counts['html'] += 1

    calculator = ROOT / 'skills/dewu-confirm-bid-discount/scripts/price_for_takehome.py'
    for target, expected in [(159, 198), (169, 211), (189, 236)]:
        result = json.loads(command([sys.executable, str(calculator), '--target', str(target), '--discount', '8']))
        if result['candidate_bid'] != expected or not result['candidate_verified']:
            raise ValueError(f'Pricing regression for target {target}')

    weekly = ROOT / 'projects/weekly-report'
    with tempfile.TemporaryDirectory(prefix='dewu-sop-check-') as temp:
        output = Path(temp) / 'site'
        command([sys.executable, str(weekly / 'build_snapshot.py'), '--output', str(output)])
        if digest_tree(output) != digest_tree(weekly / 'examples/20261005-1011/site'):
            raise ValueError('Rebuilt weekly snapshot differs from archived site')

    daily = ROOT / 'projects/product-analytics'
    daily_result = 'skipped: Node.js not found'
    if node:
        daily_result = json.loads(command([
            node, str(daily / 'work/validate-daily-1014.mjs'),
            str(daily / 'examples/2026-10-14/site/index.html')]))

    print(json.dumps({'status': 'passed', 'syntax_and_assets': counts,
                      'node_syntax': 'passed' if node else 'skipped: Node.js not found',
                      'pricing_cases': 3, 'weekly_snapshot': 'byte-identical',
                      'daily_snapshot': daily_result,
                      'raw_order_reconciliation': 'requires local private inputs; see docs/validation.md'},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
