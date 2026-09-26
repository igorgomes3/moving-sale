# HANDOFF — Projeto "Moving Sale" (venda do apê antes do Vietnã)

**Tópico Telegram:** thread `17222` (nome inicial "Sell Out" — recomendo renomear, ver §6)
**Criado em:** 2026-09-11
**Responsável:** Hermes (COO) — implementa direto

---

## 0. ESTADO ATUAL (2026-09-25) — LEIA PRIMEIRO

### Está no ar

- **Site:** https://moving-sale-c8b.pages.dev
- **Admin:** https://moving-sale-c8b.pages.dev/admin.html
- **Repo:** https://github.com/igorgomes3/moving-sale (público, branch `main`)

Deploy verificado no domínio público com Chrome real: 11 cards, 7 vendidos,
4 links `wa.me/5511949139458` (um por item à venda), **zero erros de console**.

### Decisões travadas

| Decisão | Valor | Rationale |
|---|---|---|
| Escopo | **Catálogo estático** | Sem carrinho/checkout/login. Liquidação one-time, não negócio. |
| Fonte de verdade | **Git (`data/inventory.json`)** | Versionado, diffável, rollback por commit, zero dependência Google. |
| Admin | `/admin.html` grava `inventory.json` via GitHub API | Auth por PAT no `localStorage`. Sem Google, sem planilha. |
| Hospedagem | **Cloudflare Pages**, projeto `moving-sale` | Free tier, HTTPS, CDN. |
| Contato | **WhatsApp `5511949139458`** | Autorizado por voz em 25/09. Link por item com mensagem pré-preenchida. |

### Comandos

```bash
# gerar o site a partir do inventário
cd /root/projects/moving-sale && python3 scripts/build.py

# validar renderização local (precisa de um http.server na 8899)
NODE_PATH=$(npm root -g) node scripts/validate.js

# validar o site PUBLICADO (não precisa de server local)
NODE_PATH=$(npm root -g) node scripts/validate-live.js

# deploy manual
export CLOUDFLARE_API_TOKEN=$(cat /root/.cf-token)
npx --yes wrangler@latest pages deploy site --project-name=moving-sale --branch=main

# transcrever áudio que o Hermes não transcreveu
python3 scripts/stt.py /root/.hermes/cache/audio/audio_<hash>.ogg pt
```

### Estrutura

```
/root/projects/moving-sale/
├── admin.html                    edita inventory.json via GitHub API
├── data/
│   ├── inventory.json            FONTE DE VERDADE (11 itens)
│   └── fees.json                 tabelas oficiais Enjoei
├── scripts/
│   ├── build.py                  inventário -> site/ (HTML auto-contido)
│   ├── calc.py                   calculadora de líquido/taxa
│   ├── validate.js               valida no Chrome + screenshots
│   ├── validate-live.js          valida o site publicado
│   └── stt.py                    transcrição via 9Router
├── .github/workflows/deploy.yml  CI: build + valida + deploy
└── site/                         ARTEFATO DE BUILD (gitignored)
```

### Arquitetura final

```
data/inventory.json  (fonte de verdade, versionada)
        │
        ├─► scripts/build.py ─► site/index.html   (auto-contido, zero deps)
        │                    ─► site/data/*.json  (admin lê same-origin)
        │                    ─► site/copys.md     (rascunhos de anúncio)
        │                    ─► site/resumo.md    (relatório financeiro)
        │
        └─► /admin.html ─► GitHub API (PUT contents) ─► commit
                                    │
                                    └─► GitHub Actions ─► build + valida ─► wrangler ─► Pages
```

**Fluxo do usuário:** abre `/admin.html` → edita campos → "Salvar tudo no
GitHub" → commit → CI rebuilda → site atualizado em ~1-2 min. Sem planilha,
sem Google, sem intervenção do Hermes.

### Números (25/09/2026)

**Vendido bruto: R$ 1.738,00 · Taxas: −R$ 262,92 (15,1%) · Líquido: R$ 1.475,08**

| Item | Plataforma | Bruto | Taxa | Líquido | Situação |
|---|---|---|---|---|---|
| Secadora centrífuga | Marketplace | R$ 300,00 | 0 | R$ 300,00 | recebido |
| Mesinha de centro | Marketplace | R$ 150,00 | 0 | R$ 150,00 | recebido |
| MacBook Pro 16GB | Enjoei | R$ 750,00 | R$ 142,36 | R$ 607,64 | a liberar |
| Mesa + cadeira | Enjoei | R$ 280,00 | R$ 55,10 | R$ 224,90 | **DISPUTA** |
| Cafeteira Três Corações | Enjoei | R$ 158,00 | R$ 40,46 | R$ 117,54 | a liberar |
| Casaco creme | Enjoei | R$ 50,00 | R$ 12,50 | R$ 37,50 | a liberar |
| 3 livros | Enjoei | R$ 50,00 | R$ 12,50 | R$ 37,50 | a liberar |

