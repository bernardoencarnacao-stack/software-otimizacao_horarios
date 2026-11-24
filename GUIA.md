# Guia: como funciona o projeto 
Este guia explica tudo sobre o projeto.

---

## 1. O que o projeto faz, numa frase

> Pegamos no horário do ISCTE (dias e horas já definidos), calculamos **a melhor alocação de salas possível** -
> com **prova** de que não há melhor - (item 4) e **comparamos propostas de alteração** feitas por várias
> pessoas (item 5).

Não mexemos nos dias nem nas horas das aulas: isso seria o item 3.

**O que pede o item 4, exatamente?** *"Permita a alocação (**sugestão**) de salas às aulas que estão previstas num
horário, tendo em consideração os requisitos das aulas (v.g. número de estudantes inscritos e o tipo de sala)."*
A **sugestão é da aplicação para o utilizador**: o horário já tem os dias e as horas, e a aplicação sugere a sala de
cada aula. Fazemo-lo de duas formas: 
1. para o horário todo de uma vez - a solução ótima (página "Solução ótima" da app);
2. para **uma aula** escolhida pelo utilizador, existente ou nova - a app lista as salas livres em todas as semanas dessa aula,
da mais adequada para a menos adequada (página "Sugerir sala"). O utilizador a *propor* alterações
ao horário é o item 5 (e o item 8).

**Porquê os itens 4 e 5?** São os mais fáceis de fazer bem com os dados que o professor deu (inscritos, capacidades,
tipos de sala, horas).

---

## 2. Os dados

- **Horário** (26 003 aulas depois da limpeza): cada linha é uma aula num dia concreto, com o curso, a UC, o turno,
  os inscritos, a hora, o tipo de sala pedido e a sala atribuída. Uma aula que se repete 13 semanas aparece em 13 linhas.
- **Salas** (132): o nome, a capacidade e as características de cada sala (laboratório, anfiteatro, etc.).

Limpeza (`horarios/dados.py`):
- tirámos 3 linhas repetidas e 13 aulas sem data;
- a sala 0S08 aparece no horário mas não na lista de salas, por isso acrescentámo-la;
- as salas do Edifício Sedas Nunes vinham com o nome estragado pelo Excel: "1E02" (piso 1, sala E02) aparecia como
  "1,00E+02", porque o Excel a leu como um número em notação científica. Repusemos os nomes originais.

---

## 3. Como medimos se um horário é bom (`horarios/avaliar.py`)

| Indicador | O que é | Tipo |
|---|---|---|
| Aulas sem sala | a aula pede sala e não tem | **grave**: o horário não se pode usar |
| Choques de sala | duas aulas na mesma sala à mesma hora | **grave** |
| Aulas sobrelotadas | mais inscritos do que lugares | **problema** |
| Sala de tipo errado | pediu laboratório e calhou numa sala normal, por exemplo | **problema** |
| Muda de sala a meio | aulas seguidas (ou sobrepostas) do mesmo turno, no mesmo dia, em salas diferentes | **proibido** na solução |
| Fora da sala habitual | numa semana, a aula não está na sala onde essa aula semanal está mais vezes | preferência |

**"Aulas com problemas"** = aulas sobrelotadas + aulas em sala de tipo errado.

**"Aula semanal"** = o mesmo turno, no mesmo dia da semana e à mesma hora, ao longo das semanas (por exemplo,
"DCCTIS02 às quartas das 18:00 às 20:00"). Se numa semana a aula for 18:00–19:00 e nas outras 18:00–20:00, continua
a ser a mesma aula semanal (os horários sobrepõem-se).

**O horário atual** tem 1 013 aulas sem sala e **3 983 aulas com problemas** (3 330 sobrelotadas +
653 tipo errado). Além disso, 47 aulas mudam de sala a meio e 1 299 estão fora da sala habitual.

---

## 4. O objetivo, sem pesos

