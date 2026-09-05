# 10 — Fase D: enumeração

> **Levantamento de desenho. Nada implementado.**
> **Para quem é:** quem for decidir se e como fazer. **Não** é um plano aprovado.

---

## O problema, em uma frase

`query_knowledge_files` é busca semântica **top-k**. Perguntar *"todas as pendências
do jurídico"* devolve os k trechos mais parecidos — **nunca todos**. Não é falha de
prompt nem de modelo: **top-k não enumera**, por definição.

A medida está no teste 1 da Fase A: o agente leu **4 atas de 108** e respondeu com
honestidade — *"10 pendências nas 4 atas"*. Não inventou, e não fingiu completude. O
problema não é a resposta; é o alcance.

## O que o acervo diz hoje

Medido em 05/09/2026, depois da migração para base = pasta-mãe.

### O critério da ficha: nem tipo, nem pasta — **os dois**

A pergunta era escolher entre marcar convergência como `tipo: ata` ou gerar a ficha
por pasta. **A medição mostra que nenhum dos dois sozinho serve**, e corrige duas
premissas pelo caminho.

**As Convergências já são `tipo: ata`.** São 18, todas em `3 - Reuniões/Atas`, todas
classificadas certo. O classificador não está deixando a nomenclatura antiga de fora.

**O vão é outro, e maior: 31 dos 75 arquivos da pasta de atas são `tipo: registro`.**
E não são um nome alternativo — são 31 títulos diferentes:
`MKT_Discussão de Narrativa da Metodologia_10-08`, `TEC_Alinhamento de time_03-08`,
`OPE_..._Semanal 12-08-26`, `PROD_laudos free e plus_18-08`. **Não há sinônimo a
acrescentar ao classificador; há 31 títulos.**

| critério | pega | perde |
|---|---:|---|
| só por **tipo** | 61 | **31** registros dentro da pasta de atas |
| só por **pasta** | 77 | **15** atas em pasta de trabalho (`Produtos/Captação...`, `Produtos/Jornada...`) |
| **união** | **92** | — |

**Decisão: a união.** `tipo: ata` **OU** pasta de atas. E a razão é mais forte do que
"combina com base = pasta": são **dois sinais independentes, e qualquer um basta**.
Nome novo daqui a um ano é pego pela pasta; ata arquivada fora da pasta de atas é pega
pelo tipo. Nenhum dos dois é ponto único de falha — que é exatamente a pergunta que
você fez sobre o futuro.

### O custo, e ele aperta

| | |
|---|---|
| documentos no critério (união) | **92** |
| se lidos inteiros | **944.610 chars** |
| orçamento do pipe (`MAX_CHARS_TOTAL`) | **200.000** |
| **fichas a ~1.500 chars** | **138.000 — 69% do orçamento** |

Ler os documentos inteiros custa **4,7× o orçamento**. As fichas cabem, mas **ocupam
mais de dois terços dele** — e isso deixa pouco espaço para o resto da conversa. É o
número que a etapa E2 tem de medir de verdade: se a ficha real sair maior que 1.500
chars, a margem acaba.

> Nota sobre o "108" da Fase A: aquele número era a coleção `nd-atas` inteira, que
> misturava tipos. Hoje `3 - Reuniões` tem 75 arquivos. Os dois números estão certos;
> medem coisas diferentes.

### A diferença 77 × 75: não consigo responder daqui

O que dá para afirmar: **nenhum dos dois é exclusão nem quarentena nossa.** A pasta
`3 - Reuniões` produz 75 arquivos indexados e **zero excluídos**, e o livro-caixa da
quarentena (1.447 itens) não tem nada vindo dela.

Como órfãos e faltantes estão em zero, **também não é falha de sincronização.** A
explicação mais provável é que os 77 do SharePoint incluam **duas subpastas** — a
contagem da tela conta pasta como item. Mas isso é hipótese: quem responde é o
`conferir.py`, que compara SharePoint × base e precisa das quatro credenciais do
SharePoint.

## O desenho mínimo: ficha de fatos por ata

**A ideia:** a esteira, na ingestão, gera para cada ata uma **ficha** curta e
estruturada, gravada como `.md` na mesma pasta da ata. A ficha é indexada como
qualquer outro documento.

