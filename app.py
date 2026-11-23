"""Aplicação web: Gestão de horários do ISCTE (itens 4 e 5).

Correr:  streamlit run app.py
As soluções ótimas já estão calculadas em resultados/ (para recalcular: python scripts/calcular_otimo.py).
"""
import io

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from horarios import avaliar, dados, otimizar, sugerir
from horarios.avaliar import INDICADORES

st.set_page_config(page_title="Horários ISCTE", page_icon="🗓️", layout="wide")
DIAS = {"Seg": "Segunda", "Ter": "Terça", "Qua": "Quarta", "Qui": "Quinta", "Sex": "Sexta", "Sáb": "Sábado"}
AZUL, AZUL_ESCURO, VERDE, LARANJA, AMARELO, ROXO = "#2a78d6", "#1f3864", "#1baf7a", "#eb6834", "#eda100", "#7b61c9"

# ---------------------------------------------------------------------------- estilo (cores)
st.markdown(f"""
<style>
.banner {{background: linear-gradient(120deg, {AZUL_ESCURO} 0%, {AZUL} 70%, #4fa3e8 100%); color: white;
          padding: 26px 32px; border-radius: 16px; margin-bottom: 8px;}}
.banner h1 {{color: white; margin: 0; padding: 0; font-size: 2.1rem;}}
.banner p {{color: #dbe8fb; margin: 6px 0 0 0; font-size: 1rem;}}
.cartao {{background: white; border: 1px solid #e3e8f0; border-left: 6px solid var(--cor); border-radius: 12px;
          padding: 14px 18px; box-shadow: 0 1px 3px rgba(31,56,100,.06); height: 100%;}}
.cartao .t {{color: #5b6478; font-size: .9rem;}}
.cartao .v {{color: {AZUL_ESCURO}; font-size: 2rem; font-weight: 700; line-height: 1.2;}}
.cartao .d {{font-size: .85rem; font-weight: 600; color: {VERDE};}}
.caixa {{background: var(--fundo); border-radius: 12px; padding: 16px 20px; height: 100%;}}
.caixa h4 {{margin: 0 0 6px 0; color: var(--cor);}}
.caixa p, .caixa li {{color: #2b3242; font-size: .95rem; margin-bottom: 2px;}}
.antes-depois {{font-size: 1.6rem; font-weight: 700; color: {AZUL_ESCURO};}}
.antes-depois s {{color: #a0a7b4; font-weight: 500;}}
.stTabs [data-baseweb="tab"] {{font-weight: 600; font-size: 1rem;}}
h3 {{color: {AZUL_ESCURO};}}
</style>
""", unsafe_allow_html=True)


def fmt(n):
    return f"{int(n):,}".replace(",", " ")


def hhmm(m):
    return f"{int(m) // 60:02d}:{int(m) % 60:02d}"


def cartao(col, titulo, valor, cor, delta=None):
    d = (f'<div class="d" style="color:{VERDE if delta < 0 else LARANJA}">{"▼" if delta < 0 else "▲"} '
         f'{fmt(abs(delta))} face ao atual</div>') if delta else ""
    col.markdown(f'<div class="cartao" style="--cor:{cor}"><div class="t">{titulo}</div>'
                 f'<div class="v">{valor}</div>{d}</div>', unsafe_allow_html=True)


def caixa(col, titulo, html, cor, fundo):
    col.markdown(f'<div class="caixa" style="--cor:{cor};--fundo:{fundo}"><h4>{titulo}</h4>{html}</div>',
                 unsafe_allow_html=True)


# ---------------------------------------------------------------------------- dados e soluções (carregados uma vez)
@st.cache_resource(show_spinner="A carregar os dados...")
def carregar():
    aulas, salas = dados.ler("data")
    p = otimizar.Problema(aulas, salas)
    with np.load("resultados/solucoes.npz") as f:
        solucoes = {nome: p.para_aulas(f[nome]) for nome in f.files}
    prova = pd.read_csv("resultados/prova.csv")
    metodos = pd.read_csv("resultados/comparacao_metodos.csv")
    return aulas, salas, p, solucoes, prova, metodos


aulas, salas, p, solucoes, prova, metodos = carregar()
otimo_h = solucoes["Ótima"]