Na versão anterior usávamos pesos ("uma aula sobrelotada vale 6, uma mudança vale 1..."). Descobrimos dois problemas:
1. os pesos eram escolhidos por nós sem critério;
2. a pesquisa tabu (a melhor das heurísticas) dava soluções **piores em tudo** do que outras que
se encontravam só mexendo nos pesos. Ou seja, não estava a encontrar o melhor.

Agora há **duas restrições**, **uma regra obrigatória** e **um objetivo**, sem pesos:

- **Duas restrições: não há aulas sem sala e não há aulas sobrepostas**, isto é, aulas que coincidem na mesma sala no mesmo dia e hora.
- **Regra obrigatória: ninguém muda de sala a meio da aula.** Aulas do mesmo turno, no mesmo dia, que são seguidas
  (ex.: 18:00–20:00 e depois 20:00–22:00) ou que se sobrepõem, são **a mesma aula** e ficam na mesma sala.
- **Objetivo: o menor número possível de aulas com problemas.** Sobrelotação e tipo de sala contam o mesmo - são
  ambas "uma aula com um problema". São exatamente os dois requisitos que o enunciado do item 4 pede
  ("número de estudantes inscritos e o tipo de sala").
- **Preferência (só depois):** entre as soluções com esse mínimo, pôr a mesma aula **na mesma sala de semana para
  semana**. Mudar de sala entre semanas é permitido - é muito menos mau do que mudar a meio da aula - mas evitamos
  quando não custa nada. (otimização lexicográfica)

---

## 5. Item 4: como encontramos a melhor solução

### 5.1 Blocos: a mesma aula num dia

Um **bloco** é a mesma aula num dia: aulas do mesmo turno, na mesma data, que são **seguidas** (uma começa quando a
outra acaba) ou que **se sobrepõem**. Cada bloco fica numa só sala - é assim que garantimos a regra obrigatória.
Em vez de decidir 24 748 salas (uma por aula), decidimos **19 511 salas** (uma por bloco).

**Entre semanas a sala pode mudar.** Antes obrigávamos a mesma sala em todas as semanas, mas isso custava muito: o
mínimo era 832 aulas com problemas. Sem essa obrigação, o mínimo é **677** (155 a menos), e as semanas ficam
na mesma sala sempre que isso não custa nenhum problema (secção 5.6).

**Exemplo que nos fez rever a regra:** o turno DCCTIS02 tem, às quartas, uma semana das 18:00 às 19:00 e quatro das
18:00 às 20:00. É a mesma aula semanal (os horários sobrepõem-se); a regra antiga exigia horas exatamente iguais e
tratava-as como aulas diferentes. Agora é um só bloco por dia, e na solução as cinco semanas ficam todas no Auditório B2.04 (74 inscritos). Antes ficavam na B2.02, que tem apenas 52 lugares ou seja para além de continuar sempre na mesma sala já não fica numa sala sobrelotada.

### 5.2 Choques

Dois blocos **chocam** se estão a decorrer ao mesmo tempo na mesma data. Blocos que chocam nunca podem ficar na mesma
sala. Há 608 515 pares de blocos que chocam.

### 5.3 O modelo de programação inteira (`horarios/exato.py`)

Escrevemos o problema na "linguagem" que um **solver** percebe:

- **Decisão:** em que sala fica cada bloco. (Variável x[bloco, sala] = 1 se o bloco fica nessa sala, 0 se não.)
- **Regra 1:** cada bloco fica exatamente numa sala.
- **Regra 2:** em cada sala, em cada momento, no máximo um bloco. Para isso, para cada momento de cada dia, olhamos
  para todos os blocos que estão a decorrer ao mesmo tempo, e dizemos: "destes, no máximo um pode estar na sala X".
- **Objetivo:** minimizar as aulas com problemas.

O **solver** (HiGHS, gratuito, usado através da biblioteca `highspy`) faz a parte difícil: explora as combinações
de forma inteligente (corta de uma vez grupos inteiros de combinações que provadamente não podem ser melhores).

