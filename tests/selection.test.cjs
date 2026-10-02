const {test} = require('node:test');
const assert = require('node:assert/strict');
const {read} = require('../content/selection.js');
test('reads only selected order checkboxes, preserves string IDs and removes duplicates', () => {
  const doc = {querySelectorAll(selector) {
    assert.equal(selector, '#dynamicdata input[type="checkbox"][name="idt[]"]:checked');
    return ['1046', '1045', '1046', '99999999999999999999'].map(value => ({value}));
  }};
  assert.deepEqual(read(doc), ['1046', '1045', '99999999999999999999']);
  assert.deepEqual(read({querySelectorAll: () => []}), []);
  assert.throws(() => read({querySelectorAll: () => [{value: 'on'}]}));
});
