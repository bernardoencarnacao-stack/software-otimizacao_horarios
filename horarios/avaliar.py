"""Como medimos a qualidade de um horário.

Um horário é a tabela de aulas (com data, hora e sala). Contamos, aula a aula:

  Problemas graves (tornam o horário impossível de usar):
    sem_sala      - a aula pede sala e não tem nenhuma
    choques_sala  - a aula está numa sala que, à mesma hora, já tem outra aula
  Problemas de qualidade (quanto menos, melhor):
    sobrelotadas  - há mais inscritos do que lugares na sala
    tipo_errado   - a sala não tem a característica pedida (ex.: laboratório)
    mudancas      - a aula mudou de sala ou de hora em relação ao horário atual
    fora_mancha   - começa antes das 8h, acaba depois das 20h ou é ao sábado
  Estabilidade da sala (o mesmo turno deve ficar na mesma sala):
    muda_a_meio   - aula que é continuação de outra do mesmo turno no mesmo dia (ex.: 18-20 e 20-22, ou horas
                    sobrepostas) mas está noutra sala. Na solução é proibido (regra obrigatória).
    sala_varia    - aula que não está na sala habitual da sua aula semanal (mesmo turno, dia da semana e
                    horário). Na solução é só uma preferência: mais vale mudar de semana para semana do que a meio.
"""
import pandas as pd

from .dados import SEM_SALA

INDICADORES = {
    "sem_sala": "Aulas sem sala",
    "choques_sala": "Choques de sala",
    "sobrelotadas": "Aulas sobrelotadas",
    "tipo_errado": "Sala de tipo errado",
    "mudancas": "Aulas mudadas",
    "fora_mancha": "Fora da mancha horária",
    "muda_a_meio": "Muda de sala a meio",
    "sala_varia": "Fora da sala habitual",
}
GRAVES = ["sem_sala", "choques_sala"]

# "Sala/anfiteatro aulas" é um pedido genérico: aceita qualquer uma destas características.
EQUIVALENTES = {"Sala/anfiteatro aulas": {"Sala de Aulas normal", "Anfiteatro aulas",
                                          "Sala Aulas Mestrado", "Sala Aulas Mestrado Plus"}}


def tipo_aceite(pedida, caracteristicas_da_sala, caracteristicas_existentes):
    """True se a sala serve para o tipo pedido.
    Pedidos que não existem no cadastro (ex.: "Lab ISTA") não se podem verificar: qualquer sala serve."""
    aceites = EQUIVALENTES.get(pedida, {pedida})
    if not aceites & caracteristicas_existentes:
        return True
    return bool(aceites & caracteristicas_da_sala)


def _juntar_intervalos(aulas, chave, encostadas):
    """Numera grupos de aulas com a mesma `chave` cujos horários se sobrepõem (ou, com encostadas=True,
    também as que começam exatamente quando a anterior acaba). Devolve um número por aula."""
    a = aulas.sort_values(chave + ["ini_min"])
    novo, fim_atual, chave_ant = [], -1, None
    for k, ini, fim in zip(zip(*[a[c] for c in chave]), a["ini_min"], a["fim_min"]):
        comeca = k != chave_ant or (ini > fim_atual if encostadas else ini >= fim_atual)
        novo.append(comeca)
        fim_atual = fim if comeca else max(fim_atual, fim)
        chave_ant = k
    return pd.Series(pd.Series(novo, index=a.index).cumsum().to_numpy() - 1, index=a.index).reindex(aulas.index)


def bloco_do_dia(aulas):
    """A MESMA AULA num dia: aulas do mesmo turno, na mesma data, seguidas (ex.: 18-20 e 20-22) ou com horas
    sobrepostas. Têm de ficar na mesma sala. Devolve o número do bloco de cada aula."""
    return _juntar_intervalos(aulas, ["turno", "data"], encostadas=True)


def serie_semanal(blocos):
    """A mesma aula de semana para semana: blocos do mesmo turno, no mesmo dia da semana, com horários que se
    sobrepõem (ex.: 18-20 na maioria das semanas e 18-19 numa). Preferimos (sem obrigar) que fiquem na mesma sala."""
    return _juntar_intervalos(blocos, ["turno", "dia_semana"], encostadas=False)


def marcar_choques(aulas):
    """True nas aulas que, no mesmo dia e na mesma sala, se sobrepõem a outra aula."""
    a = aulas[aulas["sala"].notna()].sort_values(["sala", "data", "ini_min"])
    grupo = [a["sala"], a["data"]]
    fim_anteriores = a.groupby(grupo)["fim_min"].cummax().groupby(grupo).shift()   # maior fim até à aula anterior
    inicio_seguinte = a.groupby(grupo)["ini_min"].shift(-1)
    choque = (a["ini_min"] < fim_anteriores) | (a["fim_min"] > inicio_seguinte)
    return choque.reindex(aulas.index, fill_value=False).astype(bool)


