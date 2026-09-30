const { test } = require('node:test');
const assert = require('node:assert/strict');
const { resolve, isOrderPage } = require('../content/tracking.js');

test('only exact HTTPS shop order pages, including the legacy iframe', () => {
  for (const path of ['/panel/orderd.php', '/panel/app/orderd.php']) {
    assert.equal(isOrderPage(`https://kartony24h.com${path}?idt=970`), true);
  }
  for (const url of ['https://evil.test/panel/orderd.php?idt=970', 'http://kartony24h.com/panel/orderd.php?idt=970', 'https://kartony24h.com/panel/orderd.php-extra?idt=970', 'https://kartony24h.com/panel/orderd.php']) {
    assert.equal(isOrderPage(url), false);
  }
});

test('carrier variants and exact tracking parameters preserve leading zeroes', () => {
  for (const [name, host, param] of [
    ['Allegro Kurier GLS', 'gls-group.com', 'match'],
    ['Allegro Paczkomaty InPost', 'inpost.pl', 'number'],
    ['Allegro DPD Pickup', 'tracktrace.dpd.com.pl', 'p1'],
    ['DHL eCommerce', 'www.dhl.com', 'tracking-id'],
    ['UPS Standard', 'www.ups.com', 'tracknum'],
    ['Allegro Kurier Pocztex', 'emonitoring.poczta-polska.pl', 'numer'],
    ['Poczta Polska', 'emonitoring.poczta-polska.pl', 'numer'],
    ['ORLEN Paczka', 'www.orlenpaczka.pl', 'numer'],
    ['FedEx', 'www.fedex.com', 'trknbr']
  ]) {
    const url = new URL(resolve(name, ' 001234567890 ').url);
    assert.equal(url.hostname, host);
    assert.equal(url.searchParams.get(param), '001234567890');
  }
});

test('unknown, ambiguous and Allegro Delivery carriers do not get guessed links', () => {
  for (const name of ['Odbiór osobisty', '', 'GLS / DPD', 'Allegro One Box DPD', 'Allegro Delivery ORLEN']) {
    assert.equal(resolve(name, '1234567890'), null);
  }
  assert.equal(resolve('ORLEN Paczka', 'AD1234567890'), null);
});

test('placeholder, order ID and unsafe values are ignored', () => {
  for (const number of ['', 'brak', '970', '123456&x=y', '<img src=x>', '123456/789']) {
    assert.equal(resolve('GLS', number), null);
  }
});
