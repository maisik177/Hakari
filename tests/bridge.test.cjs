/* Autor: Maksymilian Dyla, firma Cart-pack */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const requestId = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee';
const message = {type: 'hakari.sendOrders', ids: ['123', '456'], requestId};
const sender = {id: 'extension', url: 'https://kartony24h.com/panel/orders-search.php?'};
function bridge(fetch, token = 'test') {
  const ctx = {URL, AbortController, setTimeout, clearTimeout, fetch,
    chrome: {runtime: {id: 'extension', onMessage: {addListener() {}}},
      storage: {local: {get: async () => ({bridgeToken: token})}}}};
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../background.js'), 'utf8'), ctx);
  return ctx.sendOrders;
}
test('bridge sends only IDs and shop to fixed local endpoint and checks receipt', async () => {
  const send = bridge(async (url, options) => {
    assert.equal(url, 'http://127.0.0.1:8765/orders');
    assert.equal(options.headers.Authorization, 'Bearer test');
    assert.deepEqual(JSON.parse(options.body), {request_id: requestId, shop: 'kartony24h.com', order_ids: ['123', '456']});
    return {ok: true, json: async () => ({request_id: requestId, accepted: 2})};
  });
  assert.equal((await send(message, sender)).accepted, 2);
});
test('bridge rejects wrong source, malformed IDs and missing key before network', async () => {
  const send = bridge(() => {throw Error('must not fetch');});
  await assert.rejects(send(message, {...sender, url: 'https://example.com'}), /źródło/);
  await assert.rejects(send(message, {...sender, url: 'https://kartony24h.com/sklep/'}), /źródło/);
  await assert.rejects(send({...message, ids: ['on']}, sender), /Nieprawidłowe/);
  await assert.rejects(bridge(() => {}, '')(message, sender), /klucz/);
});
test('bridge accepts order lists with status, operator and pagination variants', async () => {
  const send = bridge(async () => ({ok: true, json: async () => ({request_id: requestId, accepted: 2})}));
  for (const route of ['orders-list.php?status=wn', 'app/orders-list.php?status=packed',
    'orders-list.php?operator=maisik&status=wn#p2d1v22', 'app/orders-search.php?status=packed']) {
    assert.equal((await send(message, {...sender, url: `https://kartony24h.com/panel/${route}`})).ok, true);
  }
});
test('bridge does not report success on failed authentication or incomplete receipt', async () => {
  await assert.rejects(bridge(async () => ({status: 401}))(message, sender), /klucz/);
  await assert.rejects(bridge(async () => ({ok: true, json: async () => ({request_id: requestId, accepted: 1})}))(message, sender), /potwierdził/);
});
