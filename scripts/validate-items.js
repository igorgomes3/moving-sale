// Valida as paginas de item: navegacao a partir do catalogo, OG tags,
// galeria carregada, CTA e botao de compartilhar.
const puppeteer = require('puppeteer');
const BASE = process.argv[2] || 'http://127.0.0.1:8899';

(async () => {
  const b = await puppeteer.launch({headless:'new',args:['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage']});
  const p = await b.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type()==='error') errs.push(m.text()); });
  await p.setViewport({width:1440,height:1100});

  // 1. catalogo: todo card tem link para a pagina do item?
  await p.goto(BASE + '/index.html', {waitUntil:'domcontentloaded', timeout:45000});
  await new Promise(r=>setTimeout(r,2000));
  const links = await p.evaluate(() => [...document.querySelectorAll('.card')].map(c => ({
    item: c.querySelector('.name').textContent.slice(0,32),
    cardlink: (c.querySelector('a.cardlink')||{}).getAttribute ? c.querySelector('a.cardlink').getAttribute('href') : null,
    detalhes: (c.querySelector('a.cta.link')||{}).getAttribute ? c.querySelector('a.cta.link').getAttribute('href') : null,
  })));
  const semLink = links.filter(l => !l.cardlink || !l.detalhes);

  // 2. clica de verdade no primeiro card e confere a navegacao
  await Promise.all([
    p.waitForNavigation({waitUntil:'domcontentloaded', timeout:30000}),
    p.click('.card a.cardlink')
  ]);
  await new Promise(r=>setTimeout(r,1200));
  const item = await p.evaluate(() => {
    const img = document.querySelector('.gal img');
    return {
      url: location.pathname,
      h1: document.querySelector('.item-h1') ? document.querySelector('.item-h1').textContent.trim() : null,
      og_title: (document.querySelector('meta[property="og:title"]')||{}).content,
      og_desc: (document.querySelector('meta[property="og:description"]')||{}).content,
      og_img: (document.querySelector('meta[property="og:image"]')||{}).content,
      og_url: (document.querySelector('meta[property="og:url"]')||{}).content,
      tem_share: !!document.getElementById('btnShare'),
      share_url: document.getElementById('btnShare') ? document.getElementById('btnShare').dataset.url : null,
      tem_voltar: !!document.querySelector('a.back'),
      foto_ok: img ? (img.complete && img.naturalWidth>0) : null,
      foto_w: img ? img.naturalWidth : 0,
      cta: document.querySelector('.cta.big') ? document.querySelector('.cta.big').textContent : null
    };
  });
  await p.screenshot({path:'/tmp/item-page.png', fullPage:false});

  // 3. volta pelo link "voltar ao catalogo"
  await Promise.all([
    p.waitForNavigation({waitUntil:'domcontentloaded', timeout:30000}),
    p.click('a.back')
  ]);
  const voltou = await p.evaluate(() => document.querySelectorAll('.card').length);

  // 4. pagina com specs (MacBook 2010) — testa painel de especificacoes
  await p.goto(BASE + '/item/macbook-pro-2010-tela-quebrada.html', {waitUntil:'domcontentloaded'});
  await new Promise(r=>setTimeout(r,700));
  const specs = await p.evaluate(() => ({
    h1: document.querySelector('.item-h1').textContent.trim(),
    linhas_specs: document.querySelectorAll('.kv').length,
    panels: [...document.querySelectorAll('.panel h2')].map(h=>h.textContent),
    cta: document.querySelector('.cta.big') ? document.querySelector('.cta.big').textContent : null
  }));

  // 5. pagina de item a venda (deve ter CTA do WhatsApp)
  await p.goto(BASE + '/item/maquina-lavar-mini.html', {waitUntil:'domcontentloaded'});
  await new Promise(r=>setTimeout(r,700));
  const avenda = await p.evaluate(() => {
    const a = document.querySelector('a.cta.big');
    return {h1: document.querySelector('.item-h1').textContent.trim(),
            tem_wa: !!a, href: a ? a.getAttribute('href').slice(0,60) : null,
            preco: document.querySelector('.price-big .now').textContent};
  });

  // 6. mobile
  await p.setViewport({width:390,height:844,deviceScaleFactor:2});
  await p.goto(BASE + '/item/controles-xbox360.html', {waitUntil:'domcontentloaded'});
  await new Promise(r=>setTimeout(r,900));
  await p.screenshot({path:'/tmp/item-mobile.png', fullPage:true});

  console.log(JSON.stringify({
    catalogo_cards: links.length,
    cards_sem_link: semLink.length,
    detalhes_sample: links.slice(0,2).map(l=>l.detalhes),
    item_page: item,
    voltou_cards: voltou,
    specs_macbook2010: specs,
    item_a_venda: avenda,
    erros: errs
  }, null, 2));
  await b.close();
})();