- Já recebido: **R$ 850,00** · A liberar: **R$ 800,18** · Em disputa (risco): **R$ 224,90**
- Potencial à venda: **R$ 450,00** · **Projeção total: R$ 2.325,08**

### Pendências (25/09)

1. ~~**Secrets do CI não configurados.**~~ **RESOLVIDO em 26/09.** `CLOUDFLARE_API_TOKEN`
   e `CLOUDFLARE_ACCOUNT_ID` configurados via `gh secret set`. Workflow
   `Build e deploy do catalogo` rodou verde (run 36240651088, deploy
   `990c8ae8` publicado em produção). Salvar pelo admin agora rebuilda sozinho.
2. **Fotos.** Todos os itens mostram "SEM FOTO". Colocar URLs em `photos[]`
   pelo admin.
3. **Inventário incompleto.** Igor disse "há outras coisas, falo na sequência".
4. **Custos de deslocamento** dos itens de Marketplace ainda zerados —
   corroem o líquido sem aparecer. Campo `delivery_cost` existe no admin.
5. **Pergunta aberta:** o Enjoei já travou o dinheiro da mesa em disputa, ou
   o valor foi recebido e ela abriu disputa depois? Muda o risco de
   R$224,90 para zero.
6. **Canal de origem do MacBook 2010** (vendido R$400): Marketplace, OLX ou
   grupo do condomínio? Só para medir qual canal converte melhor.

### MacBook 2010 (tela inoperante) — recomendação

Pesquisa de mercado (25/09): ML pede R$2.000 num Mid 2010 funcionando e
R$769,99 num que não liga — **preços de anúncio, não de venda efetivada**.
Referência internacional: ~US$100 para unidade funcionando.

Máquina de 16 anos, Core 2 Duo, tela morta → faixa justa **R$200-400**.
A oferta de R$400 recebida está no topo da faixa. **Recomendação: aceitar.**

Specs confirmadas: MacBookPro7,1, Core 2 Duo 2,4 GHz, 6 GB DDR3 (pentes
trocados — não é config de fábrica), GeForce 320M, serial `W8026S3DATM`.

---


## 1. Contexto real do projeto

Igor + esposa vivem em **São Paulo, capital**, só os dois. Mudança planejada para **Da Nang, Vietnã — Mar/Abr 2027** (~6 meses). Já começaram a vender o que não vão levar.

Estágio atual (reportado 11/09/2026):
- **Já vendidos:** 1 MacBook (vendido via site), itens entregues no grupo do condomínio
- **Em negociação:** 2º MacBook — interessado quer vir buscar
- **À venda:** outros itens
- **Indefinidos:** Igor ainda pensando como vender

O que ele quer:
1. **Controle** do que foi vendido / está à venda / falta vender
2. **Ajuda com copy** dos anúncios (Facebook Marketplace, OLX, grupo do condomínio)
3. **Visibilidade do total arrecadado** (quanto vai juntar)
4. **Página web** com fotos + preço + descrição + status, para mandar o link

---

## 2. ⚠️ Recomendação honesta: "e-commerce" está mal calibrado

**O que ele descreveu não é um e-commerce. É um catálogo/vitrine.** A diferença importa:

| | E-commerce | Catálogo (o que faz sentido aqui) |
|---|---|---|
| Carrinho / checkout | Sim | **Não** |
| Pagamento online | Sim | **Não** — transação é presencial/WhatsApp |
| Estoque/fulfillment | Sim | Não |
| Login de usuário | Sim | Não |
| Homepage própria / descoberta | Sim (SEO, ads) | Não — o link é só mandado no zap |

**Por que e-commerce completo é má ideia aqui:**
1. **É liquidação one-time, não negócio.** Infraestrutura permanente para um evento temporário de 6 meses.
2. **Zero tráfego.** Marketplace, OLX e grupo do condomínio já têm gente com intenção de compra. Um site novo tem plateia vazia — o trabalho de SEO/CDN/pagamento não se paga.
3. **Fricção de pagamento.** Móveis e itens usados em SP = dinheiro/Pix na entrega presencial. Cartão + Stripe + taxa por item só atrapalha.
4. **Custo de oportunidade.** Igor tem RevCash, Fortius, SuperBot VP, AutoClinic, Laudo PDF rodando. Construir e-commerce tira tempo de projeto que gera receita.
5. **Manutenção dupla.** Cada item vendido teria que ser atualizado no site *e* no Marketplace.

**O que faz sentido (e resolve o pedido dele):**
> Uma **página estática de vitrine** com link único (`venda.algumacoisa.com`), fotos, preço, status (à venda / reservado / vendido), botão "chamar no WhatsApp". Sem carrinho, sem checkout, sem login.

Ela resolve 100% do que ele pediu ("mandar o link pras pessoas") com ~5% do custo.

---

## 3. Arquitetura recomendada

