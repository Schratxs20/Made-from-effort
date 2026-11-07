import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const html = readFileSync(new URL('../contact.html', import.meta.url), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(source => source.includes('function validateStep'));

function setup(query = '') {
  const elements = new Map();
  for (const [, id] of html.matchAll(/\bid="([^"]+)"/g)) {
    elements.set(id, {
      value: '', style: {}, files: [],
      classList: { add() {}, remove() {}, toggle() {} },
      addEventListener() {},
      querySelector() { return { classList: { add() {}, remove() {} }, checked: false }; },
    });
  }
  const requests = [];
  const context = { URLSearchParams, window: { location: { search: query } },
    FormData: class { constructor() { this.fields = new Map(); } append(k, v) { this.fields.set(k, v); } },
    fetch: async (url, options) => { requests.push({ url, fields: options.body.fields }); return { ok: true }; },
    document: { getElementById: id => elements.get(id), querySelectorAll: () => [],
      querySelector: () => ({ disabled: false, querySelector: () => ({ textContent: '' }) }) } };
  runInNewContext(script, context);
  return { context, elements, requests, valid: n => context.validateStep(n) };
}

function contactDetails(site) {
  for (const [id, value] of Object.entries({ firstName: 'Test', lastName: 'Visitor', email: 'visitor@example.com' })) {
    site.elements.get(id).value = value;
  }
}

test('a visitor can advance without a phone but still needs valid contact details', () => {
  const site = setup();
  contactDetails(site);
  assert.equal(site.valid(1), true);
  site.elements.get('phone').value = '12';
  assert.equal(site.valid(1), false);
  site.elements.get('phone').value = '';
  site.elements.get('email').value = 'invalid';
  assert.equal(site.valid(1), false);
});

test('an audit inquiry can proceed with no construction budget or fixed timeline', () => {
  const site = setup('?project=country-club&source=fitness-audit');
  assert.equal(site.elements.get('budget').value, 'audit-consultation');
  site.elements.get('timeline').value = 'not-sure';
  assert.equal(site.valid(2), true);
});

test('referral introductions prefill their purpose but still require a project type', () => {
  const site = setup('?source=referral-partners');
  assert.equal(site.elements.get('budget').value, 'introduction');
  site.elements.get('timeline').value = 'not-sure';
  assert.equal(site.valid(2), false);
  site.context.selectTile('projectType', 'residence', site.elements.get('tile-residence'));
  assert.equal(site.valid(2), true);
});

test('ordinary inquiries retain budget selection and support an undecided budget', () => {
  const site = setup('?project=hospitality&source=hospitality-service-page');
  assert.equal(site.elements.get('budget').value, '');
  site.elements.get('timeline').value = 'not-sure';
  assert.equal(site.valid(2), false);
  site.elements.get('budget').value = 'not-defined';
  assert.equal(site.valid(2), true);
});

// Exercise the real submission handler with a local fetch stub; no inquiry is sent.
test('audit submission preserves the new options and an empty optional phone', async () => {
  const site = setup('?project=country-club&source=fitness-audit');
  contactDetails(site);
  site.elements.get('timeline').value = 'not-sure';
  site.elements.get('vision').value = 'Review an existing club fitness space.';
  site.elements.get('clubName').value = 'Example Club';
  site.elements.get('clubRole').value = 'Architect or Designer';
  await site.context.submitForm();
  assert.equal(site.requests.length, 1);
  assert.equal(site.requests[0].fields.get('budget'), 'audit-consultation');
  assert.equal(site.requests[0].fields.get('timeline'), 'not-sure');
  assert.equal(site.requests[0].fields.get('phone'), '');
  assert.equal(site.requests[0].fields.get('projectType'), 'country-club');
  assert.equal(site.requests[0].fields.get('source'), 'fitness-audit');
});
