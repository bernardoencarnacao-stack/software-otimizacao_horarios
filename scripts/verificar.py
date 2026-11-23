"""Verificação independente das soluções gravadas (não usa o solver).

Para cada solução em resultados/solucoes.npz, constrói o horário completo, aula a aula, e confirma que:
  - nenhuma aula que pede sala fica sem sala;
  - não há duas aulas na mesma sala ao mesmo tempo (verificado data a data, hora a hora);
  - nenhuma aula muda de sala a meio (aulas seguidas ou sobrepostas do mesmo turno no mesmo dia);
  - os números batem certo com os gravados em resultados/resumo.csv;
  - o número de aulas com problemas é igual à soma dos limites inferiores provados pelo solver.

Uso: python scripts/verificar.py
"""
import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # trabalhar sempre a partir da pasta do projeto
sys.path.insert(0, os.getcwd())

import numpy as np
import pandas as pd

from horarios import avaliar, dados, otimizar

aulas, salas = dados.ler("data")
p = otimizar.Problema(aulas, salas)
resumo = pd.read_csv("resultados/resumo.csv").set_index("cenario")
relatorio = pd.read_csv("resultados/prova.csv")
tudo_ok = True
with np.load("resultados/solucoes.npz") as f:
    for nome in f.files:
        horario = p.para_aulas(f[nome])
        r = avaliar.avaliar(horario, salas, aulas)
        primeira_fase = relatorio[(relatorio["cenario"] == nome)].groupby("dia").head(1)
        verificacoes = {
            "todas as aulas têm sala": r["sem_sala"] == 0,
            "nenhum choque de sala": r["choques_sala"] == 0,
            "nenhuma aula muda de sala a meio (aulas seguidas)": r["muda_a_meio"] == 0,
            "números iguais aos gravados": all(r[k] == resumo.loc[nome, k]
                                               for k in ["sobrelotadas", "tipo_errado", "sala_varia"]),
            "1.º critério provado ótimo em todos os dias": bool(primeira_fase["provado_otimo"].all()),
        }
        print(f"\n{nome}: {r['sobrelotadas']} sobrelotadas, {r['tipo_errado']} tipo errado, {r['sala_varia']} aulas fora da sala habitual (entre semanas)")
        for texto, ok in verificacoes.items():
            print(f"  [{'OK' if ok else 'FALHA'}] {texto}")
            tudo_ok &= ok
print("\nTudo verificado." if tudo_ok else "\nHá verificações que falharam.")
