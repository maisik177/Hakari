# Autor: Maksymilian Dyla, firma Cart-pack
"""Hoshi 0.1: read-only IdoSell client and compact, offline printable order cards."""
from __future__ import annotations

from contextlib import closing
import argparse
import base64
import ctypes
from ctypes import wintypes
from datetime import datetime
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
SHOP = 'kartony24h.com'
INBOX = ROOT.parent / 'python' / 'data' / 'inbox.sqlite3'
MISSING = 'brak danych'


class HoshiError(Exception):
    pass


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def protect(value: bytes, decrypt=False):
    if os.name != 'nt':
        raise HoshiError('Zapamiętywanie klucza wymaga Windows (DPAPI).')

    class Blob(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise HoshiError('Nie można odczytać/zapisać klucza Windows. Skonfiguruj klucz na tym koncie użytkownika.')
    try:
        return ctypes.string_at(output.data, output.length)
    finally:
        kernel.LocalFree(output.data)


def save_key(key):
    key = key.strip()
    if not key or any(c.isspace() for c in key) or len(key) > 4096:
        raise HoshiError('Niepoprawny format klucza API.')
    atomic_write(DATA / 'api-key.dpapi', protect(key.encode('utf-8')))


def load_key():
    try:
        return protect((DATA / 'api-key.dpapi').read_bytes(), decrypt=True).decode('utf-8')
    except OSError:
        raise HoshiError('Najpierw zaimportuj plik z kluczem API.') from None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Never forward API credentials to a redirect target.


def has_error(value):
    if isinstance(value, list):
        return any(has_error(x) for x in value)
    if isinstance(value, dict):
        return bool(value.get('faultCode') not in (None, 0, '0', '')) or any(
            has_error(x) for x in value.values() if isinstance(x, (dict, list)))
    return False


class Api:
    ALLOWED = {'orders/orders', 'orders/orders/search', 'orders/auctionDetails',
               'products/products', 'payments/forms', 'payments/payments'}

    def __init__(self, key=None):
        self.key = key if key is not None else load_key()
        self.opener = urllib.request.build_opener(NoRedirect)
        self.audit = []

    def call(self, endpoint, params=None, body=None):
        if endpoint not in self.ALLOWED or (body is not None and endpoint != 'orders/orders/search'):
            raise HoshiError('Niedozwolona operacja API.')
        method = 'POST' if body is not None else 'GET'
        url = f'https://{SHOP}/api/admin/v8/{endpoint}'
        if params:
            url += '?' + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
            headers={'X-API-KEY': self.key, 'Accept': 'application/json', 'Content-Type': 'application/json'})
        for attempt in range(3):
            try:
                with self.opener.open(request, timeout=35) as response:
                    result = json.load(response)
                    self.audit.append({'endpoint': endpoint, 'method': method, 'http': response.status})
                    if not isinstance(result, dict):
                        raise HoshiError(f'{method} {endpoint}: nieoczekiwany format odpowiedzi.')
                    if has_error(result) or result.get('isErrors'):
                        raise HoshiError(f'{method} {endpoint}: API zgłosiło błąd danych.')
                    return result
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                self.audit.append({'endpoint': endpoint, 'method': method, 'http': exc.code})
                hint = {401: 'nieprawidłowy lub nieaktywny klucz', 403: 'brak uprawnienia lub ograniczenie IP'}.get(exc.code, 'błąd żądania')
                raise HoshiError(f'{method} {endpoint}: HTTP {exc.code} — {hint}.') from None
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                raise HoshiError(f'{method} {endpoint}: błąd połączenia lub niepoprawna odpowiedź.') from None

    def orders(self, ids):
        found = {}
        for start in range(0, len(ids), 100):
            response = self.call('orders/orders', {'ordersSerialNumbers': ','.join(ids[start:start + 100])})
            for order in response.get('Results', []):
                found[str(order['orderSerialNumber'])] = order
        missing = [i for i in ids if i not in found]
        if missing:
            raise HoshiError('API nie zwróciło wszystkich zamówień: ' + ', '.join(missing))
        return [found[i] for i in ids]