def problemas_por_aula(aulas, salas, base=None):
    """Tabela com uma coluna True/False por indicador, para cada aula."""
    capacidade = salas.set_index("sala")["capacidade"]
    caract = salas.set_index("sala")["caracteristicas"]
    existentes = set().union(*salas["caracteristicas"])
    precisa = aulas["pedida"] != SEM_SALA
    tem_sala = aulas["sala"].notna()

    tipo_ok = pd.Series(True, index=aulas.index)
    for (pedida, sala), idx in aulas[precisa & tem_sala].groupby(["pedida", "sala"]).groups.items():
        tipo_ok[idx] = tipo_aceite(pedida, caract[sala], existentes)

    p = pd.DataFrame(index=aulas.index)
    p["sem_sala"] = precisa & ~tem_sala
    p["choques_sala"] = marcar_choques(aulas)
    p["sobrelotadas"] = precisa & tem_sala & (aulas["inscritos"] > aulas["sala"].map(capacidade))
    p["tipo_errado"] = precisa & tem_sala & ~tipo_ok
    if base is None:
        p["mudancas"] = False
    else:
        # Dar sala a uma aula que não tinha não conta como mudança (ninguém tem de mudar de hábitos).
        b = base.set_index("aula_id").loc[aulas["aula_id"]]
        mudou = ((b["sala"].notna().to_numpy() & (aulas["sala"].fillna("-").to_numpy() != b["sala"].fillna("-").to_numpy()))
                 | (aulas["data"].to_numpy() != b["data"].to_numpy())
                 | (aulas["ini_min"].to_numpy() != b["ini_min"].to_numpy()))
        p["mudancas"] = precisa & mudou
    # estabilidade da sala (só aulas com sala)
    c = aulas[precisa & tem_sala].copy()
    c["bloco"] = bloco_do_dia(c)
    c = c.sort_values(["bloco", "ini_min"])
    p["muda_a_meio"] = (c["bloco"].eq(c["bloco"].shift()) & c["sala"].ne(c["sala"].shift())
                        ).reindex(aulas.index, fill_value=False).astype(bool)
    b = c.groupby("bloco").agg(turno=("turno", "first"), dia_semana=("dia_semana", "first"),
                               ini_min=("ini_min", "min"), fim_min=("fim_min", "max"))
    c["serie"] = c["bloco"].map(serie_semanal(b))
    habitual = c.groupby("serie")["sala"].transform(lambda v: v.mode().iloc[0])
    p["sala_varia"] = (c["sala"] != habitual).reindex(aulas.index, fill_value=False).astype(bool)
    p["fora_mancha"] = (aulas["ini_min"] < 8 * 60) | (aulas["fim_min"] > 20 * 60) | (aulas["data"].dt.dayofweek == 5)
    return p


def avaliar(aulas, salas, base=None):
    """Resumo: quantas aulas têm cada problema."""
    p = problemas_por_aula(aulas, salas, base)
    r = {k: int(p[k].sum()) for k in INDICADORES}
    r["utilizavel"] = r["sem_sala"] == 0 and r["choques_sala"] == 0
    return r


def aplicar_alteracoes(base, alteracoes):
    """Aplica um ficheiro de alterações ao horário base.
    Colunas: aula_id ; nova_sala ; nova_data (AAAA-MM-DD) ; novo_inicio (HH:MM) ; novo_fim (HH:MM)
    Só aula_id é obrigatória; células vazias = não mudar. nova_sala = "-" retira a sala."""
    a = base.copy().set_index("aula_id", drop=False)
    para_min = lambda t: int(str(t).split(":")[0]) * 60 + int(str(t).split(":")[1])
    for linha in alteracoes.to_dict("records"):
        i = int(linha["aula_id"])
        if pd.notna(linha.get("nova_sala")):
            a.at[i, "sala"] = None if linha["nova_sala"] == "-" else linha["nova_sala"]
        if pd.notna(linha.get("nova_data")):
            a.at[i, "data"] = pd.Timestamp(linha["nova_data"])
        if pd.notna(linha.get("novo_inicio")):
            a.at[i, "ini_min"] = para_min(linha["novo_inicio"])
        if pd.notna(linha.get("novo_fim")):
            a.at[i, "fim_min"] = para_min(linha["novo_fim"])
    return a.reset_index(drop=True)


def ficheiro_de_alteracoes(base, nova):
    """O contrário de aplicar_alteracoes: gera o ficheiro que transforma `base` em `nova`."""
    b, n = base.set_index("aula_id"), nova.set_index("aula_id")
    mudou = ((b["sala"].fillna("-") != n["sala"].fillna("-")) | (b["data"] != n["data"])
             | (b["ini_min"] != n["ini_min"]) | (b["fim_min"] != n["fim_min"]))
    n = n[mudou]
    hhmm = lambda m: f"{m // 60:02d}:{m % 60:02d}"
    return pd.DataFrame({"aula_id": n.index, "nova_sala": n["sala"].fillna("-").to_numpy(),
                         "nova_data": n["data"].dt.strftime("%Y-%m-%d").to_numpy(),
                         "novo_inicio": [hhmm(m) for m in n["ini_min"]],
                         "novo_fim": [hhmm(m) for m in n["fim_min"]]})