@st.cache_data(show_spinner=False)
def indicadores(chave, _horario):
    r = avaliar.avaliar(_horario, salas, aulas)
    r["problemas"] = r["sobrelotadas"] + r["tipo_errado"]
    return r


atual = indicadores("atual", aulas)
otima = indicadores("Ótima", otimo_h)


@st.cache_data(show_spinner=False)
def aulas_semanais():
    """Uma linha por aula semanal (mesmo turno, dia da semana e horário), com a sala na solução ótima."""
    oc = (p.aula_bloco.assign(serie=p.serie[p.aula_bloco["bloco"].to_numpy()])
          .merge(otimo_h[["aula_id", "sala"]], on="aula_id"))
    se = p.blocos.assign(serie=p.serie).groupby("serie").agg(
        curso=("curso", "first"), uc=("uc", "first"), turno=("turno", "first"), dia_semana=("dia_semana", "first"),
        ini=("ini_min", "min"), fim=("fim_min", "max"), inscritos=("inscritos", "first"), pedida=("pedida", "first"))
    se["dia"] = se["dia_semana"].map(DIAS).fillna(se["dia_semana"])
    se["horas"] = se["ini"].map(hhmm) + "–" + se["fim"].map(hhmm)
    se["sala"] = oc.groupby("serie")["sala"].agg(lambda v: ", ".join(v.dropna().unique()))
    return se, oc


st.markdown('<div class="banner"><h1>🗓️ Gestão de horários do ISCTE</h1>'
            '<p>Projeto 1 · Otimização e Decisão em Engenharia de Software · Item 4 (alocação de salas) e '
            'item 5 (comparação de propostas)</p></div>', unsafe_allow_html=True)

pag1, pag2, pag3, pag4, pag5 = st.tabs(["🏠 Início", "✅ Solução ótima", "🔎 Sugerir sala",
                                        "⚖️ Comparar propostas", "🧪 Métodos"])

