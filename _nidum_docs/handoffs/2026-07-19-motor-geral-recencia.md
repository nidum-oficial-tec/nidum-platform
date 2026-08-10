# Handoff — Motor "geral" (busca web) e recência

- **Data:** 2026-07-19
- **Status:** fase encerrada por decisão do dono. Motor geral **não será mais mexido por enquanto.**
- **Ramo dos artefatos:** `feat/tavily-direto-recente` (não publicado até então).
- **Escopo:** SÓ o motor "geral" (fora do contexto Nidum). O motor Nidum (base fechada) **não está em jogo e não foi tocado.**

## TL;DR (2 minutos)

O motor geral migrou para **Tavily "basic" direto** e passou a acertar recência dura
(dólar de hoje, jogo de ontem com data). Sobrou **um** defeito, o mais brando da escala:
em perguntas de recência com a palavra **"ontem"**, o comportamento é **instável** — às
vezes acerta, às vezes "punta" (diz "não consegui confirmar, veja as fontes" mandando os
links certos). Ele **não inventa** placar nem afirma falso com confiança. Decidiu-se
**parar aqui**: o pior caso pro usuário é trabalho extra, não desinformação, e consertar
variância por ajuste de prompt arrisca trocar o punt honesto por chute convicto — o erro
pior, que a migração pra basic já tinha eliminado.

---

## Contexto

- **Objetivo da fase:** o motor "geral" dar respostas **úteis, corretas e atuais**.
  "Santos" e "dólar" foram **canários de recência**, nunca o alvo — não se otimizou para eles.
- **Pipeline:** OWUI + `_tavily_buscar` chamando a API do Tavily direto, modo **basic**.
  Chave `dev` (`tvly-dev-...`), teto **1.000 créditos/mês**.

## O que funciona hoje (produção, Tavily basic)

Testado em produção, todos corretos:
- "cotação do dólar hoje" → R$5,10–5,11, com fontes e ressalva do BCB.
- "último jogo França x Inglaterra na Copa" → correto, incluindo o recorde do Mbappé
  batido no dia anterior. **Recência dura, passou.**
- "quanto foi o último jogo do Santos?" → Botafogo 2×1, 16/07, com data e fonte.

## O que ficou em aberto (não resolvido, por decisão)

A formulação com **"ontem"** em perguntas de recência é **instável**:

| Data | Pergunta | Resultado |
|------|----------|-----------|
| 17/07 | "quem ganhou o jogo do Santos ontem?" (houve jogo dia 16) | **ERRADO** — trouxe amistoso pré-temporada velho (União São João), de página perene do Sofascore |
| 19/07 | mesma pergunta (Santos não jogou dia 18) | **PUNTOU** — "não consigo confirmar, veja as fontes" + links certos. Honesto, mas inútil quando a resposta existia |
| 19/07 | "último jogo" (sem "ontem") | **Correto** |

Três inputs quase iguais, três comportamentos. É **variância**, não um gatilho nítido.

---

## Diagnóstico — SABIDO vs INFERIDO

> Mantida a distinção de propósito. O que está em **SABIDO** foi confirmado por leitura do
> `chatnd.py` ou medido; o que está em **INFERIDO** é hipótese, **não** foi isolado.

### SABIDO — por leitura do código (confirmado no `chatnd.py`, v1.39.0)

- **Geral e Nidum são ramos mutuamente exclusivos** dentro de uma única função `Pipe.pipe`:
  `if categoria == "documentos"` (linha ~2600) vs `if categoria == "geral"` (linha ~2624).
  Não há pipe separado.
- **A busca web é exclusiva do geral:** `_contexto_web` / `_tavily_buscar` / valves `WEB_*`
  só são chamados sob `categoria == "geral"`. O **Nidum é base fechada** (`_contexto_documento`
  → `_buscar_sources` + `Knowledges`) e **NUNCA vê web**.
- **Consequência:** um conserto na busca web do geral **não afeta o Nidum** (outro ramo).
  O **único ponto compartilhado** é o classificador `_classificar` (linha ~2464), que decide
  a `categoria` dos dois → **mexer no texto dele exige rerodar o banco-8.**
- **O aviso que embrulha o contexto web** (a instrução de ancoragem do geral) fica em
  `_montar_contexto_web` (linha ~1403) — função pura, lado geral. É onde um conserto de
  ancoragem entraria.

### SABIDO — por sonda (runner local contra o Tavily real, 8 combos; resultado reportado)

- **Não existe combo global.** `topic=news` ajuda esporte e **envenena** câmbio;
  `topic=finance` faz o inverso. O tópico certo depende da intenção da pergunta.
- **`advanced` é pior para "último jogo":** puxa páginas **perenes** (Sofascore/ESPN)
  desatualizadas — foi a causa do erro do dia 17. **`basic`** traz notícia **datada** e acerta.
  Params mais agressivos não foram o ganho.
- **`days` só age sob `news`/`finance`; é no-op sob `general`** (confirmado empírico:
  combo 4 ≠ combo 5 em finance).
- **Créditos:** `advanced` = 2, `basic` = 1.

### INFERIDO — hipótese, NÃO isolada

- **O erro remanescente parece ser de ancoragem/raciocínio de data (alavanca 3), não de
  retrieval.** No teste de 19/07 a busca trouxe contexto aparentemente suficiente
  (log: `resultados=3`, `3638 chars`) e o modelo puntou mesmo assim.
- **Por que fica como hipótese:** não foi isolado. O log registrou a **quantidade** de
  contexto, mas **não o conteúdo** dos resultados — ninguém confirmou que o jogo certo
  estava de fato no que o modelo recebeu. Sem esse passo, "é ancoragem" é inferência, não fato.

---

## Por que se decidiu parar

1. **O erro que sobrou é o mais brando da escala.** O modelo não inventa placar nem afirma
   falso com confiança; é conservador demais e manda links certos. Pior caso pro usuário =
   **trabalho extra, não desinformação.**
2. **Consertar variância intermitente por prompt tem downside > upside.** Empurrar o modelo
   pro lado confiante troca o punt honesto por chute convicto — justamente o erro pior que a
   migração pra basic-direto **já eliminou.**
3. **Retorno marginal baixo** perto de outras frentes.

---

## Se alguém retomar (ponteiros, não tarefas)

1. **Isolar antes de consertar.** Adicionar um log **temporário** em `_contexto_web`
   imprimindo **títulos/URLs dos N resultados** (não só `chars`), refazer o Santos "ontem",
   e **confirmar se o jogo certo estava no contexto**. Só então decidir entre **ancoragem**
   (aviso em `_montar_contexto_web`, lado geral) e **retrieval**. Não presumir.
2. **Conserto provável, SE indicado:** instrução no aviso do contexto web para tratar data
   como **filtro flexível** — data fixada sem correspondência → dar o mais recente **com a
   data** (ex.: "não jogou ontem; o último foi 16/07, Botafogo 2×1"), preservando a
   honestidade atual **sem induzir chute**. Vive no ramo geral; **não toca classificador
   nem Nidum.**
3. **Artefatos:** `_nidum_tools/sonda_tavily_params.py` e o runner local descartável, no
   ramo `feat/tavily-direto-recente`. Descartar quando não forem mais úteis.
4. **Chave Tavily NÃO foi rotacionada** (decisão: risco baixo — gratuita, sem cartão, sem
   dado de empresa exposto; pior caso é alguém gastar os 1.000 cr/mês). **Se a busca começar
   a falhar por 429/crédito esgotado sem causa aparente, a primeira suspeita é a chave
   exposta, não o código** — gerar chave nova, revogar a atual, limpar histórico do shell.
