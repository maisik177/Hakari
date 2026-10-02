const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');

test('Chrome manifest references packaged scripts, popup and supported PNG icons', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
  assert.equal(manifest.manifest_version, 3);
  assert.equal(manifest.browser_specific_settings, undefined);
  assert.deepEqual(manifest.permissions, ['storage']);
  assert.equal(manifest.content_scripts[0].all_frames, true);
  assert.deepEqual(manifest.content_scripts[0].matches, [
    'https://kartony24h.com/panel/orderd.php*',
    'https://kartony24h.com/panel/app/orderd.php*'
  ]);
  assert.deepEqual(manifest.host_permissions, ['http://127.0.0.1/*']);
  assert.equal(manifest.content_scripts[1].all_frames, true);
  assert.deepEqual(manifest.content_scripts[1].matches, ['https://kartony24h.com/panel/*']);
  for (const entry of [manifest.background.service_worker, manifest.action.default_popup, ...manifest.content_scripts.flatMap(s => [...s.js, ...s.css])]) {
    assert.ok(fs.existsSync(path.join(root, entry)), entry);
  }
  for (const icons of [manifest.icons, manifest.action.default_icon]) {
    for (const [size, file] of Object.entries(icons)) {
      const png = fs.readFileSync(path.join(root, file));
      assert.equal(png.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
      assert.equal(png.readUInt32BE(16), Number(size));
      assert.equal(png.readUInt32BE(20), Number(size));
    }
  }
});

function popup(storage) {
  const elements = Object.fromEntries(['#note-form', '#note', '#save', '#status'].map(id => [id, {
    value: '', disabled: true, textContent: '', listeners: {},
    addEventListener(name, callback) { this.listeners[name] = callback; }
  }]));
  vm.runInNewContext(fs.readFileSync(path.join(root, 'popup/popup.js'), 'utf8'), {
    document: { querySelector: id => elements[id] },
    chrome: { storage: { local: storage } },
    console: { error() {} }
  });
  return elements;
}

test('popup works with Chrome only: load, save and clear note', async () => {
  let saved = 'Poprzednia notatka';
  const elements = popup({ get: async () => ({ note: saved }), set: async data => { saved = data.note; } });
  await new Promise(setImmediate);
  assert.equal(elements['#note'].value, saved);
  assert.equal(elements['#save'].disabled, false);
  for (const value of ['Nowa notatka', '']) {
    elements['#note'].value = value;
    let prevented = false;
    await elements['#note-form'].listeners.submit({ preventDefault() { prevented = true; } });
    assert.ok(prevented);
    assert.equal(saved, value);
    assert.equal(elements['#status'].textContent, 'Notatka zapisana.');
    assert.equal(elements['#note'].disabled, false);
  }
});

test('popup reports failed reads and allows retry after failed writes', async () => {
  const readFailure = popup({ get: async () => { throw Error('read failed'); } });
  await new Promise(setImmediate);
  assert.match(readFailure['#status'].textContent, /Nie udało się wczytać/);
  assert.equal(readFailure['#save'].disabled, true);
  const writeFailure = popup({ get: async () => ({}), set: async () => { throw Error('write failed'); } });
  await new Promise(setImmediate);
  writeFailure['#note'].value = 'Nie zgub tej notatki';
  await writeFailure['#note-form'].listeners.submit({ preventDefault() {} });
  assert.match(writeFailure['#status'].textContent, /Nie udało się zapisać/);
  assert.equal(writeFailure['#note'].value, 'Nie zgub tej notatki');
  assert.equal(writeFailure['#save'].disabled, false);
});
