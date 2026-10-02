# Autor: Maksymilian Dyla, firma Cart-pack
"""Local Hakari inbox. Python 3.10+, standard library only.

Run: python receiver.py
Read pending batches from inbox.sqlite3, table batches, status='pending'.
Receiving a batch does not execute any order operations.
"""
import json
import re
import secrets
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'


def init_db(path):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('''CREATE TABLE IF NOT EXISTS batches (
            request_id TEXT PRIMARY KEY, shop TEXT NOT NULL,
            order_ids TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')


def save_batch(path, payload):
    if not isinstance(payload, dict):
        raise ValueError('Invalid payload')
    request_id = payload.get('request_id')
    ids = payload.get('order_ids')
    if (not isinstance(request_id, str) or
            not re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', request_id) or
            payload.get('shop') != 'kartony24h.com' or
            not isinstance(ids, list) or not 1 <= len(ids) <= 5000 or
            any(not isinstance(i, str) or not re.fullmatch(r'[1-9][0-9]{0,19}', i) for i in ids)):
        raise ValueError('Invalid order IDs or request ID')
    ids = sorted(set(ids))
    encoded = json.dumps(ids)
    with closing(sqlite3.connect(path, timeout=10)) as db, db:
        db.execute('INSERT OR IGNORE INTO batches(request_id, shop, order_ids) VALUES (?, ?, ?)',
                   (request_id, payload['shop'], encoded))
        stored = db.execute('SELECT shop, order_ids FROM batches WHERE request_id=?', (request_id,)).fetchone()
        if stored != (payload['shop'], encoded):
            raise ValueError('Request ID already used for a different batch')
    return {'request_id': request_id, 'accepted': len(ids)}


def handler_for(token, db_path):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *_args):
            pass  # Never log authorization headers or order payloads.

        def reply(self, code, data):
            body = json.dumps(data).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
                return self.reply(403, {'error': 'Invalid host'})
            if self.path != '/orders':
                return self.reply(404, {'error': 'Not found'})
            if not secrets.compare_digest(self.headers.get('Authorization', ''), f'Bearer {token}'):
                return self.reply(401, {'error': 'Unauthorized'})
            origin = self.headers.get('Origin', '')
            if origin and not re.fullmatch(r'chrome-extension://[a-p]{32}', origin):
                return self.reply(403, {'error': 'Invalid origin'})
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                return self.reply(415, {'error': 'Expected JSON'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 200000:
                    return self.reply(413, {'error': 'Invalid body size'})
                result = save_batch(db_path, json.loads(self.rfile.read(length)))
            except (ValueError, UnicodeError):
                return self.reply(400, {'error': 'Invalid batch'})
            except sqlite3.Error:
                return self.reply(503, {'error': 'Cannot save batch; retry'})
            self.reply(200, result)
    return Handler


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    token_path = DATA / 'connection-key.txt'
    if not token_path.exists():
        token_path.write_text(secrets.token_urlsafe(32), encoding='utf-8')
    token = token_path.read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
        raise SystemExit('Invalid connection-key.txt')
    db_path = DATA / 'inbox.sqlite3'
    init_db(db_path)
    try:
        server = ThreadingHTTPServer(('127.0.0.1', 8765), handler_for(token, db_path))
    except OSError as error:
        raise SystemExit(f'Cannot start receiver on port 8765: {error}') from error
    print('Hakari: http://127.0.0.1:8765 — keep this window open.', flush=True)
    print(f'Connection key (paste into Hakari): {token}', flush=True)
    print(f'Inbox: {db_path}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
