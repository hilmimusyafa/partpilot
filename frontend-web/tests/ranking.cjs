/* eslint-disable @typescript-eslint/no-require-imports -- Standalone Node test uses native TypeScript stripping. */
const assert = require('node:assert/strict');
const { compareOptionCosts } = require('../src/lib/partpilot.ts');
assert.equal(typeof compareOptionCosts, 'function');
const source = (kind, id, unrounded, optionId = id) => ({ source_kind: kind, source_id: id, option_id: optionId, economics: { future_relevant_option_total: '100000.00', future_relevant_option_total_unrounded: unrounded } });
const options = [
  source('warehouse', 'AAA', '100000.1000', 'option-a'),
  source('vendor', 'a', '1.000001E5', 'option-b'),
  source('vendor', 'vendor-a-more', '100000.00000000000000000002'),
  source('vendor', 'Z', '100000.1', 'option-z'),
  source('vendor', 'vendor-z-less', '100000.00000000000000000001'),
];
assert.deepEqual(options.sort(compareOptionCosts).map(option => option.source_id), ['vendor-z-less', 'vendor-a-more', 'Z', 'a', 'AAA']);
assert.equal(compareOptionCosts(source('vendor', 'same', '0E-30'), source('vendor', 'same', '-0.00')), 0);
assert.equal(compareOptionCosts(source('vendor', 'same', '-2.000001'), source('vendor', 'same', '-2')), -1);
assert.equal(compareOptionCosts(source('vendor', 'same', '9007199254740993'), source('vendor', 'same', '9007199254740992')), 1);
assert.equal(compareOptionCosts(source('vendor', 'same', '.0000002'), source('vendor', 'same', '1E-7')), 1);
assert.equal(compareOptionCosts(source('vendor', 'same', undefined), source('vendor', 'same', '100000.0000000000000001')), -1);
console.log('PASS: exact decimal ordering, scientific notation, signed zero, negative values, large values, canonical source kind/id ties, and rounded-value fallback.');