```
┌─ FONTE DA VERDADE ────────────────────────────────────┐
│  Google Sheets (1 planilha)                            │
│  Igor E a esposa editam do celular. Zero fricção.      │
│  Colunas: item, categoria, preço pedido, preço vendido,│
│           status, data venda, canal, foto URL, notas   │
└────────────────────────────────────────────────────────┘
                        ↓  (build script, on-demand ou cron)
┌─ GERADOR ─────────────────────────────────────────────┐
│  Script Python: lê a Sheet → gera site estático        │
│  • index.html (catálogo com filtros: à venda/vendido)  │
│  • JSON de dados (para dashboard interno)              │
│  • cards de anúncio por item (copy pronta p/ OLX/FB)   │
└────────────────────────────────────────────────────────┘
                        ↓  wrangler pages deploy
┌─ HOSPEDAGEM ──────────────────────────────────────────┐
│  Cloudflare Pages (free tier) — estático, HTTPS, CDN   │
│  Fotos: mesmo repo (ou R2 se volume grande)            │
└────────────────────────────────────────────────────────┘
```

**Vantagens desse desenho:**
- A esposa edita a planilha do celular → o site reflete no próximo build
- **Zero infraestrutura de servidor** — é estático
- O mesmo dataset alimenta o **tracker de quanto já arrecadou**
- Se ele quiser migrar pra algo maior depois, os dados já estão estruturados

### Alternativa mais simples ainda (se ele quiser rapidez)
Planilha + **Notion/Airtable público**. Ainda menos trabalho, sem build. Mas visual menos customizável e não dá domínio bonito.

---

## 4. Schema do tracker

```
Item            | Categoria | Preço pedido | Preço vendido | Status    | Data venda | Canal         | Comprador      | Notas
MacBook Pro 14  | Eletrônico| R$ 9.500     | R$ 9.000      | Vendido   | 2026-08-xx | Site          | —              | pago à vista
MacBook Air M1  | Eletrônico| R$ 4.800     | —             | Reservado | —          | Marketplace   | (interessado)  | vem buscar
Sofá 3 lugares  | Móvel     | R$ 1.200     | —             | À venda   | —          | —             | —              | retirada no local
...
```

**Métricas que o tracker responde:**
- Total arrecadado até agora
- Total pendente (preço pedido dos à venda) — *potencial*
- Ticket médio
- Tempo médio entre listar e vender
- Qual canal converte melhor
- Quanto falta para a meta da mudança

---

## 5. Copys de anúncio — o que dá pra automatizar

Com **foto + descrição crua do item**, gerar via LLM:
- Título otimizado para busca (OLX/Marketplace usam título como busca)
- Descrição com keywords que comprador usa
- Versão curta pro grupo do condomínio (WhatsApp/Telegram)
- Versão longa pra OLX
- **Preço sugerido** — precisa de pesquisa de mercado (WebSearch na OLX/Marketplace por itens similares)
- Aviso de "retirada no local" / "não envio" (padrão para itens grandes)

**Regra REGRA #1 do SOUL.md:** NADA de publicar automaticamente em Marketplaces de terceiros. Toda copy é **rascunho para o Igor aprovar e postar**. Sem automação de postagem em plataforma de terceiros.

---

## 6. Nome do tópico — corrigir

Criei como **"Sell Out"** mas isso foi escolha ruim: em inglês, *sellout* é pejorativo (quem trai os próprios princípios por dinheiro). Não combina.

**Alternativas:**
- **Moving Sale** ← melhor: claro, direto, alinhado com Travel/Health/Watch
- **Desapego** — pt-BR, comum no Brasil pra isso
- **Garagem** — informal, brasileiro
- **Liquidação** — direto

Recomendo **Moving Sale**.

---

## 7. Próximos passos

- [ ] Igor decide: nome do tópico + se aceita o escopo "catálogo, não e-commerce"
- [ ] Listar o inventário inicial (o que tem pra vender, com fotos)
- [ ] Criar a planilha (Sheets) com o schema de §4
- [ ] Testar viabilidade do deploy: credenciais Cloudflare + wrangler
- [ ] Gerador do site estático (Python: Sheets API → HTML)
- [ ] Primeiro lote de copys de anúncio
- [ ] Definir meta de arrecadação até a mudança

---

## 8. Assets

| Item | Caminho/Ref |
|---|---|
| Tópico Telegram | thread `17222` |
| Projeto | `/root/projects/moving-sale/` (a criar) |
| Skill de deploy | `devops` → verificar creds Cloudflare antes |
| Skill Google Sheets | `google-sheets-pitfalls`, `google-workspace` |
| Planilha financeira existente | RevCash: `1MmOasJn8RZ4281nd_lq-LylLQSDvAvQasFywlzsj_-I` (modelo de referência) |

**Nota infra:** o token Cloudflare (`/root/.cf-token`) só tem permissão Pages — D1/KV/R2 retornam "Authentication error". Suficiente para este projeto. `yaml` NÃO existe no interpretador do `execute_code`; usar `terminal()` com o `python3` do sistema. Puppeteer está global: rodar com `NODE_PATH=$(npm root -g)`.
