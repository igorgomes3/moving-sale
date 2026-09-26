// Valida o site PUBLICADO (nao o local)
const puppeteer = require('puppeteer');
(async () => {
  const b = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage'] });
  const p = await b.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });

  const URL = 'https://moving-sale-c8b.pages.dev';
  await p.setViewport({ width: 1440, height: 1000 });
  await p.goto(URL + '/index.html', { waitUntil: 'networkidle0', timeout: 45000 });
  await new Promise(r => setTimeout(r, 1200));

  const cat = await p.evaluate(() => ({
    title: document.title,
    cards: document.querySelectorAll('.card').length,
    sold: document.querySelectorAll('.card.sold').length,
    wa_links: [...document.querySelectorAll('a.cta')].filter(a => a.href.startsWith('https://wa.me/')).length,
    stats: [...document.querySelectorAll('.stat')].map(s => s.querySelector('.k').textContent + '=' + s.querySelector('.v').textContent),
    nofoto_color: (() => { const el = document.querySelector('.nofoto'); return el ? getComputedStyle(el).color : null; })(),
    nofoto_bg: (() => { const el = document.querySelector('.ph'); return el ? getComputedStyle(el).backgroundImage.slice(0,40) : null; })()
  }));
  await p.screenshot({ path: '/tmp/live-catalogo.png', fullPage: false });
  await p.screenshot({ path: '/tmp/live-catalogo-full.png', fullPage: true });

  // admin publicado
  await p.goto(URL + '/admin.html', { waitUntil: 'networkidle0', timeout: 45000 });
  await new Promise(r => setTimeout(r, 1500));
  const adm = await p.evaluate(() => ({
    items: document.querySelectorAll('.item').length,
    msg: document.getElementById('msg').textContent.trim(),
    msg_class: document.getElementById('msg').className,
    fields: document.querySelectorAll('.item:first-child [data-k]').length
  }));
  await p.screenshot({ path: '/tmp/live-admin.png', fullPage: false });

  console.log(JSON.stringify({ catalogo: cat, admin: adm, erros: errs }, null, 2));
  await b.close();
})();