```
Reuniões/Atas/ATA_Comite_2026-08-14.md          (a ata, 8.654 chars)
Reuniões/Atas/ATA_Comite_2026-08-14.fatos.md    (a ficha, ~1.500 chars)
```

Conteúdo da ficha — uma linha por fato, formato fixo:

```markdown
<!-- ficha: ata | origem: ATA_Comite_2026-08-14.md | gerada: 2026-09-06 -->
- pendência | jurídico | revisar cláusula de rescisão do contrato quadro | resp: não consta | prazo: não consta
- pendência | operações | fechar laudo do apto 206 | resp: Kenji | prazo: 2026-08-30
- decisão | jurídico | aprovada a minuta v3 do termo de coautoria
```

**Por que isto responde a pergunta:** 61 fichas × ~1.500 chars = **~92.000 chars**,
dentro do orçamento. O agente lê **todas**, e enumerar deixa de ser busca — vira
leitura.

### Por que esta forma, e não uma camada de fatos separada

**Não precisa de armazenamento novo, nem de ferramenta nova, nem de mudança no pipe.**
A ficha é um `.md`; a esteira já sabe indexar `.md`; o agente já sabe lê-los. A Fase D
passa a ser **um gerador na ingestão**, e não uma arquitetura.

**E não depende de ninguém mudar como escreve ata.** A alternativa mais simples seria
uma convenção de escrita — "toda pendência numa linha começando com `- [ ]`" — e então
`grep_knowledge_files` enumeraria sem nenhuma infraestrutura. É genuinamente mais
barato **em código**, e mais caro exatamente onde este projeto costuma falhar: exige
que 100% das atas futuras sigam a convenção, e não faz nada pelas 61 que já existem.
Ficha gerada funciona no acervo de hoje.

---

## Etapas até a primeira versão utilizável

**E0 — os casos de aceite.** Antes do desenho, e é o que a seção final traz.

**E1 — o gerador de fichas, só para atas.** Entrega: 61 fichas indexadas. É a etapa que
responde a pergunta do teste 1. Mede-se comparando com uma contagem feita à mão.

**E2 — medir o custo real de leitura.** Entrega: quantos chars o agente consome ao
responder *"todas as pendências do jurídico"* lendo fichas. Se couber no orçamento, a
Fase D está utilizável e as etapas seguintes são opcionais.

**E3 — `consultar_fatos` como ferramenta**, *se e somente se* E2 mostrar que ler as
fichas é caro demais. É otimização, não pré-requisito — e tratá-la como pré-requisito
seria construir a parte cara antes de saber se ela é necessária.

**E4 — estender além das atas.** Registros e informativos também carregam fato. Só
depois de E2 provar o mecanismo no caso mais fácil.

**A primeira versão utilizável é E1 + E2.** Duas etapas.

---

## `consultar_fatos` no laço agêntico — se chegar a E3

**Recebe:** `tipo` (`pendencia` | `decisao` | `prazo`), `area` (opcional), `bases`
(opcional, os ids do recorte ativo).
**Devolve:** **todos** os registros que casam, com a origem de cada um — nunca um
top-k, nunca truncado em silêncio. Se houver mais do que cabe, devolve a contagem
total e a primeira página, **dizendo que truncou**.

### A docstring é a interface, e o PPTX já cobrou essa lição

O D22 mostrou que o modelo escreve a entrada e transcreve a saída: o campo se chamava
`texto` e a docstring dizia "corpo" cinco vezes — o modelo mandou `corpo`. **O nome na
docstring é o contrato.**

Aqui o risco é o modelo usar `consultar_fatos` para busca comum, ou
`query_knowledge_files` para enumerar. A docstring precisa separar as duas **pela
pergunta**, não pela implementação:

