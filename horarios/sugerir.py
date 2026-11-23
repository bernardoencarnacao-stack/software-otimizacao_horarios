"""Item 4 - sugerir salas para UMA aula (existente ou nova), à mão do utilizador.

Dado um horário (por exemplo, a solução ótima), as ocorrências da aula (data, início, fim - todas as semanas e
aulas seguidas), os inscritos e o tipo de sala pedido, devolve as salas livres em TODAS essas ocorrências, ordenadas da mais adequada para a menos adequada:
  1.º menos problemas (tipo de sala errado e falta de lugares contam igual, como na solução ótima),
  2.º entre empatadas, a que desperdiça menos lugares (para não gastar salas grandes).
"""
import pandas as pd

from .avaliar import tipo_aceite


def salas_livres(horario, salas, ocorrencias, inscritos, pedida, ignorar_aulas=()):
    oc = pd.DataFrame(ocorrencias, columns=["data", "_ini", "_fim"])
    oc["data"] = pd.to_datetime(oc["data"])
    h = horario[horario["sala"].notna() & ~horario["aula_id"].isin(list(ignorar_aulas))]
    h = h[h["data"].isin(set(oc["data"]))].merge(oc, on="data")
    ocupadas = h[(h["ini_min"] < h["_fim"]) & (h["fim_min"] > h["_ini"])]["sala"].unique()
    existentes = set().union(*salas["caracteristicas"])
    s = salas[~salas["sala"].isin(ocupadas)].copy()
    s["tipo certo"] = [tipo_aceite(pedida, c, existentes) for c in s["caracteristicas"]]
    s["lugar para todos"] = s["capacidade"] >= inscritos
    s["lugares a mais"] = s["capacidade"] - inscritos
    s["folga"] = s["lugares a mais"].where(s["lugares a mais"] >= 0, 10**6 - s["lugares a mais"])
    s["problemas"] = (~s["tipo certo"]).astype(int) + (~s["lugar para todos"]).astype(int)
    s = s.sort_values(["problemas", "folga"])
    s["características"] = s["caracteristicas"].map(lambda c: ", ".join(sorted(x for x in c if "portal" not in x)))
    return s[["sala", "edificio", "capacidade", "lugares a mais", "tipo certo", "lugar para todos", "problemas",
              "características"]]
