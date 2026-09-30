const puppeteer = require('puppeteer');
const BASE = process.argv[2] || 'http://127.0.0.1:8899';
(async () => {
  const b = await puppeteer.launch({headless:'new',args:['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage']});
  const p = await b.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  p.on('console',m=>{if(m.type()==='error')errs.push(m.text());});
  await p.setViewport({width:1440,height:1200});
  await p.goto(BASE + '/dashboard.html', {waitUntil:'networkidle0', timeout:45000});
  await new Promise(r=>setTimeout(r,1200));

  const d = await p.evaluate(() => {
    const kpis = [...document.querySelectorAll('.kpi')].map(k => ({
      k: k.querySelector('.k').textContent,
      v: k.querySelector('.v').textContent.trim(),
      n: k.querySelector('.n').textContent
    }));
    const pl = [...document.querySelectorAll('.pl .row')].map(r => ({
      lbl: r.querySelector('.lbl').textContent,
      amt: r.querySelector('.amt').textContent.trim()
    }));
    const rows = [...document.querySelectorAll('tbody tr')].map(tr => ({
      item: tr.querySelector('.item').textContent,
      plat: tr.querySelector('.plat').textContent,
      bruto: tr.children[2].textContent.trim(),
      taxa: tr.children[3].textContent.trim(),
      liq: tr.children[4].textContent.trim(),
      pct: tr.querySelector('.pct').textContent,
      pill: tr.querySelector('.pill').textContent,
      pillClass: tr.querySelector('.pill').className
    }));
    const foot = [...document.querySelectorAll('tfoot td')].map(td => td.textContent.trim()).filter(Boolean);
    const pend = [...document.querySelectorAll('.todo li')].map(li => li.querySelector('.txt').textContent);
    const sell = [...document.querySelectorAll('.selllist li')].map(li => li.querySelector('.nm').textContent);
    return {
      title: document.title, kpis, pl, rows, foot, pend, sell,
      robots: (document.querySelector('meta[name=robots]')||{}).content,
      tabular: getComputedStyle(document.querySelector('td.num')).fontVariantNumeric,
      alinhamento: getComputedStyle(document.querySelector('td.num')).textAlign,
      tem_link_publico: !!document.querySelector('a[href="index.html"]')
    };
  });
  await p.screenshot({path:'/tmp/dash-live.png', fullPage:true});
  await p.setViewport({width:390,height:844,deviceScaleFactor:2});
  await p.reload({waitUntil:'networkidle0'});
  await new Promise(r=>setTimeout(r,800));
  await p.screenshot({path:'/tmp/dash-mobile.png', fullPage:true});

  // o publico nao pode linkar pro dashboard
  await p.setViewport({width:1440,height:1000});
  await p.goto(BASE + '/index.html',{waitUntil:'networkidle0'});
  const leak = await p.evaluate(() => ({
    links_dash: document.querySelectorAll('a[href*="dashboard"]').length,
    textos_financeiros: /líquido|taxa|disputa|em disputa|a liberar/i.test(document.body.innerText)
  }));

  console.log(JSON.stringify({dashboard:d, publico_limpo:leak, erros:errs}, null, 2));
  await b.close();
})();
