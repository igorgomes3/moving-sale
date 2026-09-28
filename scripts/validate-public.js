// Valida a camada PUBLICA: nada de dado financeiro pode vazar.
const puppeteer = require('puppeteer');
const BASE = process.argv[2] || 'http://127.0.0.1:8899';

// padroes que NAO podem existir em pagina publica
const PROIBIDO = [
  /R\$ ?2\.032/, /l[íi]quido/i, /arrecadad/i, /taxa/i, /Enjoei/i,
  /em disputa/i, /a liberar/i, /J[áa] recebido/i, /pre[çc]o de amigo/i,
  /risco de revers/i,
];

(async () => {
  const b = await puppeteer.launch({headless:'new',args:['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage']});
  const p = await b.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  p.on('console',m=>{if(m.type()==='error')errs.push(m.text());});
  await p.setViewport({width:1440,height:1100});

  await p.goto(BASE + '/index.html', {waitUntil:'networkidle0', timeout:45000});
  await new Promise(r=>setTimeout(r,1500));
  const cat = await p.evaluate(() => {
    const t = document.body.innerText;
    return {
      texto: t.slice(0, 400),
      cards: document.querySelectorAll('.card').length,
      vendidos: document.querySelectorAll('.card.is-sold').length,
      vendidos_com_preco: [...document.querySelectorAll('.card.is-sold .price')].length,
      vendidos_com_cta: [...document.querySelectorAll('.card.is-sold .cta')].length,
      com_cta_ver_detalhes: [...document.querySelectorAll('.card .cta')].map(c=>c.textContent),
      tem_busca: !!document.getElementById('q'),
      tem_categoria_chips: document.querySelectorAll('.catbar button').length,
      tem_sidebar: !!document.querySelector('aside'),
      tem_sort: !!document.getElementById('sort'),
      valores: (t.match(/R\$ [\d.,]+/g)||[]),
    };
  });

  // navega para um item e checa
  await p.goto(BASE + '/item/cafeteira-tres-coracoes.html', {waitUntil:'networkidle0'});
  await new Promise(r=>setTimeout(r,1200));
  const detalhe = await p.evaluate(() => {
    const t = document.body.innerText;
    return {
      texto: t.slice(0, 500),
      h1: (document.querySelector('.buy h1')||{}).textContent,
      preco: (document.querySelector('.pricebig .now')||{}).textContent || null,
      vendeu_preco: !!document.querySelector('.pricebig .undef'),
      cta: (document.querySelector('.btn-wa, .btn-off')||{}).textContent,
      tem_galeria: !!document.querySelector('.gal .main'),
      tem_thumbs: document.querySelectorAll('.thumbs img').length,
      tem_specs: document.querySelectorAll('.kv .row').length,
      tem_breadcrumb: !!document.querySelector('.crumb'),
      valores: (t.match(/R\$ [\d.,]+/g)||[]),
      plataforma_exposta: /enjoei|mercado ?livre|olx/i.test(t),
      taxa_exposta: /taxa|comiss[ãa]o/i.test(t),
    };
  });

  // item vendido: nao pode ter preco nem CTA de contato
  await p.goto(BASE + '/item/macbook-pro-16gb.html', {waitUntil:'networkidle0'});
  await new Promise(r=>setTimeout(r,1000));
  const vendido = await p.evaluate(() => {
    const t = document.body.innerText;
    return {
      valores: (t.match(/R\$ [\d.,]+/g)||[]),
      cta: (document.querySelector('.btn-wa, .btn-off')||{}).textContent,
      marcador: (document.querySelector('.pricebig .undef')||{}).textContent,
      tem_wa: !!document.querySelector('.btn-wa'),
      desc_publica: !!document.querySelector('.sec p')
    };
  });

  await p.screenshot({path:'/tmp/pub-index.png', fullPage:true});
  await p.goto(BASE + '/index.html', {waitUntil:'networkidle0'});
  await new Promise(r=>setTimeout(r,900));
  await p.screenshot({path:'/tmp/pub-index-top.png'});
  await p.goto(BASE + '/item/cafeteira-tres-coracoes.html', {waitUntil:'networkidle0'});
  await new Promise(r=>setTimeout(r,900));
  await p.screenshot({path:'/tmp/pub-item.png', fullPage:true});

  // varredura de vazamento em TODAS as paginas publicas
  const fs = require('fs');
  const path = require('path');
  const root = process.cwd() + '/site';
  const leaks = [];
  const files = ['index.html', ...fs.readdirSync(root + '/item').map(f => 'item/' + f)];
  for (const f of files) {
    const txt = fs.readFileSync(path.join(root, f), 'utf8');
    for (const rx of PROIBIDO) {
      if (rx.test(txt)) leaks.push(f + ' -> ' + rx);
    }
  }

  console.log(JSON.stringify({catalogo:cat, item_a_venda:detalhe, item_vendido:vendido, vazamentos:leaks, erros:errs}, null, 2));
  await b.close();
})();