> `consultar_fatos` — use quando a pergunta pede **TODOS** os itens de uma categoria:
> "todas as pendências", "quantas decisões", "liste os prazos". Devolve o conjunto
> COMPLETO, e diz explicitamente quando trunca. **Não** use para pergunta aberta ("o
> que foi discutido sobre X") — para isso é `query_knowledge_files`.
>
> `query_knowledge_files` — busca semântica por semelhança. Devolve os trechos mais
> parecidos, **nunca todos**. Não use para enumerar: a resposta pareceria completa e
> não seria.

A última frase é a que importa, e é dirigida ao defeito real: hoje nada avisa o modelo
de que o resultado é parcial.

---

## O que muda com base = pasta

**A ficha respeita o `#` sem nenhum código adicional** — e isso é consequência direta
do eixo novo. A ficha mora na mesma pasta da ata, logo na **mesma base**. Quem
seleciona `3 - Reuniões` recebe as atas daquela pasta **e as fichas daquelas atas**.

**Sim: com `#` em Reuniões, "todas as pendências" enumera só Reuniões.** É a premissa
do produto (D32/D35) aplicada à camada de fatos, e é o comportamento correto — não uma
limitação a contornar. Quem quer o acervo inteiro não seleciona base.

> No eixo antigo isto **não** funcionaria: as fichas precisariam de coleção própria (ou
> cairiam em `nd-normas`), e o recorte por `#` passaria a incluir fatos de pastas que o
> usuário não selecionou. **O eixo por pasta é o que torna a Fase D compatível com o
> Modo 2 de graça.**

Consequência a aceitar, e ela é real: uma ata do comitê jurídico arquivada em
`Produtos` não é enumerada por quem selecionou `Jurídico`. Hoje isso vale para **15 das
61 atas**, que estão em `Produtos`, mais 2 em `Tecnologia`.

---

## Os casos de aceite — escritos antes do desenho

**Caso 1 — a linha de base a superar.** *"Quais são todas as pendências do jurídico,
segundo as atas?"* Sem recorte. Hoje: 4 atas de 108 (~96% não visto). **Aceite:** cita
pelo menos 90% das atas que contêm pendência jurídica, contadas à mão numa amostra de
referência.

**Caso 2 — contagem confere.** A mesma pergunta na forma *"quantas"*. **Aceite:** o
número bate com a contagem manual, ou o agente declara a margem e por quê.

**Caso 3 — não inventa o que falta.** Uma ata com pendência sem responsável.
**Aceite:** aparece como *"resp: não consta"*, nunca preenchida por inferência.

**Caso 4 — o recorte manda.** A mesma pergunta com `#` em `Jurídico`. **Aceite:**
enumera só o que está naquela base, e **diz** que o recorte está ativo. Uma resposta
que silenciosamente incluísse outras bases **reprova**, mesmo estando "mais completa".

**Caso 5 — truncamento é declarado.** Volume acima do orçamento. **Aceite:** devolve o
que cabe **e diz quanto ficou de fora**. Resposta truncada em silêncio reprova.

**Caso 6 — ficha ausente não vira lacuna silenciosa.** Uma ata sem ficha gerada.
**Aceite:** a resposta declara que N atas não têm ficha. É o D37 aplicado ao produto:
a ausência tem de ser visível, senão *"nenhuma pendência"* e *"não conferi"* ficam
iguais.

---

## As três perguntas do desenho

### 1. Quem gera a ficha, e a que custo

**Recomendação: modelo na ingestão, e a ata entra SEM ficha quando ele falha — a
rodada nunca para por isso.**

Regra determinística foi considerada e não serve para este acervo: os 31 registros
não têm formato comum, e uma regra que só pega o que já está formatado devolveria
fichas vazias justamente para os documentos que motivaram a Fase D.

| | |
|---|---|
| modelo | o **classificador** já em uso (`gpt-5-mini`), não o de conversa |
| entrada | a ata inteira — mediana 8.654 chars |
| saída | a ficha — ~1.500 chars |
| chamadas na carga inicial | **92**, uma vez |
| chamadas no regime | só ata nova ou alterada — ordem de **poucas por dia** |

**Por que a rodada não para:** a esteira já tem o padrão certo para isto — a
quarentena. Falha de geração vira **linha no livro-caixa e item na Issue**, com o
nome da ata e o motivo; a ata entra normalmente e continua buscável. Parar a rodada
por falha de um derivado seria deixar o índice congelado por causa de uma ficha — a
via 3 do D28 auto-infligida.

**E o Caso 6 é o que impede isso de virar buraco silencioso:** a resposta declara
quantas atas estão sem ficha. Ficha ausente com aviso é lacuna conhecida; ficha
ausente calada é a mesma coisa que "nenhuma pendência".

### 2. Cada fato aponta para onde na ata

**Sim, e é requisito, não enfeite.** A regra da casa — a IA nunca origina número, só
organiza e mostra a conta — vale aqui inteira: **a ficha é índice, não fonte.**

Cada linha carrega a **âncora**: seção quando a ata tem cabeçalhos, linha aproximada
quando não tem.

```
- pendência | jurídico | revisar cláusula de rescisão | resp: não consta | @ Encaminhamentos
```

**O que o agente deve citar é a ata**, e a âncora é o que torna isso possível sem ler
os 8.654 chars: ele lê a ficha para saber **onde olhar**, abre a ata e cita de lá.
Sem âncora, ou ele cita a ficha (que é texto derivado, gerado por modelo) ou lê a ata
inteira — e aí o orçamento volta a estourar.

**Consequência para o formato:** a ficha não pode parafrasear ao ponto de a âncora
não achar mais o trecho. É caso de aceite próprio, e entra na E1.

### 3. A ficha compete com a ata na busca semântica

**Compete, sim — e no eixo por pasta ela compete dentro da MESMA base.** Documento
denso e curto ranqueia bem: 1.500 chars de fatos concentrados batem 8.654 chars de
transcrição em quase qualquer consulta por semelhança.

**É problema, e não comportamento esperado**, por um motivo específico: para pergunta
**aberta** ("o que foi discutido sobre X"), a ficha é a resposta **errada** — ela tem
os fatos e perdeu a discussão, que era o que a pergunta queria. O agente citaria um
resumo gerado por modelo em vez do registro humano.

Três saídas, e a terceira é a que recomendo:

1. **Ficha fora do índice semântico**, alcançável só por `grep`/leitura direta.
   Resolve, mas exige distinção de indexação que a esteira hoje não tem.
2. **Marcar a ficha no próprio texto** (`<!-- ficha -->` no topo, e uma primeira linha
   dizendo "índice de fatos; a fonte é <ata>"). Barato, e depende do modelo respeitar.
3. **Medir antes de decidir** — E2 roda as duas perguntas, a fechada e a aberta, e
   olha **o que foi citado**. Se a ficha aparecer como fonte de pergunta aberta, (1)
   vira necessário; se não aparecer, (2) basta.

Decidir agora entre (1) e (2) seria escolher um conserto para um problema cuja
frequência ninguém mediu — e este projeto já pagou por isso hoje: eu propus três
saídas para o `MODELO_GERAL` e a resposta era abrir uma tela.

### Confirmado: a ficha é derivado, e reconversão total a regenera sozinha

**Sim.** A ficha é produzida pelo mesmo caminho que produz o `.md` — `resync` reconverte
a ata e **regenera a ficha junto**, sem intervenção. Ela nunca é editada à mão e nunca
é fonte de si mesma.

Duas consequências que precisam estar escritas antes da E1, porque são a diferença
entre derivado e cópia:

- **Ficha órfã é defeito.** Ata removida leva a ficha junto; senão a ficha vira fato
  sobre documento que não existe — e o relatório de órfãos passa a acusá-la, o que é
  o comportamento certo.
- **Ficha nunca entra no `_arquivo/`.** Derivado não se arquiva: se a ata voltar, a
  ficha se regenera; se não voltar, a ficha não serve para nada.

## O que este levantamento não decide

- **Quem gera a ficha.** Modelo na ingestão (custo por documento, qualidade variável)
  ou regra determinística (barata, e só pega o que estiver formatado). Precisa de uma
  medição sobre 10 atas reais antes de escolher.
- **Se a ficha é reindexada quando a ata muda.** É a mesma disciplina do carimbo, com
  o mesmo custo de reconversão.
- **Se `tipo: ata` cobre o que interessa.** São 61 de 648 documentos. Registros também
  carregam pendência, e ninguém mediu quantos.