def parse_ids(text):
    ids = list(dict.fromkeys(re.split(r'[\s,;]+', text.strip())))
    if not ids or len(ids) > 5000 or any(not re.fullmatch(r'[1-9][0-9]{0,19}', i) for i in ids):
        raise HoshiError('Podaj numery zamówień oddzielone spacją, przecinkiem lub średnikiem (maks. 5000).')
    return ids


def invoice_label(code):
    return {'y': 'TAK — papierowa', 'e': 'TAK — elektroniczna', 'invoice': 'TAK — papierowa',
            'e_invoice': 'TAK — elektroniczna', 'n': 'NIE'}.get(code, MISSING + (f' (API: {code})' if code else ''))


def product_image(product):
    icon = product.get('productIcon') or {}
    images = product.get('productImages') or []
    return icon.get('productIconSmallUrl') or icon.get('productIconLargeUrl') or (
        images[0].get('productImageSmallUrl') or images[0].get('productImageLargeUrl') if images else None)


def fetch_image(url):
    if not url:
        return None
    try:
        parsed = urllib.parse.urlsplit(url)
        allowed = parsed.scheme == 'https' and parsed.hostname == SHOP and parsed.port in (None, 443) and not parsed.username
    except ValueError:
        return None
    # Public storefront image download never carries X-API-KEY.
    if not allowed:
        return None
    target = DATA / 'images' / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    if target.exists() and time.time() - target.stat().st_mtime < 86400:
        return json.loads(target.read_text(encoding='utf-8'))
    try:
        with urllib.request.build_opener(NoRedirect).open(url, timeout=20) as response:
            mime = response.headers.get_content_type()
            raw = response.read(2_000_001)
            if mime not in ('image/jpeg', 'image/png', 'image/webp', 'image/gif') or len(raw) > 2_000_000:
                return None
            data = f'data:{mime};base64,' + base64.b64encode(raw).decode('ascii')
            atomic_write(target, json.dumps(data).encode())
            return data
    except (urllib.error.URLError, OSError):
        return None


def enrich(api, orders):
    warnings, sellers, images, payments = [], {}, {}, {}
    ids = sorted({str(p['productId']) for o in orders for p in o['orderDetails'].get('productsResults', [])})
    for start in range(0, len(ids), 100):
        try:
            result = api.call('products/products', {'productIds': ','.join(ids[start:start + 100])})
            for product in result.get('results', []):
                images[str(product['productId'])] = fetch_image(product_image(product))
        except HoshiError as exc:
            warnings.append(str(exc))
    for order in orders:
        serial = str(order['orderSerialNumber'])
        details = order['orderDetails']
        source = details.get('orderSourceResults') or {}
        if source.get('auctionsServiceName') or source.get('orderSourceType') in ('auction', 'auctions'):
            try:
                # Single order per request: repeated query keys returned only one order in live testing.
                result = api.call('orders/auctionDetails', {'identType': 'orders_sn', 'orders': serial})
                for auction in result.get('auctions', []):
                    if str((auction.get('orderIdent') or {}).get('identValue')) == serial:
                        sellers[serial] = auction.get('auctionsAccountLogin')
            except HoshiError as exc:
                warnings.append(str(exc))
        for payment in details.get('prepaids') or []:
            number = payment.get('paymentNumber')
            if number and number not in payments:
                try:
                    payments[number] = api.call('payments/payments', {'paymentNumber': number, 'sourceType': 'order'}).get('result', {})
                except HoshiError as exc:
                    warnings.append(str(exc))
    return sellers, images, payments, list(dict.fromkeys(warnings))


def esc(value):
    return html.escape(str(value if value is not None and value != '' else MISSING), quote=True)


