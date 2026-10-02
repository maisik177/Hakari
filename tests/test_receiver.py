# Autor: Maksymilian Dyla, firma Cart-pack
import importlib.util
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

spec = importlib.util.spec_from_file_location('receiver', Path(__file__).resolve().parents[1] / 'python/receiver.py')
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'inbox.sqlite3'
        receiver.init_db(self.db)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), receiver.handler_for('test-key', self.db))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.payload = {'request_id': 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee', 'shop': 'kartony24h.com', 'order_ids': ['123', '456']}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, payload=None, key='test-key', **headers):
        req = urllib.request.Request(f'http://127.0.0.1:{self.server.server_port}/orders',
            data=json.dumps(payload if payload is not None else self.payload).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}', **headers})
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_persists_and_retry_does_not_duplicate(self):
        for _ in range(2):
            code, body = self.post()
            self.assertEqual(code, 200)
            self.assertEqual(body['accepted'], 2)
        with closing(sqlite3.connect(self.db)) as db:
            rows = db.execute('SELECT order_ids, status FROM batches').fetchall()
        self.assertEqual(rows, [(json.dumps(['123', '456']), 'pending')])

    def test_rejects_unauthorized_and_web_origins(self):
        self.assertEqual(self.post(key='wrong')[0], 401)
        self.assertEqual(self.post(Origin='https://example.com')[0], 403)
        self.assertEqual(self.post(Host='example.com')[0], 403)

    def test_invalid_and_conflicting_batches(self):
        self.assertEqual(self.post({**self.payload, 'order_ids': ['on']})[0], 400)
        self.assertEqual(self.post({**self.payload, 'order_ids': []})[0], 400)
        self.assertEqual(self.post()[0], 200)
        self.assertEqual(self.post({**self.payload, 'order_ids': ['789']})[0], 400)


if __name__ == '__main__':
    unittest.main()
