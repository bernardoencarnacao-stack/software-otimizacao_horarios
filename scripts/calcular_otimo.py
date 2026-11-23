"""Calcula as soluções ótimas com o solver exato e grava-as em resultados/ (a app só as lê).

  Solução principal ("Ótima"):   1.º menos problemas (sobrelotação e tipo de sala contam igual)
                                  2.º preferência: a mesma sala de semana para semana
  Prioridades (extra opcional):  "Sobrelotação primeiro": 1.º sobrelotação, 2.º tipo de sala, 3.º mesma sala
                                  "Tipo de sala primeiro": 1.º tipo de sala, 2.º sobrelotação, 3.º mesma sala
  Sempre obrigatório: a mesma aula num dia (aulas seguidas ou sobrepostas do mesmo turno) fica numa só sala.

Uso: python scripts/calcular_otimo.py                             (todos os cenários; ~30 a 60 minutos)
     python scripts/calcular_otimo.py "Tipo de sala primeiro"     (só esse cenário; mantém os outros já gravados)
"""
import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # trabalhar sempre a partir da pasta do projeto
sys.path.insert(0, os.getcwd())

import numpy as np
import pandas as pd

from horarios import avaliar, dados, exato, otimizar

CENARIOS = {
    "Ótima": ("problemas",),
    "Sobrelotação primeiro": ("sobrelotadas", "tipo_errado"),
    "Tipo de sala primeiro": ("tipo_errado", "sobrelotadas"),
}

SEGUNDOS = 1200          # tempo máximo por fase e por dia
aulas, salas = dados.ler("data")
p = otimizar.Problema(aulas, salas)
escolhidos = sys.argv[1:] or list(CENARIOS)
solucoes, relatorios, resumo = {}, [], []
if sys.argv[1:] and os.path.exists("resultados/solucoes.npz"):      # manter os cenários que não se recalculam
    with np.load("resultados/solucoes.npz") as f:
        solucoes = {k: f[k] for k in f.files if k not in escolhidos}
    relatorios = [r for r in pd.read_csv("resultados/prova.csv").to_dict("records")
                  if r["cenario"] not in escolhidos]
    resumo = [r for r in pd.read_csv("resultados/resumo.csv").to_dict("records") if r["cenario"] not in escolhidos]

# Ponto de partida para o solver (só acelera; não muda o ótimo): uma solução da pesquisa tabu.
x_partida, _ = otimizar.tabu(p, segundos=60, iteracoes=10**9, semente=0)
for nome in escolhidos:
    ordem = CENARIOS[nome]
    print(f"\n=== {nome}: {' > '.join(ordem)} > mesma sala entre semanas", flush=True)
    x, rel = exato.resolver(p, ordem=ordem, segundos=SEGUNDOS, registo=lambda t: print(t, flush=True),
                            x_inicial=solucoes.get("Ótima", x_partida))
    antes = avaliar.avaliar(p.para_aulas(x), salas, aulas)["sala_varia"]
    x = otimizar.consolidar_semanas(p, x, max_passagens=50,
                                     problemas_juntos=ordem == ("problemas",))   # fase 2: mesma sala entre semanas
    print(f"mesma sala entre semanas: {antes} -> {avaliar.avaliar(p.para_aulas(x), salas, aulas)['sala_varia']} "
          "aulas fora da sala habitual", flush=True)
    assert p.choques(x) == 0, "a solução tem choques de sala"
    r = avaliar.avaliar(p.para_aulas(x), salas, aulas)
    assert r["choques_sala"] == 0 and r["sem_sala"] == 0
    solucoes[nome] = x
    relatorios += [{"cenario": nome, **linha} for linha in rel]
    resumo.append({"cenario": nome, **r, "problemas": r["sobrelotadas"] + r["tipo_errado"], "sala_varia_antes_fase2": antes})
    print(nome, resumo[-1], flush=True)

solucoes = {k: solucoes[k] for k in CENARIOS if k in solucoes}
resumo = sorted(resumo, key=lambda r: list(CENARIOS).index(r["cenario"]))
relatorios = sorted(relatorios, key=lambda r: list(CENARIOS).index(r["cenario"]))
np.savez_compressed("resultados/solucoes.npz", **solucoes)
pd.DataFrame(relatorios).to_csv("resultados/prova.csv", index=False)
pd.DataFrame(resumo).to_csv("resultados/resumo.csv", index=False)
print("feito")
