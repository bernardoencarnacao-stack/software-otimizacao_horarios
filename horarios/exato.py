"""Item 4 - a solução ÓTIMA, calculada por programação inteira (solver HiGHS).

O MODELO, em palavras
  - Decisão: em que sala fica cada bloco (a mesma aula num dia: aulas seguidas ou sobrepostas do mesmo turno).
  - Regra 1: cada bloco fica exatamente numa sala.
  - Regra 2: em cada sala, em cada momento, no máximo um bloco. Para isso juntamos, para cada momento de
    cada dia, todos os blocos que estão a decorrer ao mesmo tempo ("momentos simultâneos").
  - Regra 3: salas ocupadas por aulas fixas nesse período não se podem usar.

SEM PESOS: resolvemos por fases (ordem de prioridade)
  Fase 1 - minimizar os PROBLEMAS: aulas sobrelotadas + aulas em sala de tipo errado (contam igual).
  Fase 2 - preferência: entre as soluções com o mínimo de problemas, a mesma sala de semana para semana.
           Aqui escolhemos as salas concretas mantendo o máximo de aulas na sala que já tinham (o horário de
           exemplo é quase sempre estável); depois otimizar.consolidar_semanas junta as semanas que ainda
           ficaram em salas diferentes, sem nunca piorar a fase 1.
  (Na secção "prioridades" da app usamos outras ordens, por exemplo sobrelotação primeiro.)

TRUQUE 1 - um dia da semana de cada vez: blocos de dias diferentes nunca chocam.
TRUQUE 2 - salas iguais juntas: salas com a mesma capacidade e características são intercambiáveis para os
  problemas. Em vez de "o bloco vai para a sala C2.01" decidimos "o bloco vai para uma sala do grupo
  {C2.01, C2.02, ...}" e a regra 2 passa a "no máximo tantos blocos quantas salas tem o grupo". Isto torna o
  problema muito mais rápido. No fim, um segundo modelo escolhe a sala concreta de cada bloco, sem choques,
  sem piorar nenhum problema e mantendo o máximo de aulas na sala que já tinham.

A GARANTIA: além da solução, o solver devolve um LIMITE INFERIOR - um valor abaixo do qual é impossível
descer. Quando a solução é igual ao limite, está PROVADO que não existe solução melhor.
"""
import time

import highspy
import numpy as np

CRITERIOS = {"problemas": "aulas com problemas", "sobrelotadas": "aulas sobrelotadas",
             "tipo_errado": "aulas em sala de tipo errado"}


def momentos_simultaneos(p):
    """Conjuntos de blocos a decorrer ao mesmo tempo em algum momento de algum dia (só os maiores)."""
    oc = p.aula_bloco.merge(p.aulas[["aula_id", "data", "ini_min", "fim_min"]], on="aula_id")
    conjuntos = set()
    for _, dia in oc.groupby("data"):
        for inicio in dia["ini_min"].unique():
            a_decorrer = frozenset(dia.loc[(dia["ini_min"] <= inicio) & (dia["fim_min"] > inicio), "bloco"])
            if len(a_decorrer) > 1:
                conjuntos.add(a_decorrer)
    maiores = []
    for c in sorted(conjuntos, key=len, reverse=True):
        if not any(c <= m for m in maiores):
            maiores.append(c)
    return maiores


def custo(p, criterio):
    """Tabela bloco x sala: quantas aulas ficam com o problema `criterio` se o bloco b for para a sala s."""
    if criterio == "sobrelotadas":
        return p.sobre[:, :p.R]
    if criterio == "tipo_errado":
        return p.tipo[:, :p.R]
    return p.sobre[:, :p.R] + p.tipo[:, :p.R]


def grupos_de_salas(p):
    """Salas intercambiáveis: mesma capacidade, mesmas características e mesmos bloqueios por aulas fixas."""
    grupos = {}
    for s in range(p.R):
        chave = (p.cabe[:, s].tobytes(), p.tipo[:, s].tobytes(), p.bloqueada[:, s].tobytes())
        grupos.setdefault(chave, []).append(s)
    return list(grupos.values())


