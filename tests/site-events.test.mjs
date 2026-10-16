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

test('About, Training, and project entry pages capture first touch', () => {
  for (const path of [
    'about.html', 'training.html', 'project-jupiter-island.html',
    'project-yacht.html', 'project-jericho.html', 'project-caumsett.html',
    'project-dix-hills.html', 'project-glen-cove.html',
    'project-oyster-bay-cove.html', 'project-sands-point.html',
  ]) {
    const html = readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
    assert.equal((html.match(/site-events\.js\?v=2/g) || []).length, 1, path);
  }
});

test('Training inquiry includes attribution and tracks only a successful submission', () => {
  const html = readFileSync(new URL('../training.html', import.meta.url), 'utf8');
  assert.match(html, /body: window\.peAppendAttribution \? window\.peAppendAttribution\(new FormData\(form\)\)/);
  assert.match(html, /if \(res\.ok\) \{\s*if \(window\.peTrack\) window\.peTrack\('lead_submit', \{ lead_type: 'training_consultation'/);
  const site = setup();
  site.window.peTrack('lead_submit', { lead_type: 'training_consultation' });
  assert.deepEqual(site.events(), ['lead_submit']);
});

test('featured case studies expose an inquiry link in the hero', () => {
  for (const [path, project] of [
    ['project-jupiter-island.html', 'residence'],
    ['project-yacht.html', 'marine'],
  ]) {
    const html = readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
    assert.match(html, new RegExp(`<div class="hero-content">[\\s\\S]*?<a class="hero-cta" href="contact\\.html\\?project=${project}&amp;source=`), path);
  }
});

test('mobile entry CTAs reach forms with visible required contact fields', () => {
  const home = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const training = readFileSync(new URL('../training.html', import.meta.url), 'utf8');
  assert.match(home, /id="inquiry-form"[^>]*scroll-margin-top: 80px/);
  assert.match(home, /@media\(max-width:860px\)\{[\s\S]*?#inquiry-form\.reveal\{transform:none\}/);
  assert.match(training, /href="#training-form">Request a Consultation/);
  assert.match(training, /#training-form \{ scroll-margin-top: 80px; \}/);
  assert.match(training, /id="t-first"[^>]*required/);
  assert.match(training, /id="t-email"[^>]*required/);
});