### 5.4 A prova: o limite inferior

Esta é a parte mais importante. Além da solução, o solver calcula um **limite inferior**: um valor abaixo do qual é
**impossível** descer, seja qual for a alocação. Quando a solução encontrada é igual ao limite inferior, está provado
que **não existe nenhuma solução melhor**.

No nosso caso: **solução = limite inferior = 677 aulas com problemas**, em todos os dias da semana.

### 5.5 Truques para o solver terminar em minutos

Na primeira tentativa, o solver esteve 4 minutos só na terça-feira e não terminou. Estes truques resolveram:

1. **Um dia da semana de cada vez.** Uma aula de segunda nunca choca com uma de terça (até porque na nossa otimização as aulas nunca mudam em data/hora), por isso cada dia é um problema
   independente e mais pequeno.
2. **Juntar salas iguais.** Salas com a mesma capacidade e características são intercambiáveis: para os problemas,
   tanto faz pôr a aula na C2.01 ou na C2.02. Em vez de "o bloco vai para a C2.01", o solver decide "o bloco vai para
   uma sala do grupo {C2.01, C2.02, ...}", e a regra 2 passa a "no máximo tantos blocos quantas salas tem o grupo".
   Isto elimina milhares de soluções repetidas. No fim, um segundo passo escolhe a sala concreta de cada bloco, sem
   choques e sem piorar nenhum problema.
3. **Plano B.** Se o truque 2 prometer uma solução que, ao escolher as salas concretas, se revela impossível, esse dia
   é resolvido **sala a sala**, sem o atalho. O valor dos grupos continua a ser um limite inferior válido.
4. **Boa solução inicial.** Damos ao solver a solução da pesquisa tabu (a melhor das heurísticas) como ponto de partida. Não muda o ótimo, só o
   ajuda a chegar lá mais depressa.

Com isto, a solução principal fica calculada em **cerca de 3 minutos** num portátil normal.

### 5.6 A preferência: a mesma sala de semana para semana

Depois de o solver encontrar o mínimo de problemas, ainda há muitas soluções com esse mesmo mínimo. Escolhemos uma em
que as semanas da mesma aula ficam na mesma sala, em dois passos:

1. ao escolher as salas concretas, o solver mantém o máximo de aulas na sala que já tinham (o horário de exemplo é
   quase sempre igual de semana para semana);
2. uma **pesquisa local** (`otimizar.consolidar_semanas`) pega em cada aula semanal que ainda está em salas diferentes
   e tenta levar as semanas "fora" para a sala habitual - movendo-as, se a sala estiver livre, ou trocando com a aula
   que lá está. Só aceita a jogada se **nenhuma aula ficar com mais problemas**.

Resultado: as aulas fora da sala habitual passam de 3 997 para **1 005** (o horário atual tem 1 299), sem mexer
nas 677 aulas com problemas. **Esta parte não tem prova de ótimo** (é uma preferência, resolvida por pesquisa local),
e admitimo-lo. As restantes 1 005 aulas (4% das 24 748) ficam noutra sala nessa semana porque a sala habitual está
ocupada e trocar daria mais problemas, ou porque nessa semana há uma sala melhor livre (ex.: um laboratório).
A pesquisa local não garante o mínimo: por exemplo o próprio cenário extra "Sobrelotação primeiro" (ver secção 8) chega a 998.

### 5.7 Resultado

| | Aulas com problemas | Sobrelotadas | Tipo errado | Sem sala | Muda a meio | Fora da sala habitual |
|---|---:|---:|---:|---:|---:|---:|
| Horário atual | 3 983 | 3 330 | 653 | 1 013 | 47 | 1 299 |
| **Solução ótima** | **677** | 409 | 268 | 0 | **0** | 1 005 |