class _Modelo:
    """Modelo de um dia da semana com uma variável por (bloco, unidade). Uma unidade é um grupo de salas iguais
    ou uma sala concreta."""

    def __init__(self, p, blocos, momentos, grupos, segundos, permitido=None):
        self.p, self.blocos, self.grupos, self.segundos = p, blocos, grupos, segundos
        ok = permitido or (lambda b, g: not p.bloqueada[b, grupos[g][0]])
        self.pares = [(b, g) for b in blocos for g in range(len(grupos)) if ok(b, g)]
        self.col = {par: j for j, par in enumerate(self.pares)}
        n = len(self.pares)
        h = self.h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("mip_rel_gap", 0.0)
        h.addVars(n, np.zeros(n), np.ones(n))
        h.changeColsIntegrality(n, np.arange(n, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * n))
        for b in blocos:                                                   # regra 1
            js = [self.col[(b, g)] for g in range(len(grupos)) if (b, g) in self.col]
            h.addRow(1, 1, len(js), np.array(js, dtype=np.int32), np.ones(len(js)))
        no_dia = set(blocos)
        for m in momentos:                                                 # regra 2 (por grupo)
            m = [b for b in m if b in no_dia]
            for g, salas in enumerate(grupos):
                js = [self.col[(b, g)] for b in m if (b, g) in self.col]
                if len(js) > len(salas):
                    h.addRow(0, len(salas), len(js), np.array(js, dtype=np.int32), np.ones(len(js)))
        self.n = h.getNumCol()

    def vetor(self, tabela):
        return np.array([tabela[b, self.grupos[g][0]] for b, g in self.pares], float)

    def completar(self, escolha):
        """Vetor de solução (ponto de partida) a partir de {bloco: unidade}."""
        v = np.zeros(self.n)
        for b, g in escolha.items():
            v[self.col[(b, g)]] = 1
        return v

    def minimizar(self, coef, inicial=None, constante=0):
        h = self.h
        h.changeColsCost(self.n, np.arange(self.n, dtype=np.int32), coef)
        h.setOptionValue("time_limit", float(self.segundos))
        if inicial is not None:
            s = highspy.HighsSolution()
            s.col_value = list(inicial)
            h.setSolution(s)
        t = time.perf_counter()
        h.run()
        info = h.getInfo()
        x = np.array(h.getSolution().col_value)
        if info.primal_solution_status != 2:              # sem solução viável
            return None, {"valor": None, "limite_inferior": None, "provado_otimo": False,
                          "segundos": round(time.perf_counter() - t, 1)}
        return x, {"valor": int(round(info.objective_function_value)) + constante,
                   "limite_inferior": int(np.ceil(info.mip_dual_bound - 1e-6)) + constante,
                   "provado_otimo": h.getModelStatus() == highspy.HighsModelStatus.kOptimal,
                   "segundos": round(time.perf_counter() - t, 1)}

    def fixar_maximo(self, coef, valor):
        js = np.flatnonzero(coef)
        self.h.addRow(-highspy.kHighsInf, valor, len(js), js.astype(np.int32), coef[js])

    def grupo_escolhido(self, x):
        return {b: g for (b, g), v in zip(self.pares, x) if v > 0.5}


def _distribuir_pelas_salas(p, blocos, momentos, grupos, grupo_de_bloco, segundos):
    """Passo final: escolher a sala concreta de cada bloco, sem choques, mantendo o máximo de aulas na sala que já
    tinham (o horário de exemplo usa quase sempre a mesma sala de semana para semana, o que ajuda a fase 2). Cada bloco pode ir para qualquer sala que não lhe dê MAIS problemas (de nenhum tipo) do
    que o grupo escolhido - por isso os totais de problemas nunca pioram e a garantia de ótimo mantém-se."""
    def permitido(b, s):
        g = grupos[grupo_de_bloco[b]][0]
        return not p.bloqueada[b, s] and p.sobre[b, s] <= p.sobre[b, g] and p.tipo[b, s] <= p.tipo[b, g]
    m = _Modelo(p, blocos, momentos, [[s] for s in range(p.R)], segundos, permitido=permitido)
    x, info = m.minimizar(m.vetor(p.muda[:, :p.R]))
    if x is None:
        raise RuntimeError("não foi possível distribuir os blocos pelas salas")
    return m.grupo_escolhido(x), info


