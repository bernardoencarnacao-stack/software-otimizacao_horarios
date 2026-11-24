# Gestão de horários do ISCTE

**Otimização e Decisão em Engenharia de Software · Grupo 17 · Itens 4 e 5**

- **Item 4:** sugerir a melhor sala para cada aula do horário (dias e horas fixos), tendo em conta os inscritos e o
  tipo de sala.
- **Item 5:** comparar propostas de alteração ao horário feitas por diferentes utilizadores.

**App online:** https://software-otimizacaohorarios-vb4zxc24yt8ktpfzds5wv9.streamlit.app/

**Trello:** https://trello.com/b/IbBfTb2Z/software-otimizacaohorarios

**Relatório:** [`docs/Relatorio_Horarios_ISCTE.docx`](docs/Relatorio_Horarios_ISCTE.docx)

Para perceber o projeto de ponta a ponta **por favor** ler: **[GUIA.md](GUIA.md)**.

## Em resumo

- **Regra obrigatória:** ninguém muda de sala a meio da aula (aulas seguidas ou sobrepostas do mesmo turno, no mesmo
  dia, ficam na mesma sala). Entre semanas a sala pode mudar.
- **Objetivo, sem pesos:** o menor número de aulas com problemas (sobrelotadas ou em sala de tipo errado, a contar
  igual). Depois, sem piorar isto, tentar que seja a mesma sala de semana para semana.
- **Método:** programação inteira com o solver **HiGHS**, que dá a solução e a prova. Comparámos com 4 heurísticas:
  a melhor (pesquisa tabu) fica 25% acima do ótimo.

| | Aulas com problemas | Sobrelotadas | Tipo errado | Sem sala | Mudam a meio |
|---|---:|---:|---:|---:|---:|
| Horário atual | 3 983 | 3 330 | 653 | 1 013 | 47 |
| **Solução ótima (provada)** | **677** | 409 | 268 | 0 | 0 |

## Correr a app localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Embora a mesma também esteja publicada no Streamlit Community Cloud estando disponível através do link de acesso: https://software-otimizacaohorarios-vb4zxc24yt8ktpfzds5wv9.streamlit.app/


## O que está em cada pasta

```
app.py              a aplicação web
requirements.txt    bibliotecas de Python necessárias (o Streamlit Cloud também usa este ficheiro)
GUIA.md             explicação de tudo, com perguntas prováveis do professor

horarios/           o código do projeto
  dados.py            ler e limpar os dois CSV do professor
  avaliar.py          medir a qualidade de um horário; aplicar propostas
  otimizar.py         blocos e choques; heurísticas (guloso, tabu, genético)
  exato.py            o modelo de programação inteira (solver HiGHS)
  sugerir.py          sugerir salas para uma aula

scripts/            programas que se correm uma vez para gerar os resultados
  calcular_otimo.py   calcula as soluções ótimas (~17 min)
  comparar_metodos.py compara as heurísticas com o ótimo (~11 min)
  criar_exemplos.py   cria as 3 propostas de exemplo do item 5
  verificar.py        confirma as soluções sem usar o solver

data/               os dados do professor (horário e salas)
resultados/         o que os scripts calcularam e a app mostra
  solucoes.npz        a sala escolhida para cada aula, nas 3 soluções (formato compacto do NumPy)
  resumo.csv          os números de cada solução
  prova.csv           solução e limite inferior, dia a dia (a prova de que é ótima)
  comparacao_metodos.csv  resultados das heurísticas
exemplos/           3 propostas de alteração simuladas por nós (item 5)

docs/
  Relatorio_Horarios_ISCTE.docx   o relatório
  gestao_projeto.md               Scrum, backlog e Trello
  diagramas/                      diagramas UML (casos de uso, classes, sequência) e BPMN

.streamlit/         cores da app
.gitignore          ficheiros que o git ignora
```

## Limitações

- A garantia de ótimo vale para o número de aulas com problemas, com dias e horas fixos e os pressupostos do
  `GUIA.md` (secção 11).
- A preferência "mesma sala entre semanas" é resolvida por pesquisa local, sem prova de ótimo.
- As propostas em `exemplos/` são simuladas.

## Trabalho realizado por:
- Bernardo Encarnação nº123457
- Pedro Portugal nº122412
- Tomás Saraiva nº142847
