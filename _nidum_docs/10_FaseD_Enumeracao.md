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

Medido em 05/09/2026, depois da migração para base = pasta-mãe:

| | |
|---|---|
| arquivos com `tipo: ata` | **61** |
| distribuídos em | `3 - Reuniões` 44 · `Produtos` 15 · `Tecnologia` 2 |
| tamanho de uma ata | mediana **8.654** chars · p90 **14.245** |
| **todas as atas somadas** | **667.420 chars** |
| orçamento do pipe (`MAX_CHARS_TOTAL`) | **200.000** |

**É esse par de números que decide o desenho:** ler todas as atas custa **3,3× o
orçamento inteiro**. Qualquer desenho que dependa de "ler tudo" está morto antes de
começar — e é por isso que a saída não é aumentar o `k`.

> Nota sobre o "108" da Fase A: aquele número era a coleção `nd-atas` inteira, que
> misturava tipos. Hoje `3 - Reuniões` tem 75 arquivos, dos quais **44** são atas. Os
> dois números estão certos; medem coisas diferentes.

---

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

## O que este levantamento não decide

- **Quem gera a ficha.** Modelo na ingestão (custo por documento, qualidade variável)
  ou regra determinística (barata, e só pega o que estiver formatado). Precisa de uma
  medição sobre 10 atas reais antes de escolher.
- **Se a ficha é reindexada quando a ata muda.** É a mesma disciplina do carimbo, com
  o mesmo custo de reconversão.
- **Se `tipo: ata` cobre o que interessa.** São 61 de 648 documentos. Registros também
  carregam pendência, e ninguém mediu quantos.