def _resolver_dia_por_sala(p, blocos, momentos, ordem, valores, segundos, x_inicial):
    """Plano B, quando os grupos de salas iguais não se conseguem distribuir pelas salas concretas: resolve o dia
    diretamente sala a sala (mais lento, mas exato). O limite inferior dos grupos continua válido para o 1.º
    critério, por isso, se a solução o atingir, continua provada ótima."""
    m = _Modelo(p, blocos, momentos, [[s] for s in range(p.R)], segundos)
    x = None
    if x_inicial is not None and np.all(x_inicial[blocos] < p.R):
        x = m.completar({b: int(x_inicial[b]) for b in blocos})
    infos = []
    for k, criterio in enumerate(ordem):
        coef = m.vetor(custo(p, criterio))
        x, info = m.minimizar(coef, x)
        if k == 0 and info["valor"] is not None:
            info["limite_inferior"] = max(info["limite_inferior"], valores[criterio])
            info["provado_otimo"] = info["valor"] == info["limite_inferior"]
        m.fixar_maximo(coef, info["valor"])
        infos.append((f"{criterio}", info))
    x, info = m.minimizar(m.vetor(p.muda[:, :p.R]), x)
    infos.append(("mudancas (salas concretas)", info))
    return m.grupo_escolhido(x), infos


def resolver(p, ordem=("problemas",), segundos=600, ao_progredir=None, registo=print, x_inicial=None):
    """Resolve todos os dias da semana. `ordem` = critérios por ordem de prioridade; no fim mantém o máximo
    de aulas na sala que já tinham. `x_inicial` (opcional) = uma solução já conhecida, que o solver usa como
    ponto de partida (não muda o resultado ótimo, só o torna mais rápido de encontrar).
    Devolve (sala de cada bloco, relatório por dia e por fase)."""
    momentos = momentos_simultaneos(p)
    grupos = grupos_de_salas(p)
    grupo_da_sala = {s: g for g, ss in enumerate(grupos) for s in ss}
    x_final = np.full(p.B, p.R)
    relatorio = []
    dias = list(dict.fromkeys(p.dia_semana))
    for k, dia in enumerate(dias):
        blocos = np.flatnonzero(p.dia_semana == dia).tolist()
        m = _Modelo(p, blocos, momentos, grupos, segundos)
        x = None
        if x_inicial is not None and np.all(x_inicial[blocos] < p.R):
            x = m.completar({b: grupo_da_sala[int(x_inicial[b])] for b in blocos})
        valores, n_antes = {}, len(relatorio)
        for criterio in ordem:
            coef = m.vetor(custo(p, criterio))
            x, info = m.minimizar(coef, x)
            m.fixar_maximo(coef, info["valor"])
            valores[criterio] = info["valor"]
            relatorio.append({"dia": dia, "fase": criterio, **info})
            registo(f"{dia} | {criterio}: {info}")
        # entre as soluções ótimas, manter as aulas nas salas que já tinham (ao nível dos grupos)
        muda_grupo = np.array([p.muda[:, ss].min(axis=1) for ss in grupos]).T
        x, info = m.minimizar(np.array([float(muda_grupo[b, g]) for b, g in m.pares]), x)
        relatorio.append({"dia": dia, "fase": "mudancas (grupos)", **info})
        registo(f"{dia} | mudanças (grupos): {info}")
        try:
            sala, info = _distribuir_pelas_salas(p, blocos, momentos, grupos, m.grupo_escolhido(x), segundos)
            relatorio.append({"dia": dia, "fase": "mudancas (salas concretas)", **info})
            registo(f"{dia} | mudanças (salas concretas): {info}")
        except RuntimeError:
            registo(f"{dia} | os grupos não se distribuem pelas salas: plano B, sala a sala")
            del relatorio[n_antes:]
            sala, infos = _resolver_dia_por_sala(p, blocos, momentos, ordem, valores, segundos, x_inicial)
            for fase, info in infos:
                relatorio.append({"dia": dia, "fase": fase, **info})
                registo(f"{dia} | {fase} (sala a sala): {info}")
        for b in blocos:
            x_final[b] = sala[b]
        if ao_progredir:
            ao_progredir((k + 1) / len(dias))
    return x_final, relatorio
