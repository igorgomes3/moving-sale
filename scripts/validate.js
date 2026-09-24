// Valida o catalogo renderizado + gera screenshots
const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();

  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

  await page.setViewport({ width: 1440, height: 1000, deviceScaleFactor: 1 });
  const base = 'http://127.0.0.1:8899';

  // ---- catalogo
  await page.goto(base + '/index.html', { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 800));

  const info = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('.card')];
    const stats = [...document.querySelectorAll('.stat')].map(s =>
      s.querySelector('.k').textContent + ' = ' + s.querySelector('.v').textContent);
    const f = cards[0];
    return {
      title: document.title,
      total_cards: cards.length,
      stats,
      filters: [...document.querySelectorAll('.filters button')].map(b => b.textContent),
      sold_cards: document.querySelectorAll('.card.sold').length,
      ghost_ctas: document.querySelectorAll('.cta.ghost').length,
      body_bg: getComputedStyle(document.body).backgroundColor,
      first_card: f ? {
        name: f.querySelector('.name').textContent,
        category: f.querySelector('.cat').textContent,
        badge: f.querySelector('.badge').textContent,
        price: f.querySelector('.price').textContent.replace(/\s+/g, ' ').trim(),
        cta: (f.querySelector('.cta') || {}).textContent
      } : null,
      names: cards.map(c => c.querySelector('.name').textContent)
    };
  });

  await page.screenshot({ path: '/tmp/ms-catalogo-full.png', fullPage: true });
  await page.screenshot({ path: '/tmp/ms-catalogo-top.png' });

  // ---- filtro "a_venda"
  await page.click('.filters button[data-f="a_venda"]');
  await new Promise(r => setTimeout(r, 400));
  const aVenda = await page.evaluate(() => ({
    count: document.querySelectorAll('.card').length,
    names: [...document.querySelectorAll('.card .name')].map(n => n.textContent)
  }));
  await page.screenshot({ path: '/tmp/ms-catalogo-avenda.png', fullPage: true });

  // ---- filtro "vendido"
  await page.click('.filters button[data-f="vendido"]');
  await new Promise(r => setTimeout(r, 400));
  const vendidos = await page.evaluate(() => document.querySelectorAll('.card').length);

  // ---- mobile
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2 });
  await page.click('.filters button[data-f="todos"]');
  await new Promise(r => setTimeout(r, 500));
  await page.screenshot({ path: '/tmp/ms-mobile.png', fullPage: true });

  // ---- admin
  await page.setViewport({ width: 1440, height: 1000, deviceScaleFactor: 1 });
  await page.goto(base + '/admin.html', { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 1200));
  const admin = await page.evaluate(() => ({
    items_rendered: document.querySelectorAll('.item').length,
    stats: document.getElementById('stats').textContent.replace(/\s+/g, ' ').trim(),
    msg: document.getElementById('msg').textContent.trim(),
    msg_class: document.getElementById('msg').className,
    auth_visible: getComputedStyle(document.getElementById('authPanel')).display !== 'none',
    fields_per_item: document.querySelectorAll('.item:first-child [data-k]').length
  }));
  await page.screenshot({ path: '/tmp/ms-admin.png', fullPage: true });

  console.log(JSON.stringify({ catalogo: info, filtro_a_venda: aVenda, filtro_vendido: vendidos, admin, errors }, null, 2));
  await browser.close();
})();