# ============================================================================ 1. INÍCIO
with pag1:
    st.subheader("O que fizemos")
    st.write("Partimos do horário de exemplo do ISCTE (dias e horas já marcados) e tratámos de duas perguntas: "
             "**em que sala deve ficar cada aula?** e **como comparar propostas de alteração de várias pessoas?**")
    c1, c2, c3 = st.columns(3)
    caixa(c1, "Item 4 · Alocação de salas",
          "<p>Calculámos a <b>melhor alocação de salas possível</b>, tendo em conta os inscritos e o tipo de sala, "
          "com <b>prova</b> de que não há melhor. Também sugerimos salas para uma aula concreta.</p>"
          "<p>👉 páginas <b>Solução ótima</b> e <b>Sugerir sala</b></p>", AZUL, "#eaf2fc")
    caixa(c2, "Item 5 · Comparar propostas",
          "<p>Cada pessoa propõe alterações num ficheiro CSV. A app aplica-as e <b>ordena as propostas</b> com o "
          "mesmo critério, sem pesos, e explica porque é que uma proposta não serve.</p>"
          "<p>👉 página <b>Comparar propostas</b></p>", VERDE, "#e6f6ef")
    caixa(c3, "Como · Solver exato",
          "<p>Programação inteira com o solver <b>HiGHS</b>. Comparámos com quatro heurísticas: a melhor fica "
          "25% acima do ótimo.</p><p>👉 página <b>Métodos</b></p>", ROXO, "#f1edfb")

    st.markdown("&nbsp;")
    st.markdown("**As regras, sem pesos**")
    st.markdown("""
1. **Obrigatório:** ninguém muda de sala a meio da aula (aulas seguidas ou sobrepostas do mesmo turno, no mesmo dia,
   ficam na mesma sala).
2. **Objetivo:** o menor número de **aulas com problemas** - sobrelotadas ou em sala de tipo errado (contam igual).
3. **Preferência:** sem piorar o objetivo, a mesma sala de semana para semana.
""")
    st.markdown("**O resultado**")
    c = st.columns(3)
    for col, titulo, a, d, cor in [(c[0], "Aulas com problemas", atual["problemas"], otima["problemas"], AZUL),
                                   (c[1], "Aulas sem sala", atual["sem_sala"], otima["sem_sala"], LARANJA),
                                   (c[2], "Aulas que mudam de sala a meio", atual["muda_a_meio"], otima["muda_a_meio"], VERDE)]:
        col.markdown(f'<div class="cartao" style="--cor:{cor}"><div class="t">{titulo}</div>'
                     f'<div class="antes-depois"><s>{fmt(a)}</s> → {fmt(d)}</div></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Como está o horário atual")
    c = st.columns(4)
    cartao(c[0], "Aulas (cada semana conta uma)", fmt(len(aulas)), AZUL)
    cartao(c[1], "Aulas sem sala", fmt(atual["sem_sala"]), LARANJA)
    cartao(c[2], "Aulas sobrelotadas", fmt(atual["sobrelotadas"]), AMARELO)
    cartao(c[3], "Sala de tipo errado", fmt(atual["tipo_errado"]), ROXO)
    st.write("")
    st.write(f"No total, **{fmt(atual['problemas'])} aulas com problemas** (sobrelotadas ou em sala de tipo errado) "
             f"e {fmt(atual['sem_sala'])} aulas sem sala.")

    problemas = avaliar.problemas_por_aula(aulas, salas)
    c1, c2 = st.columns(2)
    indicador = c1.selectbox("Problema", ["sobrelotadas", "tipo_errado", "sem_sala"], format_func=INDICADORES.get)
    lista = aulas[problemas[indicador]]
    curso = c2.selectbox("Curso", ["(todos)"] + sorted(lista["curso"].unique()))
    if curso != "(todos)":
        lista = lista[lista["curso"] == curso]
    lista = lista.assign(capacidade=lista["sala"].map(salas.set_index("sala")["capacidade"]),
                         data=lista["data"].dt.strftime("%Y-%m-%d"))
    st.dataframe(lista[["curso", "uc", "turno", "data", "inicio", "fim", "inscritos", "sala", "capacidade", "pedida"]],
                 hide_index=True, width="stretch", height=380)
    st.caption(f"{fmt(len(lista))} aulas. Dados limpos: 3 linhas repetidas e 13 aulas sem data removidas; nomes de "
               "salas estragados pelo Excel (ex.: \"1,00E+02\" → 1E02) corrigidos.")

# ============================================================================ 2. SOLUÇÃO ÓTIMA
with pag2:
    st.subheader("A melhor alocação de salas possível")
    st.markdown("""
- Os dias e as horas ficam iguais; só mudam as **salas**.
- **Regra obrigatória:** ninguém muda de sala a meio da aula.
- **Objetivo:** o menor número de **aulas com problemas** (sobrelotada ou sala de tipo errado contam igual). Depois,
  sem piorar isto, a mesma sala de semana para semana sempre que possível.
""")
    rel = prova[(prova["cenario"] == "Ótima") & (prova["fase"] == "problemas")]
    if rel["provado_otimo"].all():
        st.success(f"**Provado ótimo:** não existe nenhuma alocação com menos de **{fmt(otima['problemas'])}** aulas "
                   f"com problemas (hoje são {fmt(atual['problemas'])}).", icon="✅")

    c = st.columns(4)
    for col, k, nome, cor in zip(c, ["problemas", "sobrelotadas", "tipo_errado", "sem_sala"],
                                 ["Aulas com problemas", "Aulas sobrelotadas", "Sala de tipo errado", "Aulas sem sala"],
                                 [AZUL, AMARELO, ROXO, LARANJA]):
        cartao(col, nome, fmt(otima[k]), cor, otima[k] - atual[k])
    st.caption(f"Mudam de sala a meio: {otima['muda_a_meio']} (hoje {atual['muda_a_meio']}). Fora da sala habitual "
               f"numa semana: {fmt(otima['sala_varia'])} (hoje {fmt(atual['sala_varia'])}).")

    with st.expander("Ver a prova, dia a dia"):
        st.write("O solver devolve a solução e um **limite inferior** (abaixo dele é impossível descer). "
                 "Quando os dois são iguais, a solução é a melhor possível.")
        st.dataframe(rel.assign(dia=rel["dia"].map(DIAS))[["dia", "valor", "limite_inferior", "provado_otimo"]]
                     .rename(columns={"valor": "aulas com problemas", "limite_inferior": "limite inferior",
                                      "provado_otimo": "provado ótimo?"}), hide_index=True, width="stretch")

    exp = otimo_h.drop(columns=["ini_min", "fim_min"]).assign(data=otimo_h["data"].dt.strftime("%Y-%m-%d"))
    st.download_button("⬇️ Descarregar o horário otimizado (CSV)", exp.to_csv(index=False, sep=";"),
                       file_name="horario_otimo.csv", mime="text/csv", type="primary")

    st.divider()
    st.subheader("Extra: e se um problema for mais importante do que o outro?")
    st.write("A solução principal conta sobrelotação e tipo de sala por igual. Calculámos também as soluções ótimas "
             "para as duas ordens de prioridade possíveis. Cada uma é provada ótima para a sua ordem.")
    ordem = {"Ótima": ("Principal", "os dois contam igual", AZUL),
             "Sobrelotação primeiro": ("Sobrelotação primeiro", "1.º sobrelotação, 2.º tipo de sala", AMARELO),
             "Tipo de sala primeiro": ("Tipo de sala primeiro", "1.º tipo de sala, 2.º sobrelotação", ROXO)}
    c = st.columns(3)
    for col, (k, (titulo, desc, cor)) in zip(c, ordem.items()):
        r = indicadores(k, solucoes[k])
        col.markdown(f'<div class="cartao" style="--cor:{cor}"><div class="t">{desc}</div>'
                     f'<div class="v" style="font-size:1.3rem">{titulo}</div>'
                     f'<div class="t">{fmt(r["problemas"])} aulas com problemas: <b>{fmt(r["sobrelotadas"])}</b> '
                     f'sobrelotadas + <b>{fmt(r["tipo_errado"])}</b> tipo errado</div></div>', unsafe_allow_html=True)
    st.write("")
    st.info("As três têm o **mesmo total**; só muda a divisão. É possível ter **zero aulas sobrelotadas** sem "
            "aumentar o total de problemas, à custa de mais aulas em sala de tipo errado. Quem decide escolhe.",
            icon="💡")

# ============================================================================ 3. SUGERIR SALA
with pag3:
    st.subheader("Sugerir sala para uma aula")
    st.write("Escolham uma aula que já existe ou descrevam uma aula nova. A app mostra as salas **livres em todas as "
             "semanas** dessa aula (segundo a solução ótima), da mais adequada para a menos adequada.")
    se, oc = aulas_semanais()
    modo = st.radio("Que aula?", ["Aula existente", "Aula nova"], horizontal=True)
    if modo == "Aula existente":
        c1, c2, c3 = st.columns(3)
        curso_s = c1.selectbox("Curso", sorted(se["curso"].unique()), key="sug_curso")
        b = se[se["curso"] == curso_s]
        uc_s = c2.selectbox("Unidade curricular", sorted(b["uc"].unique()), key="sug_uc")
        b = b[b["uc"] == uc_s]
        rotulo = {i: f"{r.turno} · {r.dia} {r.horas} · {r.inscritos} inscritos" for i, r in b.iterrows()}
        serie = c3.selectbox("Turno e horário", list(rotulo), format_func=rotulo.get)
        ids = oc.loc[oc["serie"] == serie, "aula_id"]
        minhas = otimo_h[otimo_h["aula_id"].isin(ids)]
        ocorrencias = list(zip(minhas["data"], minhas["ini_min"], minhas["fim_min"]))
        inscritos, pedida, ignorar = se.loc[serie, "inscritos"], se.loc[serie, "pedida"], ids
        st.caption(f"Tipo pedido: **{pedida}** · {len(ocorrencias)} aulas · sala na solução ótima: "
                   f"**{se.loc[serie, 'sala']}**")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        dia_s = c1.selectbox("Dia", list(DIAS)[:5], format_func=DIAS.get)
        ini_t = c2.time_input("Início", value=pd.Timestamp("2022-01-01 09:30").time(), step=1800)
        fim_t = c3.time_input("Fim", value=pd.Timestamp("2022-01-01 11:00").time(), step=1800)
        inscritos = c4.number_input("Inscritos", min_value=1, value=40)
        tipos = sorted(set(aulas["pedida"]) - {"Não necessita de sala"})
        pedida = c5.selectbox("Tipo de sala", tipos, index=tipos.index("Sala/anfiteatro aulas"))
        ini, fim = ini_t.hour * 60 + ini_t.minute, fim_t.hour * 60 + fim_t.minute
        semanas = pd.date_range("2022-09-12", "2022-12-16")
        ocorrencias = [(d, ini, fim) for d in semanas[semanas.dayofweek == list(DIAS).index(dia_s)]] if fim > ini else []
        ignorar = []
        st.caption(f"1.º semestre (12/09 a 16/12/2022): {len(ocorrencias)} semanas")

    if not ocorrencias:
        st.warning("Verifiquem as horas.")
    else:
        sug = sugerir.salas_livres(otimo_h, salas, ocorrencias, inscritos, pedida, ignorar)
        if sug.empty:
            st.error("Nenhuma sala está livre em todas essas semanas a essa hora.")
        else:
            boas = int((sug["problemas"] == 0).sum())
            st.write(f"**{len(sug)} salas livres**, das quais **{boas}** sem nenhum problema.")
            st.dataframe(sug.head(15), hide_index=True, width="stretch")

# ============================================================================ 4. COMPARAR PROPOSTAS
with pag4:
    st.subheader("Comparar propostas de vários utilizadores")
    st.markdown("""
Cada utilizador propõe alterações num **ficheiro CSV** com as colunas `aula_id, nova_sala, nova_data, novo_inicio,
novo_fim` (células vazias = não mudar). A app aplica cada proposta ao horário e ordena-as com a mesma regra, sem pesos:
**1.º** utilizável (sem aulas sem sala nem choques) → **2.º** menos aulas com problemas → **3.º** menos mudanças de sala
a meio → **4.º** menos aulas fora da sala habitual.
""")
    c1, c2 = st.columns(2)
    ficheiros = c1.file_uploader("Carregar propostas (CSV)", type="csv", accept_multiple_files=True)
    exemplos = c2.checkbox("Incluir as 3 propostas de exemplo (simuladas por nós)", value=True)
    prioridades = c2.checkbox("Incluir as soluções com prioridades (página Solução ótima)", value=False)

    variantes = {"Horário atual": aulas, "Solução ótima": otimo_h}
    if prioridades:
        for nome in ["Sobrelotação primeiro", "Tipo de sala primeiro"]:
            variantes[f"Prioridade: {nome.lower()}"] = solucoes[nome]
    if exemplos:
        for nome, ficheiro in [("Exemplo 1: gabinete dá sala às aulas sem sala", "exemplo1_gabinete_espacos"),
                               ("Exemplo 2: coordenação pede salas maiores", "exemplo2_coordenacao_curso"),
                               ("Exemplo 3: aulas de sábado passam para sexta", "exemplo3_docentes_sabado")]:
            variantes[nome] = avaliar.aplicar_alteracoes(aulas, pd.read_csv(f"exemplos/{ficheiro}.csv"))
    for f in ficheiros or []:
        try:
            variantes[f.name] = avaliar.aplicar_alteracoes(aulas, pd.read_csv(io.BytesIO(f.getvalue())))
        except Exception as erro:
            st.error(f"Não foi possível ler {f.name}: {erro}")

    t = pd.DataFrame([{"Proposta": nome, **indicadores(nome + str(pd.util.hash_pandas_object(
        h[["sala", "data", "ini_min"]]).sum()), h)} for nome, h in variantes.items()])
    t = t.sort_values(["utilizavel", "problemas", "muda_a_meio", "sala_varia"],
                      ascending=[False, True, True, True]).reset_index(drop=True)
    t.insert(0, "Lugar", [f"{i + 1}.º" if u else "—" for i, u in enumerate(t["utilizavel"])])
    t["Utilizável"] = t["utilizavel"].map({True: "✅ sim", False: "❌ não"})
    nomes = {"problemas": "Com problemas", "sobrelotadas": "Sobrelotadas", "tipo_errado": "Tipo errado",
             "sem_sala": "Sem sala", "choques_sala": "Choques", "muda_a_meio": "Mudam a meio",
             "sala_varia": "Fora da sala habitual"}
    tabela = t[["Lugar", "Proposta", "Utilizável"] + list(nomes)].rename(columns=nomes)
    melhores = ["Com problemas", "Sobrelotadas", "Tipo errado", "Mudam a meio", "Fora da sala habitual"]

    def pintar(col):
        if col.name in melhores and t["utilizavel"].any():
            melhor = col[t["utilizavel"].to_numpy()].min()
            return [f"background-color: #c9efdc; color: #0d6b47; font-weight: 600" if (u and v == melhor) else ""
                    for u, v in zip(t["utilizavel"], col)]
        if col.name in ["Sem sala", "Choques"]:
            return ["background-color: #fde2d6; color: #a33a12; font-weight: 600" if v > 0 else "" for v in col]
        return [""] * len(col)

    st.dataframe(tabela.style.apply(pintar), hide_index=True, width="stretch")
    st.caption(f"🟩 o melhor valor de cada coluna entre as propostas utilizáveis · 🟧 o que torna uma proposta "
               f"inutilizável. Nenhuma proposta pode ter menos de {fmt(otima['problemas'])} aulas com problemas sem "
               "mexer em dias ou horas: é o mínimo provado.")

    for linha in t[~t["utilizavel"]].itertuples():
        with st.expander(f"Porque é que '{linha.Proposta}' não é utilizável?"):
            h = variantes[linha.Proposta]
            pr = avaliar.problemas_por_aula(h, salas)
            st.write(f"{linha.sem_sala} aulas sem sala e {linha.choques_sala} aulas em choque de sala. Exemplos:")
            m = h[pr["sem_sala"] | pr["choques_sala"]].sort_values(["sala", "data", "ini_min"]).head(20)
            st.dataframe(m.assign(data=m["data"].dt.strftime("%Y-%m-%d"), inicio=m["ini_min"].map(hhmm),
                                  fim=m["fim_min"].map(hhmm))[["uc", "turno", "data", "inicio", "fim", "sala"]],
                         hide_index=True, width="stretch")

# ============================================================================ 5. MÉTODOS
with pag5:
    st.subheader("Porque usamos um solver exato")
    st.write("Comparámos o solver exato com quatro heurísticas (métodos rápidos, mas sem garantia de chegar ao "
             "melhor), todas com o mesmo objetivo, 60 segundos e 3 repetições cada.")
    como = {"Guloso": "cada aula na sala que tem hoje, ou na melhor livre",
            "Algoritmo genético": "30 soluções que se cruzam e sofrem mutações",
            "Pesquisa local simples": "muda aulas de sala, só se melhorar",
            "Pesquisa tabu": "aceita também pioras e tem memória para não andar às voltas",
            "Solver exato": "programação inteira (HiGHS): solução + prova"}
    otimo_n = int(metodos.loc[metodos["metodo"] == "Solver exato", "problemas"].iloc[0])
    m = metodos.groupby("metodo")["problemas"].mean().reindex(list(como)).round().astype(int)
    grafico = pd.DataFrame({"Método": ["Horário atual"] + list(m.index),
                            "Aulas com problemas": [atual["problemas"]] + list(m.values)})
    grafico["tipo"] = ["atual"] + ["heurística"] * 4 + ["exato"]
    barras = alt.Chart(grafico).mark_bar(cornerRadiusEnd=6, height=26).encode(
        y=alt.Y("Método:N", sort=None, title=None, axis=alt.Axis(labelFontSize=13, labelLimit=220)),
        x=alt.X("Aulas com problemas:Q", title="Aulas com problemas"),
        color=alt.Color("tipo:N", scale=alt.Scale(domain=["atual", "heurística", "exato"],
                                                  range=["#a0a7b4", AZUL, VERDE]), legend=None),
        tooltip=["Método", "Aulas com problemas"])
    texto = barras.mark_text(align="left", dx=6, fontSize=13, fontWeight="bold", color="#2b3242").encode(
        text="Aulas com problemas:Q")
    st.altair_chart((barras + texto).properties(height=300), width="stretch")

    st.dataframe(pd.DataFrame({"Método": m.index, "Como funciona": [como[k] for k in m.index],
                               "Aulas com problemas": m.values,
                               "Acima do ótimo": [f"+{(v / otimo_n - 1) * 100:.0f}%" if k != "Solver exato"
                                                  else "ótimo provado" for k, v in m.items()]}),
                 hide_index=True, width="stretch")
    st.success(f"A melhor heurística (pesquisa tabu) fica com **{m['Pesquisa tabu']}** aulas com problemas; o solver "
               f"chega a **{otimo_n}** e prova que não há melhor, em cerca de 3 minutos. Por isso a solução da app vem "
               "do solver exato.", icon="🏆")
