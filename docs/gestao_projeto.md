# Gestão do projeto (Scrum, Trello e GitHub)

O enunciado pede: (1) um processo de gestão do projeto, (2) uma plataforma digital de apoio, (3) todos os artefactos
no GitHub e (4) documentação em UML e BPMN. Este documento trata dos três primeiros. Os diagramas estão em
`docs/diagramas/` (explicados no `GUIA.md`, secção 12).

Os campos `[...]` são para o grupo preencher.

---

## 1. Processo: Scrum

Escolhemos o Scrum porque o trabalho mudou várias vezes com o feedback (do professor na intercalar e do próprio
grupo ao rever a app). O Scrum trabalha em ciclos curtos (sprints de 1 semana), com uma revisão no fim de cada um.

**Papéis**

| Papel | Quem | O que faz |
|---|---|---|
| Product Owner | [nome] | decide a ordem das tarefas; fala com o "cliente" (o professor) |
| Scrum Master | [nome] | marca as reuniões e mantém o Trello em dia |
| Equipa | [nomes] | todos: código, testes e documentação |

**Reuniões**

| Reunião | Quando | Para quê |
|---|---|---|
| Planeamento | início do sprint | escolher as tarefas do sprint |
| Ponto de situação | todos os dias, por mensagem | o que fiz / o que vou fazer / o que me bloqueia |
| Revisão | fim do sprint | mostrar a app e recolher feedback |
| Retrospetiva | a seguir à revisão | uma coisa a manter e uma a mudar |

**Uma tarefa está "feita" quando:** o código está no GitHub, `python scripts/verificar.py` passa, a funcionalidade
aparece na app e a decisão está explicada no `GUIA.md`.

---

## 2. Sprints e backlog

| Sprint | Objetivo | Resultado |
|---|---|---|
| 0 | Perceber os dados e organizar o trabalho | dados analisados e limpos; GitHub e Trello criados |
| 1 | Primeira versão (apresentação intercalar) | indicadores; heurísticas com pesos; primeira app |
| 2 | Responder ao feedback | objetivo sem pesos; solver exato com prova; item 5; regras das salas revistas |
| 3 | Entrega final | app online; relatório; apresentação |

**Backlog** (cada linha é um cartão no Trello):

| # | Sprint | História ("Como ... quero ...") | Tarefa | Estado |
|---|---|---|---|---|
| 1 | 0 | Como grupo quero perceber os dados do professor | Analisar os 2 CSV e limpar | Feito |
| 2 | 0 | Como grupo quero um processo de trabalho | GitHub + Trello + sprints de 1 semana | Feito |
| 3 | 0 | Como gestor quero saber o que está mal no horário | Indicadores de qualidade | Feito |
| 4 | 1 | Como gestor quero melhores salas para as aulas | Heurísticas com perfis de pesos | Substituído (5 e 7) |
| 5 | 1 | Como utilizador quero usar tudo num browser | App Streamlit | Feito |
| 6 | 2 | Como docente quero saber quem define os pesos | Objetivo sem pesos | Feito |
| 7 | 2 | Como gestor quero a melhor solução com garantia | Solver exato (HiGHS) com prova | Feito |
| 8 | 2 | Como grupo quero justificar o método | Comparar 4 heurísticas com o ótimo | Feito |
| 9 | 2 | Como decisor quero dar prioridade a um problema | Soluções para outras prioridades (extra) | Feito |
| 10 | 2 | Como utilizador quero propor alterações | Propostas em CSV aplicadas ao horário | Feito |
| 11 | 2 | Como decisor quero comparar propostas sem pesos | Classificação das propostas | Feito |
| 12 | 2 | Como professor quero documentação em notações padrão | Diagramas UML e BPMN | Feito |
| 13 | 2 | Como utilizador quero uma sugestão de sala para uma aula | Página "Sugerir sala" | Feito |
| 14 | 2 | Como aluno não quero mudar de sala a meio da aula | Regra dos blocos | Feito |
| 15 | 3 | Como professor quero aceder à app | Publicar no Streamlit Cloud | [estado] |
| 16 | 3 | Como grupo quero validar os pressupostos | Confirmar tipos de sala com o professor | [estado] |
| 17 | 3 | Como professor quero o relatório final | Relatório e apresentação | [estado] |

**Retrospetivas (o que aprendemos)**
- Sprint 0: olhar para os dados antes de programar foi o que nos fez encontrar os nomes de salas estragados pelo Excel.
- Sprint 1: os pesos eram arbitrários. O professor perguntou "quem define os pesos?" e mudámos de abordagem.
- Sprint 2: rever a app com casos concretos (uma aula que mudava de sala a meio) levou a regras mais realistas.

---

## 3. Trello

1. Em https://trello.com criem o quadro **"Horários ISCTE"** e convidem o grupo e o professor.
2. Criem 4 listas: **Backlog**, **Sprint atual**, **Em curso** e **Feito**.
3. Criem um cartão por linha da tabela de backlog. Para ir mais depressa, copiem a coluna "História" e colem-na
   no campo "Adicionar um cartão": o Trello cria um cartão por linha.
4. Ponham nos cartões uma etiqueta com o sprint (S0 a S3) e movam-nos para a lista certa.
5. Link do quadro: [link]

---

## 4. GitHub

O repositório tem todos os artefactos do projeto: código, dados, resultados, app, documentação, diagramas e
relatório. É o mesmo repositório que o Streamlit Cloud usa para pôr a app online.

- Repositório: [link]
- App online: [link]

Daqui para a frente: cada alteração entra com um commit de mensagem clara (ex.: "Página 4: mostrar choques de
sala"), feito por quem a fez.
