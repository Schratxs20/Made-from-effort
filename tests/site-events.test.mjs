import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const script = readFileSync(new URL('../site-events.js', import.meta.url), 'utf8');

function setup() {
  let onClick;
  const window = { location: new URL('https://www.madefromeffort.com/journal/example') };
  const document = {
    referrer: '',
    head: { appendChild() {} },
    createElement() { return {}; },
    addEventListener(name, callback) { if (name === 'click') onClick = callback; },
  };
  const localStorage = { getItem() { return null; }, setItem() {} };
  runInNewContext(script, { window, document, localStorage, URL, URLSearchParams, Date });
  return {
    window,
    click(href) {
      const link = {
        href: new URL(href, window.location.href).href,
        textContent: 'Start a Project',
        getAttribute() { return href; },
      };
      onClick({ target: { closest() { return link; } } });
    },
    events() { return Array.from(window.dataLayer, item => item?.event).filter(Boolean); },
  };
}

test('only successful design inquiries count as qualified conversions', () => {
  for (const lead_type of ['home_gym_guide', 'training_consultation', 'estimator']) {
    const site = setup();
    site.window.peTrack('lead_submit', { lead_type });
    assert.deepEqual(site.events(), ['lead_submit']);
  }
  for (const lead_type of ['design_inquiry', 'homepage_design_inquiry']) {
    const site = setup();
    site.window.peTrack('lead_submit', { lead_type });
    assert.deepEqual(site.events(), ['lead_submit', 'close_convert_lead']);
  }
});

test('contact CTA tracking works for clean and legacy URLs', () => {
  for (const href of ['/contact?project=residence', '/contact.html?project=residence']) {
    const site = setup();
    site.click(href);
    assert.ok(site.events().includes('inquiry_cta_click'), href);
  }
});

test('residential and Journal entry pages load the measurement script', () => {
  for (const path of ['residential-gym-design.html', 'journal/index.html', 'journal/a-gym-isn-t-a-pile-of-good-equipment.html']) {
    const html = readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
    assert.match(html, /site-events\.js\?v=2/, path);
  }
});
