# HANDOFF — Projeto "Moving Sale" (venda do apê antes do Vietnã)

**Tópico Telegram:** thread `17222` (nome inicial "Sell Out" — recomendo renomear, ver §6)
**Criado em:** 2026-09-11
**Responsável:** Hermes (COO) — implementa direto

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

**Nota infra:** Supabase CLI instalado em `/usr/local/bin/supabase`; sem credenciais Cloudflare encontradas no `.env` — **verificar com Igor** antes de planejar o deploy (mas Cloudflare Pages free tier precisa só de conta).
