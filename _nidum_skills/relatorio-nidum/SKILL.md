---
name: relatorio-nidum
description: Monta relatórios da Nidum em HTML — diagnóstico, acompanhamento de obra, análise de ativo, status de projeto, parecer técnico. Use quando pedirem um relatório, laudo em prosa, dossiê, análise escrita ou documento longo com seções e tabelas. Também para revisar um relatório existente contra a identidade.
---

# Relatório Nidum

Um relatório da Nidum é **um documento para ser lido inteiro**, não um deck para
ser projetado. Ele defende uma conclusão com evidência ordenada. Se o material
cabe em bullets numa tela, é apresentação — use a `apresentacao-nidum`.

Herde a paleta, a tipografia e o tom da **`marca-nidum`**. Esta skill trata só do
que é específico do formato relatório.

## HTML ou PDF

**HTML** é o padrão. Entregue nele quando:

- o relatório tem **tabela larga** — em HTML ela rola dentro do próprio bloco; em
  PDF ela é cortada na margem e não há conserto;
- o leitor vai **navegar** (sumário com âncoras, seções longas);
- o conteúdo ainda vai mudar — reemitir HTML é barato;
- há link para fonte externa que o leitor deve poder clicar.

**PDF** quando o documento vai ser **assinado, protocolado ou arquivado como peça
fechada** — parecer que acompanha contrato, laudo que vai para terceiro, anexo de
processo. PDF é a escolha certa quando *não mudar mais* é uma propriedade
desejada, e não uma limitação.

Na dúvida entre os dois: se alguém vai imprimir, PDF; se alguém vai ler na tela e
possivelmente responder, HTML.

## O que um relatório da Nidum tem

Nesta ordem. Nenhuma seção é decorativa — cada uma responde a uma pergunta que o
leitor faz.

**Cabeçalho** — título do relatório, o objeto (qual ativo, qual projeto, qual
período), a data e quem assina. O leitor precisa saber em cinco segundos *sobre o
quê* e *de quando*. Sem logo gigante: a identidade vem da paleta e da tipografia,
não do tamanho da marca.

**Sumário executivo** — a conclusão, antes da evidência. Três a seis linhas que
respondem "e daí?". Quem lê só isso precisa sair sabendo o que foi decidido ou
recomendado. Escreva-o por último.

**Sumário navegável** — lista de seções com âncora. Obrigatório acima de quatro
seções; dispensável abaixo disso.

**Seções** — uma pergunta por seção, respondida no primeiro parágrafo e
sustentada nos seguintes. Prosa, não bullets: bullet é para enumerar coisas
paralelas, não para fugir de escrever a frase. Uma lista de mais de sete itens
quase sempre é uma tabela mal disfarçada.

**Tabelas** — para dado que se compara. Cabeçalho fixo, números alinhados à
direita com `font-variant-numeric: tabular-nums`, unidade no cabeçalho e não em
cada célula. Toda tabela precisa de uma legenda dizendo **de quando é o dado e
como foi apurado** — número sem método envelhece virando folclore.

**Rodapé** — origem dos dados, data de apuração, e o que ficou fora do escopo.
"O que não foi verificado" é informação, não confissão.

## Cor e tipografia

Use **apenas** os seis nomes oficiais, herdados da `marca-nidum`:

```css
:root{
  --areia:#E5E0D5;   /* fundo do documento */
  --pedra:#9D9890;   /* filetes, texto secundário */
  --terracota:#9A4A2E; /* destaque — um por seção, no máximo */
  --ceu:#4F7187;     /* links e referências */
  --musgo:#515E52;   /* estados positivos, confirmações */
  --escuro:#1F1E1B;  /* texto corrido */
}
```

Regras que não se negociam:

- **Fundo `--areia`, texto `--escuro`.** Sempre.
- **Terracota é acento, não tema.** Um destaque por seção. Terracota em tudo é o
  mesmo que terracota em nada.
