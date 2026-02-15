(function(){
  const API = '/api/v1/marketing/events';

  function uuid(){
    // Small, good-enough id for anonymous sessions.
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function getOrSet(key){
    const existing = localStorage.getItem(key);
    if (existing) return existing;
    const v = uuid();
    localStorage.setItem(key, v);
    return v;
  }

  const anonId = getOrSet('leadswarm_anon_id');
  const sessionId = getOrSet('leadswarm_session_id');

  function getUTM(){
    const u = new URL(window.location.href);
    const keys = ['utm_source','utm_medium','utm_campaign','utm_term','utm_content'];
    const utm = {};
    let any = false;
    for (const k of keys){
      const v = u.searchParams.get(k);
      if (v){ utm[k] = v; any = true; }
    }
    if (any) localStorage.setItem('leadswarm_utm', JSON.stringify(utm));
    try { return JSON.parse(localStorage.getItem('leadswarm_utm') || '{}'); } catch { return {}; }
  }

  const utm = getUTM();

  function post(event, props){
    const payload = {
      event,
      properties: props || {},
      anonymous_id: anonId,
      session_id: sessionId,
      path: window.location.pathname,
      referrer: document.referrer || null,
      utm
    };

    try {
      const body = JSON.stringify(payload);
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: 'application/json' });
        navigator.sendBeacon(API, blob);
        return;
      }

      fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true
      }).catch(() => {});
    } catch {
      // ignore
    }
  }

  function trackClick(el){
    const name = el.getAttribute('data-track');
    if (!name) return;
    post('marketing.cta_click', {
      name,
      text: (el.textContent || '').trim().slice(0, 80)
    });
  }

  document.addEventListener('click', (e) => {
    const el = e.target && e.target.closest ? e.target.closest('[data-track]') : null;
    if (!el) return;
    trackClick(el);

    // funnel hint for Start trial links
    const t = el.getAttribute('data-track') || '';
    if (t.includes('start_trial')) post('marketing.signup_started', { source: t });
  });

  // scroll depth
  (function(){
    const marks = [25, 50, 75, 100];
    const fired = new Set();

    function onScroll(){
      const doc = document.documentElement;
      const scrollTop = window.scrollY || doc.scrollTop || 0;
      const h = doc.scrollHeight - doc.clientHeight;
      if (h <= 0) return;
      const pct = Math.min(100, Math.round((scrollTop / h) * 100));
      for (const m of marks){
        if (pct >= m && !fired.has(m)){
          fired.add(m);
          post('marketing.scroll_depth', { percent: m });
        }
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  })();

  // sample reveal
  const btn = document.getElementById('viewSampleBtn');
  const panel = document.getElementById('samplePanel');
  const hint = document.getElementById('panelHint');
  if (btn && panel && hint){
    btn.addEventListener('click', () => {
      const open = !panel.hidden;
      panel.hidden = open;
      hint.hidden = !open;
      btn.textContent = open ? 'View a sample' : 'Hide the sample';
      post('marketing.sample_toggled', { open: !open });
    });
  }

  const y = document.getElementById('year');
  if (y) y.textContent = String(new Date().getFullYear());

  post('marketing.page_view', { title: document.title });
})();
