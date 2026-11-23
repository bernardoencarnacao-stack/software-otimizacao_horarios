"""Leitura e limpeza dos dois ficheiros do professor.

data/horario.csv -> uma linha por aula (cada semana conta como uma aula diferente)
data/salas.csv   -> uma linha por sala, com capacidade e características marcadas com "X"
"""
import re

import pandas as pd

SEM_SALA = "Não necessita de sala"


def reparar_nome(nome):
    """O Excel leu salas como "1E02" (Edifício Sedas Nunes, piso 1, sala E02) como números em notação
    científica e gravou-as como "1,00E+02". Repomos o nome original: "1,00E+02" -> "1E02"."""
    if isinstance(nome, str):
        return re.sub(r"^(\d),00E\+(\d\d)$", r"\1E\2", nome)
    return nome


def ler_salas(caminho="data/salas.csv"):
    s = pd.read_csv(caminho, sep=";", encoding="utf-8-sig")
    colunas_fixas = ["Edifício", "Nome sala", "Capacidade Normal", "Capacidade Exame", "Nº características"]
    colunas_caract = [c for c in s.columns if c not in colunas_fixas]
    salas = pd.DataFrame({
        "sala": s["Nome sala"].map(reparar_nome),
        "edificio": s["Edifício"],
        "capacidade": s["Capacidade Normal"],
        # conjunto das características que têm "X" nessa sala
        "caracteristicas": [frozenset(c for c in colunas_caract if pd.notna(linha[c])) for _, linha in s.iterrows()],
    })
    return salas


def ler_horario(caminho="data/horario.csv"):
    h = pd.read_csv(caminho, sep=";", encoding="utf-8-sig")
    h.columns = ["curso", "uc", "turno", "turma", "inscritos", "dia_semana", "inicio", "fim",
                 "dia", "pedida", "sala", "lotacao", "caract_reais"]
    h = h.drop_duplicates()                 # 3 linhas repetidas
    h = h.dropna(subset=["dia"])            # 13 aulas sem data não podem ir para o calendário
    h["data"] = pd.to_datetime(h["dia"], format="%d/%m/%Y")
    h["ini_min"] = (pd.to_timedelta(h["inicio"]).dt.total_seconds() // 60).astype(int)   # 09:30 -> 570
    h["fim_min"] = (pd.to_timedelta(h["fim"]).dt.total_seconds() // 60).astype(int)
    h["pedida"] = h["pedida"].fillna(SEM_SALA)
    h["sala"] = h["sala"].map(reparar_nome)
    h = h.reset_index(drop=True)
    h.insert(0, "aula_id", range(len(h)))   # identificador único de cada aula
    return h.drop(columns=["dia", "lotacao", "caract_reais"])


def ler(pasta="data"):
    """Devolve (aulas, salas). A sala 0S08 é usada no horário mas não está no cadastro:
    acrescentamo-la com a lotação e as características que o próprio horário indica."""
    salas = ler_salas(f"{pasta}/salas.csv")
    bruto = pd.read_csv(f"{pasta}/horario.csv", sep=";", encoding="utf-8-sig")
    aulas = ler_horario(f"{pasta}/horario.csv")
    caract_conhecidas = set().union(*salas["caracteristicas"])
    for nome in sorted(set(aulas["sala"].dropna()) - set(salas["sala"])):
        linhas = bruto[bruto["Sala da aula"] == nome]
        caract = set()
        for txt in linhas["Características reais da sala"].dropna().unique():
            caract |= {c.strip() for c in txt.split(",")}
        salas.loc[len(salas)] = [nome, "(fora do cadastro)", linhas["Lotação"].max(),
                                 frozenset(caract & caract_conhecidas)]
    return aulas, salas
