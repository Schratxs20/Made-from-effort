(function () {
  const measurementId = 'G-MVF11QSSPG';
  const params = new URLSearchParams(window.location.search);
  const firstTouchKey = 'pe_first_touch';
  const campaignKeys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];

  function readStored() {
    try { return JSON.parse(localStorage.getItem(firstTouchKey) || 'null'); }
    catch { return null; }
  }

  function currentTouch() {
    const campaign = {};
    campaignKeys.forEach(key => { if (params.get(key)) campaign[key] = params.get(key); });
    return {
      ...campaign,
      source: params.get('source') || campaign.utm_source || (document.referrer ? 'referral' : 'direct'),
      landing_page: window.location.pathname,
      referrer: document.referrer || '',
      captured_at: new Date().toISOString()
    };
  }

  let firstTouch = readStored();
  if (!firstTouch) {
    firstTouch = currentTouch();
    try { localStorage.setItem(firstTouchKey, JSON.stringify(firstTouch)); } catch {}
  }

  window.dataLayer = window.dataLayer || [];
  if (/^G-[A-Z0-9]+$/i.test(measurementId)) {
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', measurementId, { anonymize_ip: true });
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
    document.head.appendChild(script);
  }
  window.peAttribution = function () {
    return {
      first_touch_source: firstTouch.source || 'direct',
      first_touch_landing_page: firstTouch.landing_page || '',
      first_touch_referrer: firstTouch.referrer || '',
      latest_source: params.get('source') || params.get('utm_source') || firstTouch.source || 'direct',
      latest_page: window.location.pathname,
      utm_campaign: params.get('utm_campaign') || firstTouch.utm_campaign || '',
      utm_medium: params.get('utm_medium') || firstTouch.utm_medium || '',
      utm_content: params.get('utm_content') || firstTouch.utm_content || ''
    };
  };

  window.peAppendAttribution = function (formData) {
    Object.entries(window.peAttribution()).forEach(([key, value]) => formData.append(key, value));
    formData.append('submission_page', window.location.href);
    return formData;
  };

  window.peTrack = function (eventName, details) {
    const payload = { event: eventName, ...window.peAttribution(), ...(details || {}) };
    window.dataLayer.push(payload);
    if (typeof window.gtag === 'function') window.gtag('event', eventName, payload);
    if (eventName === 'lead_submit') {
      const conversionPayload = { ...payload, event: 'close_convert_lead' };
      window.dataLayer.push(conversionPayload);
      if (typeof window.gtag === 'function') window.gtag('event', 'close_convert_lead', conversionPayload);
    }
  };

  document.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link) return;
    const href = link.getAttribute('href') || '';
    if (href.startsWith('mailto:')) {
      window.peTrack('charter_email_click', { link_text: link.textContent.trim(), destination: 'scott' });
    } else if (href.includes('contact.html')) {
      const destination = new URL(link.href, window.location.href);
      window.peTrack('inquiry_cta_click', {
        link_text: link.textContent.trim(),
        project_type: destination.searchParams.get('project') || 'unspecified',
        inquiry_source: destination.searchParams.get('source') || window.location.pathname
      });
    } else if (href.includes('estimator.html')) {
      window.peTrack('estimator_start', { link_text: link.textContent.trim() });
    }
  });
})();