def render(orders, sellers, images, payments, warnings=()):
    cards = []
    for order in orders:
        d = order['orderDetails']; serial = str(order['orderSerialNumber'])
        c = order.get('clientResult') or {}; billing = c.get('clientBillingAddress') or {}
        delivery = c.get('clientDeliveryAddress') or {}; account = c.get('clientAccount') or {}
        source = d.get('orderSourceResults') or {}; source_detail = source.get('orderSourceDetails') or {}
        source_name = source_detail.get('orderSourceName') or source.get('auctionsServiceName') or source.get('orderSourceType')
        origin = esc(source_name)
        if source.get('auctionsServiceName') or source.get('orderSourceType') in ('auction', 'auctions'):
            origin += ' · konto: <b>' + esc(sellers.get(serial)) + '</b>'
        else:
            origin += ' · sklep ID: ' + esc(source.get('shopId'))
        invoice = invoice_label(d.get('clientRequestInvoice'))
        nip = billing.get('clientNip') or (c.get('payerAddress') or {}).get('payerAddressNip')
        pay_lines = []
        for p in d.get('prepaids') or []:
            extra = payments.get(p.get('paymentNumber'), {})
            status = extra.get('status')
            # Preserve API statuses; never infer full order settlement from one payment.
            status_text = 'status API: ' + str(status) if status else 'status nierozpoznany (API: ' + str(p.get('paymentStatus', '?')) + ')'
            pay_lines.append(f"{esc(p.get('payformName'))} · {esc(p.get('paymentValue'))} {esc(p.get('currencyId'))} · {esc(status_text)}")
        pay_type = (d.get('payments') or {}).get('orderPaymentType')
        pay_title = {'cash_on_delivery': 'Pobranie', 'prepaid': 'Przedpłata', 'tradecredit': 'Kredyt kupiecki'}.get(pay_type, pay_type or MISSING)
        if not pay_lines:
            pay_lines.append('Brak szczegółów transakcji w API')
        if pay_type == 'cash_on_delivery':
            pay_lines.append('Kwota do pobrania: do weryfikacji — nie wyliczono z wartości zamówienia')
        name = ' '.join(str(delivery.get(k) or '') for k in ('clientDeliveryAddressFirstName', 'clientDeliveryAddressLastName')).strip()
        name = name or billing.get('clientFirm') or ' '.join(str(billing.get(k) or '') for k in ('clientFirstName', 'clientLastName')).strip()
        login = (d.get('auctionInfo') or {}).get('auctionClientLogin') or account.get('clientLogin')
        pickup = (c.get('clientPickupPointAddress') or {}).get('pickupPointId')
        rows = []
        for p in d.get('productsResults') or []:
            image = images.get(str(p.get('productId')))
            photo = f'<img src="{esc(image)}" alt="Zdjęcie produktu">' if image else '<span class="no-photo">Brak<br>zdjęcia</span>'
            variant = ' · '.join(str(p.get(k)) for k in ('versionName', 'sizePanelName') if p.get(k))
            code = p.get('productSizeCodeExternal') or p.get('productCode') or p.get('productId')
            remark = '<div>Uwagi: ' + esc(p['remarksToProduct']) + '</div>' if p.get('remarksToProduct') else ''
            rows.append(f'<tr><td class="photo">{photo}</td><td><b>{esc(p.get("productName"))}</b><div class="sub">{esc(code)} · {esc(variant)}</div>{remark}</td><td class="qty">× {esc(p.get("productQuantity"))}</td><td class="check">□</td></tr>')
        notes = ''.join(f'<div class="note"><b>{label}:</b> {esc(d[key])}</div>' for key, label in
                        [('clientNoteToOrder', 'Uwagi klienta'), ('clientNoteToCourier', 'Uwagi dla kuriera'), ('orderNote', 'Uwagi wewnętrzne')] if d.get(key))
        cards.append(f'''<section class="order"><header><strong>#{esc(serial)}</strong><span>{origin}</span></header>
<div class="invoice"><b>FAKTURA: {esc(invoice)}</b><span>NIP: <b>{esc(nip)}</b></span></div>
<div><b>Płatność · {esc(pay_title)}:</b> {'<br>'.join(pay_lines)}</div>
<div><b>Dostawa:</b> {esc((d.get('dispatch') or {}).get('courierName'))}{' · ' + esc(pickup) if pickup else ''}</div>
<div><b>Klient:</b> {esc(name)} · {esc(login)}</div>
<table><thead><tr><th colspan="4">Produkty · zamówienie #{esc(serial)}</th></tr></thead><tbody>{''.join(rows)}</tbody></table>{notes}</section>''')
    warning_html = ''.join('<p>' + esc(w) + '</p>' for w in warnings)
    stamp = datetime.now().astimezone().isoformat(timespec='seconds')
    return f'''<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Hoshi — karty zamówień</title><style>
@page {{size:A4; margin:9mm}}
*{{box-sizing:border-box}} body{{margin:0;background:#e9edf1;color:#171717;font:12px/1.35 Arial,sans-serif}}
.toolbar{{max-width:192mm;margin:20px auto;padding:12px 0;font-size:14px}} .toolbar p{{margin:4px 0}}
main{{width:192mm;margin:0 auto 30px;background:white;padding:0 3mm}}
.order{{padding:3mm 0; border-bottom:1px dashed #777;break-inside:avoid-page;overflow-wrap:anywhere}}
header{{display:flex;gap:12px;align-items:baseline;justify-content:space-between;border-bottom:2px solid #222;margin-bottom:5px;padding-bottom:3px}}
header strong{{font-size:22px;white-space:nowrap}}header span{{font-size:13px;text-align:right}}
.invoice{{display:flex;justify-content:space-between;background:#f0f0f0;padding:4px 6px;margin-bottom:4px;font-size:14px;gap:12px}}
table{{width:100%;border-collapse:collapse;margin-top:4px}}th{{text-align:left;font-size:10px;font-weight:normal;color:#555;border-bottom:1px solid #ccc}}
td{{padding:3px 5px;border-bottom:1px solid #ddd;vertical-align:middle}}tr{{break-inside:avoid}}thead{{display:table-header-group}}
.photo{{width:17mm;padding-left:0}}img{{width:14mm;height:14mm;object-fit:contain}}.no-photo{{display:block;width:14mm;text-align:center;font-size:10px;color:#777}}
.qty{{font-weight:bold;font-size:19px;white-space:nowrap;text-align:right;width:19mm}}.check{{width:7mm;font-size:20px}}.sub,small{{font-size:10px;color:#444}}.note{{margin-top:4px;white-space:pre-wrap}}.warning{{color:#932800}}.footer{{font-size:9px;color:#555;padding:4px 0}}
@media print{{body{{background:white;font-size:10px}}main{{width:auto;margin:0;padding:0}}.toolbar{{display:none}}.invoice{{font-size:12px}}header strong{{font-size:20px}}}}
@media screen and (max-width:760px){{main,.toolbar{{width:auto;margin:12px}}header,.invoice{{flex-wrap:wrap}}}}
</style></head><body><div class="toolbar"><b>Hoshi 0.1 · {len(orders)} zamówień</b><p>Drukuj: Ctrl+P → A4, skala 100%, bez nagłówków i stopek przeglądarki.</p><p>Dane pobrane: {esc(stamp)}. Sprawdź braki danych przed pakowaniem.</p></div><main>
<div class="warning">{warning_html}</div>{''.join(cards)}<div class="footer">Hoshi · pobrano {esc(stamp)} · {len(orders)} zamówień</div></main></body></html>'''


