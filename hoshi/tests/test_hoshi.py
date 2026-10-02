# Autor: Maksymilian Dyla, firma Cart-pack
import importlib.util
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('hoshi_core', Path(__file__).parents[1] / 'hoshi.py')
hoshi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hoshi)


def order(serial=123):
    return {'orderSerialNumber': serial, 'clientResult': {'clientBillingAddress': {'clientNip': '1234567890'}},
            'orderDetails': {'clientRequestInvoice': 'e_invoice', 'orderSourceResults': {'auctionsServiceName': 'allegro'},
              'auctionInfo': {'auctionClientLogin': 'buyer-not-seller'},
              'payments': {'orderPaymentType': 'prepaid'},
              'prepaids': [{'paymentNumber': '123-1', 'payformName': 'Allegro Finanse', 'paymentStatus': 'y',
                           'paymentValue': 12, 'currencyId': 'PLN', 'paymentType': 'payment'}],
              'productsResults': [{'productId': 1, 'productName': '<script>alert(1)</script>', 'productQuantity': 2}]}}


class HoshiTests(unittest.TestCase):
    def test_ids_validate_deduplicate_preserve_order(self):
        self.assertEqual(hoshi.parse_ids('3,1;3\n2'), ['3', '1', '2'])
        for value in ['', '0', '../7', '1&orders=2', '123abc']:
            with self.assertRaises(hoshi.HoshiError):
                hoshi.parse_ids(value)

    def test_invoice_live_codes_and_unknown(self):
        for code in ['e_invoice', 'e', 'y', 'invoice']:
            self.assertTrue(hoshi.invoice_label(code).startswith('TAK'))
        self.assertEqual(hoshi.invoice_label('n'), 'NIE')
        self.assertIn('brak danych', hoshi.invoice_label(None))
        self.assertIn('brak danych', hoshi.invoice_label('unexpected'))

    def test_render_does_not_infer_invoice_from_nip_or_paid_from_y(self):
        value = order()
        value['orderDetails'].pop('clientRequestInvoice')
        result = hoshi.render([value], {}, {}, {})
        self.assertIn('FAKTURA: brak danych', result)
        self.assertIn('1234567890', result)
        self.assertIn('status nierozpoznany (API: y)', result)
        self.assertNotIn('opłacone', result)

    def test_escape_customer_content_and_distinguish_accounts(self):
        result = hoshi.render([order()], {'123': 'seller'}, {}, {'123-1': {'status': 'pending'}})
        self.assertIn('konto: <b>seller</b>', result)
        self.assertIn('buyer-not-seller', result)
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertIn('status API: pending', result)
        self.assertIn('Allegro Finanse', result)
        self.assertNotIn('Allegro Pay', result)
        self.assertNotIn('typ: payment', result)

    def test_missing_requested_orders_fail(self):
        api = hoshi.Api('test')
        with patch.object(api, 'call', return_value={'Results': [order()]}):
            with self.assertRaises(hoshi.HoshiError):
                api.orders(['123', '124'])

    def test_bulk_orders_chunked_and_ordered(self):
        api = hoshi.Api('test')
        ids = [str(i) for i in range(1, 102)]
        def respond(_endpoint, params):
            return {'Results': [order(int(i)) for i in reversed(params['ordersSerialNumbers'].split(','))]}
        with patch.object(api, 'call', side_effect=respond) as call:
            self.assertEqual([str(o['orderSerialNumber']) for o in api.orders(ids)], ids)
            self.assertEqual(call.call_count, 2)

    def test_api_is_read_only_and_redirects_rejected(self):
        api = hoshi.Api('test')
        for endpoint, body in [('payments/confirm', None), ('orders/orders', {'params': {}})]:
            with self.assertRaises(hoshi.HoshiError):
                api.call(endpoint, body=body)
        self.assertIsNone(hoshi.NoRedirect().redirect_request(None, None, None, None, None, None))

    def test_api_fault_detection(self):
        self.assertFalse(hoshi.has_error({'errors': [], 'faultCode': 0}))
        self.assertTrue(hoshi.has_error({'Results': [{'errors': {'faultCode': 7}}]}))

    def test_images_restrict_origin_and_scheme(self):
        for url in ['http://kartony24h.com/a.jpg', 'https://evil.test/a.jpg', 'https://kartony24h.com:999/a', 'file:///a']:
            self.assertIsNone(hoshi.fetch_image(url))

    @unittest.skipUnless(sys.platform == 'win32', 'Windows DPAPI')
    def test_key_encrypted_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(hoshi, 'DATA', Path(directory)):
            hoshi.save_key('unit-test-not-a-real-key')
            self.assertEqual(hoshi.load_key(), 'unit-test-not-a-real-key')
            self.assertNotIn(b'unit-test-not-a-real-key', (Path(directory) / 'api-key.dpapi').read_bytes())

    def test_queue_deduplicates_and_keeps_hakari_intact(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(hoshi, 'DATA', Path(directory)):
            inbox = Path(directory) / 'inbox.sqlite3'
            with closing(sqlite3.connect(inbox)) as db, db:
                db.execute('CREATE TABLE batches(request_id TEXT,shop TEXT,order_ids TEXT,status TEXT,received_at TEXT)')
                db.execute('INSERT INTO batches VALUES (?,?,?,?,?)', ('test-batch', hoshi.SHOP, '["123"]', 'pending', '2026-01-01'))
            path = Path(directory) / 'output.html'
            with patch.object(hoshi, 'generate', return_value=(path, {'warnings': []})) as generate:
                self.assertEqual(hoshi.process_queue(inbox=inbox), [path])
                self.assertEqual(hoshi.process_queue(inbox=inbox), [])
                self.assertEqual(generate.call_count, 1)
            with closing(sqlite3.connect(inbox)) as db:
                self.assertEqual(db.execute('SELECT status FROM batches').fetchone()[0], 'pending')

    def test_queue_failure_is_retryable(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(hoshi, 'DATA', Path(directory)):
            batch = [('test', hoshi.SHOP, '["123"]')]
            with patch.object(hoshi, 'pending_batches', return_value=batch):
                with patch.object(hoshi, 'generate', side_effect=hoshi.HoshiError('HTTP 403')):
                    with self.assertRaises(hoshi.HoshiError):
                        hoshi.process_queue()
                with patch.object(hoshi, 'generate', return_value=(Path(directory) / 'ok.html', {'warnings': []})):
                    self.assertEqual(len(hoshi.process_queue()), 1)


if __name__ == '__main__':
    unittest.main()