**Exemplos reais:**
- *Cognição e Emoção* (MCE, turno 00121TP02) tem aulas às sextas das 18:00 às 20:00 e das 20:00 às 22:00, com 33
  inscritos, na AA3.26 (30 lugares). Fica na **1E06 (50 lugares) nas duas aulas seguidas e em todas as semanas**:
  deixa de estar sobrelotada e ninguém muda de sala a meio.
- *Investigação Operacional* (LG, turno IOTP06), 31 inscritos, estava na AA3.30 (24 lugares). Às terças (8:00–11:00,
  duas aulas seguidas) passa para a AA3.40 (32 lugares) e às quintas para a 2E07 (50 lugares), sempre na mesma sala.
- *Análise de Indicadores Estatísticos* (turno 00555TP03), quintas 18:00–20:00, pede laboratório de informática. Fica
  no Auditório B2.03 em 9 semanas e, numa semana em que há um laboratório livre (D1.09), vai para lá. É um exemplo de
  "mudar de sala entre semanas": nessa semana a aula fica com o tipo de sala certo.

**O que ganhámos ao deixar a sala mudar entre semanas:** obrigar a mesma sala em todas as semanas dava, no mínimo,
832 aulas com problemas; agora são 677. Ou seja, 155 aulas deixam de estar sobrelotadas ou em sala de tipo errado,
à custa de algumas aulas mudarem de sala numa ou noutra semana.

**Aulas mudadas face ao horário original:** 4 410 aulas ficam numa sala diferente da que tinham no horário de exemplo. Muitas não resolvem um
problema da própria aula: libertam a sala certa para outra aula que precisa dela (um "efeito dominó").

---

## 6. Porquê um solver, e porquê o HiGHS

**Porquê o solver e não as heurísticas?** Porque medimos (secção 7): com o mesmo objetivo, a melhor heurística ficou
25% acima do ótimo, e o solver dá a solução **e a prova** de que é a melhor.

**Porque é que não começámos logo pelo solver, e porquê heurísticas?**
1. **O conselho do professor.** Problemas de grande dimensão como um horário universitário são tão complexos que os métodos exatos normalmente não terminam; aí as heurísticas (pesquisa tabu,
   algoritmos genéticos) são a ferramenta habitual e que de facto foram muito úteis na mesma.
2. **O nosso item 4 é um subproblema mais pequeno e com estrutura especial**: dias e horas fixos, cada dia da semana
   independente, salas iguais entre si. Não sabíamos à partida que isso chegava - **a primeira tentativa com o solver
   falhou** (a terça-feira não terminou em 4 minutos). Só com os truques da secção 5.5 passou a resolver em minutos.
3. **O percurso foi:** heurísticas com pesos → reparámos que havia soluções piores em tudo do que outras → desconfiámos
   que a heurística estava longe do ótimo → testámos um método exato → confirmámos e provámos. Foi sobretudo à base de teste e "tentativa e erro".

**As heurísticas não foram inúteis:** dão ao solver o ponto de partida, a pesquisa local trata da preferência "mesma
sala entre semanas", e seriam o plano B se o problema crescesse (por exemplo, se mexêssemos também em dias e horas).

**Porquê o HiGHS e não outro solver?**
- É **open source e gratuito** (licença MIT): não precisa de licença, ao contrário do Gurobi ou do CPLEX (comerciais),
  e instala-se com `pip install highspy`, por isso corre em qualquer computador e no Streamlit Cloud.
- Segundo a Universidade de Edimburgo, que o desenvolve, é o software open source de otimização linear com melhor
  desempenho nos benchmarks padrão da área.
- É o solver usado por omissão para estes problemas no **SciPy** e no **MATLAB**, e está disponível no Pyomo, PuLP e
  OR-Tools - é uma escolha padrão, não exótica.
- Alternativas: CBC e GLPK (open source, mais antigos), CP-SAT do OR-Tools (alternativa válida), Gurobi/CPLEX (mais
  rápidos, comerciais). **Não as comparámos com testes**: o HiGHS é uma escolha fundamentada, não o vencedor de uma
  comparação nossa.

