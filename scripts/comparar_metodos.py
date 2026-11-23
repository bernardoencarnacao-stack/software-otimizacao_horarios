"""Como sabemos que a solução é a melhor? Comparamos as heurísticas com o ÓTIMO provado pelo solver exato.

Todos os métodos têm o MESMO objetivo principal: menos problemas (sobrelotação + tipo de sala), com a mesma
regra obrigatória (a mesma aula num dia fica numa só sala). Comparamos só os problemas.

  Guloso                  - cada bloco na sala que tem hoje, ou na melhor sala livre
  Pesquisa local simples  - muda blocos de sala, mas só aceita mudanças que melhoram
  Pesquisa tabu           - aceita também mudanças piores e usa a lista tabu
  Algoritmo genético      - população de 30 soluções, cruzamento por dia da semana, mutação
  Solver exato            - programação inteira (calcular_otimo.py): solução ótima + prova

Cada heurística tem 60 segundos e corre com 3 sementes aleatórias.
Uso: python scripts/comparar_metodos.py   (~10 minutos; precisa de resultados/solucoes.npz)
"""
import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # trabalhar sempre a partir da pasta do projeto
sys.path.insert(0, os.getcwd())

import time

import numpy as np
import pandas as pd

from horarios import avaliar, dados, otimizar

SEGUNDOS, SEMENTES = 60, [0, 1, 2]

aulas, salas = dados.ler("data")
p = otimizar.Problema(aulas, salas)
x_guloso = otimizar.guloso(p)
PROBLEMAS = p.sobre + p.tipo


def problemas(x):
    return int(PROBLEMAS[p._todos, x].sum())


finais = []


def guardar(metodo, semente, x, historico, segundos):
    assert p.choques(x) == 0
    r = p.resultado(x)
    finais.append({"metodo": metodo, "semente": semente, "problemas": problemas(x), **r, "segundos": round(segundos, 1)})
    print(f"{metodo:24} semente {semente}: {problemas(x):5} problemas  {r}", flush=True)


guardar("Guloso", 0, x_guloso, [(0, 1000 * problemas(x_guloso)), (SEGUNDOS, 1000 * problemas(x_guloso))], 0)
for s in SEMENTES:
    t = time.perf_counter()
    x, h = otimizar.tabu(p, iteracoes=10**9, semente=s, x_inicial=x_guloso, segundos=SEGUNDOS, so_melhorias=True)
    guardar("Pesquisa local simples", s, x, h, time.perf_counter() - t)
    t = time.perf_counter()
    x, h = otimizar.tabu(p, iteracoes=10**9, semente=s, x_inicial=x_guloso, segundos=SEGUNDOS)
    guardar("Pesquisa tabu", s, x, h, time.perf_counter() - t)
    t = time.perf_counter()
    x, h = otimizar.genetico(p, segundos=SEGUNDOS, semente=s, x_inicial=x_guloso)
    guardar("Algoritmo genético", s, x, h, time.perf_counter() - t)

# o solver exato (já calculado por calcular_otimo.py)
x_otimo = np.load("resultados/solucoes.npz")["Ótima"]
rel = pd.read_csv("resultados/prova.csv")
tempo_exato = rel[rel["cenario"] == "Ótima"]["segundos"].sum()
guardar("Solver exato", 0, x_otimo, [(0, 1000 * problemas(x_otimo)), (tempo_exato, 1000 * problemas(x_otimo))],
        tempo_exato)

pd.DataFrame(finais).to_csv("resultados/comparacao_metodos.csv", index=False)
print(pd.DataFrame(finais).groupby("metodo", sort=False)[["problemas", "sobrelotadas", "tipo_errado", "mudancas"]].mean().round(0))
