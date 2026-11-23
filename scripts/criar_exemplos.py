"""Cria 3 propostas de alteração SIMULADAS por nós, para testar a comparação de propostas (item 5).

  exemplos/exemplo1_gabinete_espacos.csv   - o gabinete dá sala às aulas que não têm
  exemplos/exemplo2_coordenacao_curso.csv  - uma coordenação pede salas maiores (mas só verifica a 1.ª semana)
  exemplos/exemplo3_docentes_sabado.csv    - os docentes passam as aulas de sábado para sexta-feira

Uso: python scripts/criar_exemplos.py   (~10 segundos)
"""
import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # trabalhar sempre a partir da pasta do projeto
sys.path.insert(0, os.getcwd())

from collections import defaultdict

import pandas as pd

from horarios import avaliar, dados
from horarios.dados import SEM_SALA

aulas, salas = dados.ler("data")

# ------------------------------------------------------------------ item 5: propostas de exemplo
capacidade = salas.set_index("sala")["capacidade"]
caract = salas.set_index("sala")["caracteristicas"]
existentes = set().union(*salas["caracteristicas"])


def ocupacao(horario):
    oc = defaultdict(list)
    for a in horario[horario["sala"].notna()].itertuples():
        oc[(a.sala, a.data)].append((a.ini_min, a.fim_min, a.aula_id))
    return oc


def livre(oc, sala, data, ini, fim, ignorar=None):
    return all(fim <= i or ini >= f for i, f, aid in oc[(sala, data)] if aid != ignorar)


def salas_por_preferencia(pedida, inscritos):
    """Salas do tipo pedido, primeiro as que têm lugar para todos (da mais pequena para a maior)."""
    ok = [s for s in salas["sala"] if avaliar.tipo_aceite(pedida, caract[s], existentes) and pd.notna(capacidade[s])]
    cabem = sorted([s for s in ok if capacidade[s] >= inscritos], key=lambda s: capacidade[s])
    return cabem + sorted([s for s in ok if capacidade[s] < inscritos], key=lambda s: -capacidade[s])


# Exemplo 1 - Gabinete de espaços: dá sala às aulas que não têm (verifica sempre a ocupação).
ex1 = aulas.copy()
oc = ocupacao(ex1)
for a in ex1[(ex1.pedida != SEM_SALA) & ex1.sala.isna()].sort_values("inscritos", ascending=False).itertuples():
    for s in salas_por_preferencia(a.pedida, a.inscritos) + list(salas["sala"]):
        if livre(oc, s, a.data, a.ini_min, a.fim_min):
            ex1.at[a.Index, "sala"] = s
            oc[(s, a.data)].append((a.ini_min, a.fim_min, a.aula_id))
            break

# Exemplo 2 - Coordenação de curso: pede salas maiores para as aulas sobrelotadas do seu curso,
# mas só confirma que a sala está livre na 1.ª semana e aplica a mudança ao semestre todo.
problemas = avaliar.problemas_por_aula(ex1, salas)
curso = ex1[problemas["sobrelotadas"]]["curso"].value_counts().index[0]
ex2 = ex1.copy()
oc = ocupacao(ex2)
for turno, g in ex1[problemas["sobrelotadas"] & (ex1.curso == curso)].groupby("turno"):
    primeira = g.sort_values("data").iloc[0]
    for s in salas_por_preferencia(primeira.pedida, primeira.inscritos):
        if capacidade[s] >= primeira.inscritos and livre(oc, s, primeira.data, primeira.ini_min, primeira.fim_min):
            ex2.loc[g.index, "sala"] = s
            break

# Exemplo 3 - Docentes: passam as aulas de sábado para sexta-feira à mesma hora (verificam a sala).
ex3 = ex1.copy()
oc = ocupacao(ex3)
for a in ex3[ex3.data.dt.dayofweek == 5].itertuples():
    sexta = a.data - pd.Timedelta(days=1)
    ex3.at[a.Index, "data"] = sexta
    if a.pedida == SEM_SALA:
        continue
    opcoes = ([a.sala] if pd.notna(a.sala) else []) + salas_por_preferencia(a.pedida, a.inscritos) + list(salas["sala"])
    nova = next((s for s in opcoes if livre(oc, s, sexta, a.ini_min, a.fim_min, a.aula_id)), None)
    ex3.at[a.Index, "sala"] = nova
    if nova:
        oc[(nova, sexta)].append((a.ini_min, a.fim_min, a.aula_id))

for nome, horario in [("exemplo1_gabinete_espacos", ex1), ("exemplo2_coordenacao_curso", ex2),
                      ("exemplo3_docentes_sabado", ex3)]:
    alt = avaliar.ficheiro_de_alteracoes(aulas, horario)
    alt.to_csv(f"exemplos/{nome}.csv", index=False)
    print(f"{nome}: {len(alt)} alterações", avaliar.avaliar(horario, salas, aulas))
print("curso usado no exemplo 2:", curso)