**Nuance importante:** o professor tem razão que não existe um horário "perfeito" no mundo real. O que provámos é mais
estreito: **para este modelo** (dias e horas fixos, estes critérios, estes dados) não há nenhuma alocação de salas com
menos de 677 aulas com problemas. Com outros critérios, o ótimo seria outro.

## 7. As heurísticas: porque é que não chegavam (`scripts/comparar_metodos.py`)

Uma **heurística** é um método que procura boas soluções depressa, mas sem garantia de ser a melhor. Comparámos quatro
heurísticas com o solver exato, **todas com o mesmo objetivo e a mesma regra obrigatória**, 60 segundos cada, 3
repetições:

| Método | Como funciona | Aulas com problemas | Acima do ótimo |
|---|---|---:|---:|
| Guloso | cada bloco na sala que tem hoje, ou na melhor livre | 4 057 | +499% |
| Algoritmo genético | população de 30 soluções, cruzamento e mutação | 3 157 | +366% |
| Pesquisa local simples | só aceita mudanças que melhoram | 864 | +28% |
| Pesquisa tabu | aceita mudanças piores + lista tabu | 846 | +25% |
| **Solver exato** | programação inteira, com prova | **677** | **ótimo provado** |

**O que isto mostra:** as heurísticas melhoram muito o horário atual, mas ficam longe do ótimo, acabavam por ficar presas em máximos locais. Sem o solver exato,
não teríamos como saber.

---

## 8. Extra: prioridades (página "Solução ótima" da app)

A solução principal trata sobrelotação e tipo de sala como igualmente importantes. Se o ISCTE quiser dar prioridade a
uma delas, calculámos também, com o solver exato:

| Solução | Ordem | Sobrelotadas | Tipo errado | Fora da sala habitual |
|---|---|---:|---:|---:|
| **Ótima (principal)** | problemas (a contar igual) | 409 | 268 | 1 005 |
| Sobrelotação primeiro | sobrelotação → tipo de sala | 0 | 677 | 998 |
| Tipo de sala primeiro | tipo de sala → sobrelotação | 620 | 57 | 1 142 |

Cada uma é **provada ótima para a sua ordem**, por isso nenhuma é pior em tudo do que outra - são compromissos
diferentes. Isto é uma **funcionalidade extra**, não o resultado principal.

**Uma descoberta interessante:** as três soluções têm o **mesmo total de 677 aulas com problemas**; só muda a
divisão. Ou seja, há muitas soluções ótimas, e é possível ter **zero aulas sobrelotadas** sem aumentar o total (à
custa de mais aulas em sala de tipo errado). Se o ISCTE preferir garantir lugar a todos os alunos, tem essa
alternativa.

**Porque é que não há "pesos à escolha"?** Cada solução exata demora alguns minutos. E soluções aproximadas podem ser
piores em tudo do que outras, que era um dos problemas da versão que havíamos feito anteriormente.

---

## 9. Item 5: comparar propostas de vários utilizadores

Cada pessoa (coordenação, docentes, gabinete de espaços...) propõe alterações num **ficheiro CSV**:

```
aula_id,nova_sala,nova_data,novo_inicio,novo_fim
1520,C3.01,,,
2044,,2023-03-10,09:30,11:00
```

(células vazias = não mudar). A app aplica cada proposta ao horário e classifica-as com **a mesma regra do item 4,
sem pesos**:

1. **É utilizável?** Aulas sem sala ou choques de sala tiram a proposta da corrida. Exemplo: a proposta de exemplo 2
   (a coordenação pediu salas maiores mas só confirmou que estavam livres na primeira semana) tem 263 choques.
2. **Menos aulas com problemas.**
3. **Menos aulas a mudar de sala a meio**, e depois **menos aulas fora da sala habitual**.

A app lembra ainda que nenhuma proposta pode ter menos de 677 aulas com problemas (o mínimo provado).

