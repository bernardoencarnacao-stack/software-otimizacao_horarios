# Guião da apresentação (~10 minutos, grupo todo)

Apresentem **com a app aberta**. Se a internet falhar, usem as imagens da app que estão no relatório.

| # | Quem | Tempo | O que dizer | O que mostrar |
|---|---|---|---|---|
| 1 | Elemento A | 1 min | Itens 4 (alocação de salas) e 5 (comparar propostas). Não mexemos em dias nem horas, só em salas. | Título da app |
| 2 | Elemento A | 1,5 min | O horário atual tem 1 013 aulas sem sala e 3 983 aulas com problemas (3 330 sobrelotadas + 653 em sala de tipo errado). Limpeza dos dados, incluindo os nomes de salas estragados pelo Excel. | Página 1 |
| 3 | Elemento B | 2 min | **Regra obrigatória: ninguém muda de sala a meio da aula** (aulas seguidas ou sobrepostas do mesmo turno no mesmo dia ficam na mesma sala); entre semanas pode mudar. **A pergunta da intercalar: quem define os pesos?** Primeiro usámos perfis de pesos e descobrimos dois problemas: eram arbitrários, e a pesquisa tabu dava soluções piores em tudo do que outras. Agora: sem pesos - menos aulas com problemas (os dois requisitos do enunciado, a contar igual); depois, só como preferência, a mesma sala entre semanas. | Página 2: texto do topo |
| 4 | Elemento B | 2 min | O modelo de programação inteira, em palavras: cada bloco numa sala; em cada sala e momento no máximo um bloco. O solver dá a solução **e a prova** (limite inferior). Resultado: **677, provado ótimo**, ninguém muda de sala a meio, e só 1 005 aulas (4%) mudam de sala numa semana (hoje: 1 299). Obrigar a mesma sala em todas as semanas custaria +155 problemas. Exemplo real: Cognição e Emoção, sextas 18-22, 33 alunos numa sala de 30 → 1E06 (50 lugares) nas duas aulas e em todas as semanas. | Página 2: caixa verde, "Ver a prova, dia a dia", tabela do que muda |
| 5 | Elemento C | 1,5 min | Porque não uma heurística: comparámos guloso, pesquisa local, tabu e genético com o ótimo. A melhor (tabu) fica 25% acima (846 contra 677). Os truques que tornaram o solver rápido: um dia de cada vez, salas iguais juntas. | Página 5 |
| 6 | Elemento D | 1,5 min | Item 5: cada pessoa envia um CSV; a app classifica com a mesma regra (utilizável → problemas → mudanças a meio → sala habitual). O exemplo 2 tem 263 choques. Carregar um CSV ao vivo. Mostrar também a página 3 (sugerir sala). | Páginas 4 e 3 |
| 7 | Elemento D | 0,5 min | Extra: prioridades. As três ordens têm o mesmo total (677); "Sobrelotação primeiro" tem zero aulas sobrelotadas. | Página 5 |

## Perguntas a fazer ao professor
1. A mancha horária padrão é 8h–20h sem sábados? E nos cursos pós-laborais?
2. "Sala/anfiteatro aulas" pode ir para uma sala de mestrado? O que é o "Lab ISTA"?
3. Para o ISCTE, sobrelotação e tipo de sala errado valem o mesmo? (Se não, a página 5 já tem as alternativas.)

Respostas às perguntas mais prováveis do professor: secção 13 do `GUIA.md`.
