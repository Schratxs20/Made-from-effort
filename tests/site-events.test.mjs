import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const script = readFileSync(new URL('../site-events.js', import.meta.url), 'utf8');

function setup(path = '/journal/example') {
  let onClick;
  const window = { location: new URL(path, 'https://www.madefromeffort.com') };
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

test('Journal article clicks to internal design services have their own event', () => {
  for (const href of [
    '/residential-gym-design', '/yacht-gym-design.html',
    '/commercial-gym-design', '/country-club-fitness-design',
    '/hospitality-gym-design?source=journal',
  ]) {
    const site = setup('/journal/example.html');
    site.click(href);
    assert.deepEqual(site.events(), ['journal_service_click'], href);
    const payload = site.window.dataLayer.find(item => item?.event === 'journal_service_click');
    assert.equal(payload.journal_article, '/journal/example');
    assert.equal(payload.service_page, new URL(href, site.window.location.href).pathname.replace(/\.html$/, ''));
  }
});

test('Journal service clicks exclude listing, email, off-site, and non-service links', () => {
  for (const [page, href] of [
    ['/journal/', '/residential-gym-design'],
    ['/journal/index.html', '/residential-gym-design'],
    ['/journal/example-email.html', '/residential-gym-design'],
    ['/residential-gym-design', '/yacht-gym-design'],
    ['/journal/example', 'https://other.example/residential-gym-design'],
    ['/journal/example', '/training'],
  ]) {
    const site = setup(page);
    site.click(href);
    assert.deepEqual(site.events(), [], `${page} → ${href}`);
  }
  const site = setup();
  site.click('/contact?project=residence');
  assert.deepEqual(site.events(), ['inquiry_cta_click']);
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
    'referral-partners.html', 'privacy.html',
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
    assert.match(html, new RegExp(`<div class="hero-content">[\\s\\S]*?<a class="hero-cta" href="/contact\\?project=${project}&amp;source=`), path);
  }
});

test('every project has a persistent mobile inquiry route with a recognized project type', () => {
  const pages = [
    'project-caumsett.html', 'project-dix-hills.html', 'project-glen-cove.html',
    'project-jericho.html', 'project-jupiter-island.html',
    'project-oyster-bay-cove.html', 'project-sands-point.html', 'project-yacht.html',
  ];
  const css = readFileSync(new URL('../project-mobile-cta.css', import.meta.url), 'utf8');
  assert.match(css, /position: fixed/);
  assert.match(css, /env\(safe-area-inset-bottom\)/);
  for (const path of pages) {
    const html = readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
    assert.match(html, /href="\/project-mobile-cta\.css"/, path);
    assert.match(html, /class="mobile-project-cta" href="\/contact\?project=(residence|marine)&amp;source=[^"]+"/, path);
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