As 3 propostas de exemplo **fomos nós que as simulámos** (`scripts/criar_exemplos.py`), para mostrar a app a funcionar.

---

## 10. A app (`app.py`)

Feita com **Streamlit** (biblioteca de Python que transforma um script numa página web). A app tem 5 páginas/abas:

1. **Início:** o que fizemos, as regras e o resultado em resumo; depois, o horário atual (números e lista de aulas
   com problemas, por curso).
2. **Solução ótima (item 4):** o resultado, a prova dia a dia, o download do horário otimizado e, no fim, o extra das
   prioridades.
3. **Sugerir sala (item 4):** salas livres para uma aula existente ou nova.
4. **Comparar propostas (item 5):** carregar CSVs e classificá-los; a verde, o melhor valor de cada coluna. Pode
   incluir as soluções com prioridades.
5. **Métodos:** as heurísticas contra o solver exato.

As soluções ótimas são calculadas antes (`scripts/calcular_otimo.py`, ~17 minutos para os 3 cenários) e a app só
as lê, por isso abre logo.

---

## 11. Pressupostos (a confirmar com o professor)

| Pressuposto | O que usámos | Onde se muda |
|---|---|---|
| Capacidade de uma sala | "Capacidade Normal" (não a de exame) | `horarios/dados.py` |
| "Sala/anfiteatro aulas" | aceita sala normal, anfiteatro ou sala de mestrado | `horarios/avaliar.py` (`EQUIVALENTES`) |
| Tipos de sala que não existem no cadastro (ex.: "Lab ISTA") | qualquer sala serve | `horarios/avaliar.py` (`tipo_aceite`) |
| Sobrelotação | conta a aula, não quantos alunos ficam sem lugar | `horarios/otimizar.py` |

**O que pusemos de lado, e porquê:**
- **Pesos** (versão da intercalar): eram arbitrários e davam soluções piores em tudo do que outras.
- **Obrigar a mesma sala em todas as semanas:** custava 155 aulas com problemas a mais (832 em vez de 677).
- **Item 3 (criar o horário de raiz):** faltam dados (docentes, planos de estudo) e é muito maior.

---

## 12. Diagramas (UML e BPMN)

Estão em `docs/diagramas/` e também no relatório.

| Diagrama | Notação | O que mostra |
|---|---|---|
| `1_casos_de_uso.png` | UML - casos de uso | quem usa o sistema (gabinete, decisor, utilizadores) e para quê |
| `2_classes.png` | UML - classes | os módulos do código e como dependem uns dos outros |
| `3_sequencia_item4.png` | UML - sequência | como se calcula a solução ótima (script → modelo → solver → app) |
| `4_sequencia_item5.png` | UML - sequência | como a app avalia e ordena as propostas dos utilizadores |
| `5_processo_bpmn.png` / `.bpmn` | BPMN 2.0 | o processo de decisão no ISCTE, do horário à publicação (o `.bpmn` abre em https://demo.bpmn.io) |

---

## 13. Onde está cada coisa no código

| Ficheiro | O que tem |
|---|---|
| `horarios/dados.py` | ler e limpar os CSV |
| `horarios/avaliar.py` | os indicadores (incluindo blocos e aulas semanais); aplicar ficheiros de alterações |
| `horarios/otimizar.py` | blocos, choques, as heurísticas (guloso, tabu, genético) e a pesquisa local "mesma sala entre semanas" |
| `horarios/exato.py` | o modelo de programação inteira |
| `horarios/sugerir.py` | salas livres e ordenadas para uma aula concreta |
| `scripts/calcular_otimo.py` | calcula as soluções ótimas e grava-as em `resultados/` |
| `scripts/comparar_metodos.py` | heurísticas contra o ótimo |
| `scripts/criar_exemplos.py` | as 3 propostas de exemplo do item 5 |
| `scripts/verificar.py` | confirma as soluções sem usar o solver |
| `app.py` | a aplicação web |