def generate(ids, api=None, output=None):
    api = api or Api()
    orders = api.orders(ids)
    sellers, images, payments, warnings = enrich(api, orders)
    output = Path(output) if output else DATA / 'wydruki' / ('hoshi-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.html')
    atomic_write(output, render(orders, sellers, images, payments, warnings).encode('utf-8'))
    report = {'generated_at': datetime.now().astimezone().isoformat(), 'orders': len(orders),
              'invoice_known': sum(invoice_label(o['orderDetails'].get('clientRequestInvoice')).startswith(('TAK', 'NIE')) for o in orders),
              'nip_present': sum(bool((o.get('clientResult', {}).get('clientBillingAddress') or {}).get('clientNip')) for o in orders),
              'seller_accounts_found': sum(bool(x) for x in sellers.values()),
              'distinct_products': len({str(p['productId']) for o in orders for p in o['orderDetails'].get('productsResults', [])}),
              'photos_downloaded': sum(bool(x) for x in images.values()), 'payment_details': len(payments),
              'payment_names': sorted({p.get('payformName', '') for o in orders for p in o['orderDetails'].get('prepaids', [])}),
              'warnings': warnings, 'requests': api.audit}
    atomic_write(output.with_suffix('.report.json'), json.dumps(report, ensure_ascii=False, indent=2).encode('utf-8'))
    return output, report