- Tipografia: **Maxima Nouva**, com a pilha de fallback completa
  (`-apple-system, Segoe UI, Roboto, Arial, sans-serif`). A fonte vai **embutida
  em base64** — é o que garante que o arquivo abra igual offline, no celular de
  quem recebeu por e-mail e no computador sem a fonte instalada.
- Corpo do texto perto de **65 caracteres por linha**. Relatório é lido, e linha
  longa cansa.
- Números em coluna: `tabular-nums`. Sem isso a coluna "desalinha" e parece erro
  de dado.

## O que não fazer

**Não crie um design system próprio.** Nada de escala de espaçamento nova, nada
de nomes de variável inventados, nada de paleta "complementar". A marca já existe;
o relatório a aplica.

**Não use `@import`.** Ele quebra a garantia de offline — a fonte embutida em
base64 existe justamente para o arquivo não depender da rede, e um `@import`
externo desfaz isso em silêncio: abre certo na sua máquina e errado na de quem
recebeu.

**Nada de fundo escuro.** Relatório da Nidum é claro. Fundo escuro é do deck, e
mesmo lá é exceção. Também não faça tema alternativo: um relatório tem uma
aparência só, e ela é a que vai ser impressa.

**Não use emoji como marcador de seção**, nem ícone decorativo. O que estrutura o
documento é a hierarquia tipográfica.

**Não invente número.** Se o dado não está na fonte, escreva que não está. Um
relatório que preenche lacuna com estimativa não declarada é pior que um
relatório com lacuna.

## Esqueleto mínimo

```html
<style>
  :root{--areia:#E5E0D5;--pedra:#9D9890;--terracota:#9A4A2E;
        --ceu:#4F7187;--musgo:#515E52;--escuro:#1F1E1B}
  body{background:var(--areia);color:var(--escuro);
       font-family:'Maxima Nouva',-apple-system,Segoe UI,Roboto,Arial,sans-serif;
       line-height:1.72;margin:0 auto;max-width:880px;padding:64px 44px 72px}
  h1{font-size:2.2rem;line-height:1.15;margin:0 0 .3rem}
  .objeto{color:var(--pedra);margin:0 0 2.5rem}
  h2{font-size:1.35rem;margin:2.6rem 0 .5rem;
     border-top:1px solid var(--pedra);padding-top:1.4rem}
  .resumo{border-left:4px solid var(--terracota);padding:.2rem 0 .2rem 1.2rem;
          margin:0 0 2rem}
  a{color:var(--ceu)}
  .tabela{overflow-x:auto}
  table{border-collapse:collapse;width:100%}
  td.n{text-align:right;font-variant-numeric:tabular-nums}
  th{text-align:left;border-bottom:1px solid var(--pedra)}
  caption{caption-side:bottom;text-align:left;color:var(--pedra);
          font-size:.88rem;padding-top:.6rem}
  footer{margin-top:3.5rem;border-top:1px solid var(--pedra);
         padding-top:1.2rem;color:var(--pedra);font-size:.9rem}
</style>

<h1>Título do relatório</h1>
<p class="objeto">Objeto · período · data · quem assina</p>

<div class="resumo">
  <p>A conclusão, em três a seis linhas.</p>
</div>

<h2 id="s1">Uma pergunta por seção</h2>
<p>Resposta no primeiro parágrafo; evidência nos seguintes.</p>

<div class="tabela">
  <table>
    <caption>De quando é o dado e como foi apurado.</caption>
    <thead><tr><th>Item</th><th>Valor (R$)</th></tr></thead>
    <tbody><tr><td>Exemplo</td><td class="n">1.234</td></tr></tbody>
  </table>
</div>

<footer>Origem dos dados · data de apuração · o que ficou fora do escopo.</footer>
```

## Antes de entregar

- O sumário executivo responde "e daí?" sozinho?
- Toda tabela tem legenda com data e método?
- O rodapé diz o que **não** foi verificado?
- Alguma cor fora dos seis nomes oficiais? Algum `@import`?
- O arquivo abre igual com a rede desligada?
