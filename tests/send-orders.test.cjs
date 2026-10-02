/* Autor: Maksymilian Dyla, firma Cart-pack */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../content/send-orders.js'), 'utf8');

function page(pathname, initiallyPresent = true) {
  let update;
  let orderList = initiallyPresent;
  let present = initiallyPresent;
  let selected = ['123'];
  let mounts = 0;
  const elements = [];
  const sent = [];
  const list = {
    querySelector: () => orderList ? {} : null,
    before(bar) { bar.isConnected = true; bar.nextElementSibling = list; mounts++; }
  };
  const document = {
    body: {},
    querySelector(selector) {
      if (selector === '#dynamicdata') return present ? list : null;
      if (selector === '#counterOrders') return orderList ? {} : null;
      return null;
    },
    createElement(tag) {
      const el = {tag, isConnected: false, handlers: {}, children: [],
        append(...items) { this.children.push(...items); },
        setAttribute() {}, remove() { this.isConnected = false; },
        addEventListener(name, handler) { this.handlers[name] = handler; }};
      elements.push(el);
      return el;
    }
  };
  vm.runInNewContext(source, {document, location: {origin: 'https://kartony24h.com', pathname},
    MutationObserver: class {constructor(fn) {update = fn;} observe() {}},
    crypto: {randomUUID: () => 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'},
    HakariSelection: {read: () => selected},
    chrome: {runtime: {sendMessage: async message => {sent.push(message); return {ok: true, accepted: message.ids.length};}}}
  });
  return {elements, sent, update: () => update(), get mounts() {return mounts;},
    setPresent(value) {present = value; orderList = value;},
    unrelated() {present = true; orderList = false;}, select(ids) {selected = ids;}};
}

test('mounts exactly once in search and status-list frames, remounts after table refresh', () => {
  for (const route of ['/panel/orders-search.php', '/panel/orders-list.php', '/panel/app/orders-list.php']) {
    const p = page(route);
    assert.equal(p.mounts, 1);
    p.update();
    assert.equal(p.mounts, 1);
    p.elements[0].isConnected = false;
    p.update();
    assert.equal(p.mounts, 2);
  }
});
test('waits for async order table, removes control on unrelated views and returns on navigation', () => {
  const p = page('/panel/app/orders-list.php', false);
  assert.equal(p.mounts, 0);
  p.setPresent(true); p.update();
  assert.equal(p.mounts, 1);
  p.unrelated(); p.update();
  assert.equal(p.elements[0].isConnected, false);
  p.setPresent(true); p.update();
  assert.equal(p.mounts, 2);
});
test('button reads current selection on click and does not send empty selections', async () => {
  const p = page('/panel/orders-list.php');
  p.select([]);
  await p.elements[1].handlers.click();
  assert.equal(p.sent.length, 0);
  p.select(['456', '789']);
  await p.elements[1].handlers.click();
  assert.deepEqual(p.sent[0].ids, ['456', '789']);
  assert.match(p.elements[2].textContent, /Zapisano 2 ID/);
});