def pending_batches(inbox=INBOX):
    if not Path(inbox).exists():
        return []
    with closing(sqlite3.connect(Path(inbox).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        return db.execute("SELECT request_id,shop,order_ids FROM batches WHERE status='pending' ORDER BY received_at,request_id").fetchall()


def process_queue(api=None, inbox=INBOX):
    DATA.mkdir(exist_ok=True)
    outputs = []
    with closing(sqlite3.connect(DATA / 'hoshi.sqlite3', timeout=3)) as ledger:
        ledger.execute('CREATE TABLE IF NOT EXISTS generated(request_id TEXT PRIMARY KEY, output TEXT NOT NULL)')
        for request_id, shop, encoded in pending_batches(inbox):
            if shop != SHOP:
                continue
            # Claim under transaction so two Hoshi instances cannot generate the same batch concurrently.
            ledger.execute('BEGIN IMMEDIATE')
            previous = ledger.execute('SELECT output FROM generated WHERE request_id=?', (request_id,)).fetchone()
            if previous:
                ledger.rollback()
                continue
            try:
                ids = parse_ids(' '.join(json.loads(encoded)))
                name = hashlib.sha256(request_id.encode()).hexdigest()[:24]
                output, report = generate(ids, api=api, output=DATA / 'wydruki' / f'batch-{name}.html')
                # Missing permissions should be retryable after configuration is corrected.
                if report['warnings']:
                    raise HoshiError('Niepełny wydruk zapisano do podglądu; paczka pozostaje do ponowienia. ' + '; '.join(report['warnings']))
                ledger.execute('INSERT INTO generated VALUES (?,?)', (request_id, str(output)))
                ledger.commit()
                outputs.append(output)
            except Exception:
                ledger.rollback()
                raise
    return outputs


def main():
    parser = argparse.ArgumentParser(description='Hoshi — wydruki z API IdoSell')
    sub = parser.add_subparsers(dest='command', required=True)
    setup = sub.add_parser('setup'); setup.add_argument('--key-file', type=Path, required=True)
    order = sub.add_parser('orders'); order.add_argument('ids', nargs='+'); order.add_argument('--open', action='store_true')
    recent = sub.add_parser('sample'); recent.add_argument('--limit', type=int, default=8)
    sub.add_parser('queue')
    args = parser.parse_args()
    try:
        if args.command == 'setup':
            key = args.key_file.read_text(encoding='utf-8-sig').strip()
            Api(key).call('orders/orders/search', body={'params': {'resultsLimit': 1, 'resultsPage': 0}})
            save_key(key)
            print('Klucz sprawdzony i zapisany w Windows DPAPI dla bieżącego użytkownika.')
        elif args.command == 'queue':
            for path in process_queue():
                print(path)
        else:
            api = Api()
            if args.command == 'sample':
                if not 1 <= args.limit <= 20:
                    raise HoshiError('Próbka musi liczyć od 1 do 20 zamówień.')
                result = api.call('orders/orders/search', body={'params': {'resultsLimit': args.limit, 'resultsPage': 0,
                    'ordersBy': [{'elementName': 'sn', 'sortDirection': 'DESC'}]}})
                ids = [str(o['orderSerialNumber']) for o in result.get('Results', [])]
                if not ids:
                    raise HoshiError('API nie zwróciło zamówień.')
            else:
                ids = parse_ids(' '.join(args.ids))
            path, report = generate(ids, api)
            print(path)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if getattr(args, 'open', False):
                webbrowser.open(path.as_uri())
    except (HoshiError, OSError, sqlite3.Error) as exc:
        # OS errors may contain paths, but never headers or the key.
        parser.exit(1, f'Hoshi: {exc}\n')


if __name__ == '__main__':
    main()
