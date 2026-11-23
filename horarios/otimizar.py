"""Item 4 - representação do problema e métodos heurísticos (guloso, pesquisa tabu, algoritmo genético).

A solução final da app vem do solver exato (exato.py). As heurísticas daqui servem para:
  - dar uma primeira solução rápida (guloso);
  - mostrar, por comparação, o quão perto (ou longe) do ótimo chegam (comparar_metodos.py).

1. BLOCOS. A mesma aula num dia: aulas do mesmo turno, na mesma data, seguidas (ex.: 18:00-20:00 e
   20:00-22:00) ou sobrepostas. Cada bloco fica numa só sala. Entre semanas a sala pode mudar.

2. CHOQUES. Dois blocos chocam se têm pelo menos uma data com horas sobrepostas.
   Blocos que chocam nunca podem ficar na mesma sala (regra obrigatória, nunca é violada).

3. CUSTO usado pelas heurísticas (o mesmo objetivo do solver exato):
       custo = 1000 x (aulas sobrelotadas + aulas em sala de tipo errado) + 1 x (aulas mudadas)
   Os 1000 não são uma "prioridade" inventada: servem só para que uma mudança de sala nunca compense
   um problema. Ou seja, primeiro menos problemas; entre soluções empatadas, menos mudanças.
"""
import time

import numpy as np
import pandas as pd

from .avaliar import bloco_do_dia, serie_semanal, tipo_aceite
from .dados import SEM_SALA

PESOS = (1000, 1000, 1)   # (sobrelotação, tipo de sala, mudança): problemas primeiro, mudanças só desempatam


class Problema:
    def __init__(self, aulas, salas):
        self.aulas = aulas
        self.salas = salas["sala"].tolist()
        self.R = len(self.salas)                     # índice R = "sem sala"
        capacidade = salas["capacidade"].to_numpy(float)
        caract = salas["caracteristicas"].tolist()
        existentes = set().union(*caract)
        indice_sala = {s: i for i, s in enumerate(self.salas)}

        # ---------------------------------------------------------------- 1. blocos
        # Um bloco = a MESMA AULA num dia: aulas do mesmo turno, na mesma data, seguidas (ex.: 18:00-20:00 e
        # 20:00-22:00) ou com horas sobrepostas. Fica obrigatoriamente numa só sala (ninguém muda a meio).
        # De semana para semana a sala PODE mudar; só preferimos que não mude (ver exato.py, fase 2).
        precisa = aulas[aulas["pedida"] != SEM_SALA].copy().reset_index(drop=True)
        precisa["bloco"] = bloco_do_dia(precisa)
        precisa["sala_atual"] = precisa["sala"].map(indice_sala).fillna(self.R).astype(int)

        moda = lambda serie: serie.mode().iloc[0]
        self.blocos = precisa.groupby("bloco").agg(
            uc=("uc", "first"), curso=("curso", "first"), turno=("turno", "first"), dia_semana=("dia_semana", "first"),
            ini_min=("ini_min", "min"), fim_min=("fim_min", "max"), inscritos=("inscritos", "first"),
            pedida=("pedida", moda), n_aulas=("aula_id", "size"),
            sala_atual=("sala_atual", lambda v: moda(v[v < self.R]) if (v < self.R).any() else self.R),
        ).reset_index(drop=True)
        self.B = len(self.blocos)
        self.serie = serie_semanal(self.blocos).to_numpy()   # blocos que são a mesma aula em semanas diferentes
        self.aula_bloco = precisa[["aula_id", "bloco"]]
        self.atual = self.blocos["sala_atual"].to_numpy()        # sala mais usada hoje pelo bloco (R = nenhuma)
        self.dia_semana = self.blocos["dia_semana"].to_numpy()
        inscritos = self.blocos["inscritos"].to_numpy()

        # ---------------------------------------------------------------- 2. choques entre blocos
        # Aulas que não precisam de sala mas ocupam uma (30 casos) ficam fixas e bloqueiam essa sala.
        fixas = aulas[(aulas["pedida"] == SEM_SALA) & aulas["sala"].notna()]
        eventos = pd.concat([
            precisa[["data", "ini_min", "fim_min", "bloco"]],
            pd.DataFrame({"data": fixas["data"], "ini_min": fixas["ini_min"], "fim_min": fixas["fim_min"],
                          "bloco": -1 - fixas["sala"].map(indice_sala).to_numpy()}),   # negativo = sala fixa
        ])
        pares, bloqueios = set(), set()
        for _, dia in eventos.groupby("data"):
            a_decorrer = []                                  # (fim, bloco) das aulas ainda a decorrer
            for b, ini, fim in sorted(zip(dia["bloco"], dia["ini_min"], dia["fim_min"]), key=lambda t: t[1]):
                a_decorrer = [(f, o) for f, o in a_decorrer if f > ini]
                for _, outro in a_decorrer:
                    if b >= 0 and outro >= 0 and b != outro:
                        pares.add((min(b, outro), max(b, outro)))
                    elif (b >= 0) != (outro >= 0):
                        bloqueios.add((b, -1 - outro) if b >= 0 else (outro, -1 - b))
                a_decorrer.append((fim, b))
        vizinhos = [[] for _ in range(self.B)]
        for a, b in pares:
            vizinhos[a].append(b)
            vizinhos[b].append(a)
        self.choca_com = [np.array(v, dtype=int) for v in vizinhos]
        self.n_choques = len(pares)
        self.bloqueada = np.zeros((self.B, self.R), dtype=bool)
        for b, s in bloqueios:
            self.bloqueada[b, s] = True

        # ---------------------------------------------------------------- 3. tabelas de problemas (bloco x sala)
        # Quantas aulas do bloco b ficariam sobrelotadas / em tipo errado / mudadas se ele fosse para a sala s.
        # (Contamos aula a aula: no mesmo bloco pode haver semanas com pedidos ou salas atuais diferentes.)
        R, R1 = self.R, self.R + 1
        self.cabe = inscritos[:, None] <= capacidade[None, :]
        n = self.blocos["n_aulas"].to_numpy()
        self.sobre = np.zeros((self.B, R1), int)
        self.tipo = np.zeros((self.B, R1), int)
        self.muda = np.zeros((self.B, R1), int)
        self.sobre[:, :R] = ~self.cabe * n[:, None]
        for (b, pedida), k in precisa.groupby(["bloco", "pedida"]).size().items():
            self.tipo[b, :R] += k * np.array([not tipo_aceite(pedida, c, existentes) for c in caract])
        for (b, s_atual), k in precisa.groupby(["bloco", "sala_atual"]).size().items():
            if s_atual < R:                       # aulas que já tinham sala: mudam se forem para outra
                self.muda[b, :R] += k
                self.muda[b, s_atual] -= k
        self.tipo_ok = self.tipo[:, :R] == 0
        self.sem = np.zeros((self.B, R1), int)
        self.sem[:, R] = n
        self.capacidade = capacidade
        self.inscritos = inscritos
        self._todos = np.arange(self.B)

    # -------------------------------------------------------------------- utilitários
    def custos(self, pesos):
        """Tabela bloco x sala com o custo de pôr cada bloco em cada sala."""
        ws, wt, wm = pesos[:3]
        return ws * self.sobre + wt * self.tipo + wm * self.muda + 100 * max(pesos[:3]) * self.sem

    def salas_livres(self, x, b, ignorar=None):
        """Salas onde o bloco b pode entrar sem chocar com ninguém."""
        livre = np.ones(self.R + 1, dtype=bool)
        outros = self.choca_com[b] if ignorar is None else self.choca_com[b][self.choca_com[b] != ignorar]
        livre[x[outros]] = False
        return livre[:self.R] & ~self.bloqueada[b]

    def resultado(self, x):
        """Contagens de problemas (em aulas) de uma solução."""
        t = self._todos
        return {"sobrelotadas": int(self.sobre[t, x].sum()), "tipo_errado": int(self.tipo[t, x].sum()),
                "mudancas": int(self.muda[t, x].sum()), "sem_sala": int(self.sem[t, x].sum())}

    def choques(self, x):
        """Quantos pares de blocos que chocam estão na mesma sala (tem de ser sempre 0)."""
        return sum(int(((x[self.choca_com[b]] == x[b]) & (self.choca_com[b] > b)).sum()) + int(self.bloqueada[b, x[b]])
                   for b in range(self.B) if x[b] < self.R)

    def para_aulas(self, x):
        """Tabela de aulas com as salas da solução x."""
        aulas = self.aulas.copy()
        nomes = np.array(self.salas + [None], dtype=object)
        nova = pd.Series(nomes[x[self.aula_bloco["bloco"].to_numpy()]], index=self.aula_bloco["aula_id"].to_numpy())
        aulas.loc[nova.index, "sala"] = nova.to_numpy()
        return aulas

    def resumo(self):
        return {"aulas que precisam de sala": int(self.aula_bloco.shape[0]), "blocos": self.B,
                "salas": self.R, "pares de blocos que chocam": self.n_choques}


# ------------------------------------------------------------------------ guloso
def melhor_sala(p, b, livres):
    """Entre as salas livres: primeiro as do tipo certo, depois as que têm lugar para todos,
    e entre essas a mais pequena (para não gastar salas grandes)."""
    cand = np.flatnonzero(livres)
    if len(cand) == 0:
        return None
    folga = p.capacidade[cand] - p.inscritos[b]
    ordem = np.lexsort((np.where(folga >= 0, folga, 1e4 - folga), ~p.cabe[b, cand], ~p.tipo_ok[b, cand]))
    return int(cand[ordem[0]])


def guloso(p):
    """Ponto de partida. Cada bloco fica, se possível, na sala que mais usa hoje; se essa sala já estiver ocupada
    (ou se o bloco não tinha sala), recebe a melhor sala livre. Turmas maiores primeiro."""
    x = np.full(p.B, p.R)
    for b in np.lexsort((-p.inscritos, p.atual == p.R)):      # primeiro os que têm sala atual
        livres = p.salas_livres(x, b)
        if p.atual[b] < p.R and livres[p.atual[b]]:
            x[b] = p.atual[b]
        else:
            s = melhor_sala(p, b, livres)
            if s is not None:
                x[b] = s
    return x


# ------------------------------------------------------------------------ pesquisa tabu
def tabu(p, pesos=PESOS, iteracoes=2000, semente=0, x_inicial=None, ao_progredir=None, segundos=None,
         so_melhorias=False):
    """Pesquisa tabu (Glover, 1989).

    Em cada iteração:
      1. escolhe ~50 blocos (sobretudo blocos com problemas);
      2. para cada um, vê todas as jogadas possíveis:
           - MOVER o bloco para uma sala livre;
           - TROCAR com o único bloco que ocupa a sala desejada;
      3. faz a melhor jogada que não seja "tabu" - mesmo que piore o custo (é isto que permite
         sair de becos sem saída, ao contrário de um método que só aceita melhorias);
      4. proíbe o bloco de voltar à sala de onde saiu durante 7 a 15 iterações (a "lista tabu"),
         para não andar em círculos. Exceção: se a jogada proibida der o melhor custo de sempre, é aceite.
    Guarda sempre a melhor solução encontrada.

    Com so_melhorias=True passa a ser uma "pesquisa local simples" (sem lista tabu e só aceita
    jogadas que baixam o custo). Usamo-la na comparação para mostrar o que a lista tabu acrescenta.
    """
    rng = np.random.default_rng(semente)
    C = p.custos(pesos)
    R = p.R
    x = (guloso(p) if x_inicial is None else x_inicial).copy()
    custo_bloco = C[p._todos, x]
    custo = melhor_custo = int(custo_bloco.sum())
    melhor_x = x.copy()
    minimo_possivel = C[:, :R].min(axis=1)
    tabu_ate = np.zeros((p.B, R + 1), dtype=int)       # iteração até à qual (bloco, sala) está proibido
    historico = [(0.0, melhor_custo)]
    inicio = time.perf_counter()

    for it in range(1, iteracoes + 1):
        com_problemas = np.flatnonzero(custo_bloco > minimo_possivel)
        escolhidos = rng.choice(com_problemas, min(40, len(com_problemas)), replace=False) if len(com_problemas) else []
        escolhidos = np.concatenate([escolhidos, rng.integers(0, p.B, 10)]).astype(int)

        melhor_jogada, melhor_delta = None, np.inf
        for b in escolhidos:
            sala_b = x[b]
            delta = C[b, :R] - C[b, sala_b]                         # quanto muda o custo se b for para cada sala
            livres = p.salas_livres(x, b)
            if sala_b < R:
                livres[sala_b] = False
            permitido = livres & ((tabu_ate[b, :R] < it) | (custo + delta < melhor_custo))
            if so_melhorias:
                permitido = livres & (delta < 0)
            if permitido.any():
                s = int(np.argmin(np.where(permitido, delta, np.inf)))
                if delta[s] < melhor_delta:
                    melhor_jogada, melhor_delta = ("mover", b, s), delta[s]
            if sala_b == R:
                continue
            for s in np.argsort(delta)[:3]:                         # trocas com quem está nas 3 melhores salas
                if livres[s] or s == sala_b:
                    continue
                ocupantes = p.choca_com[b][x[p.choca_com[b]] == s]
                if len(ocupantes) != 1:
                    continue
                o = int(ocupantes[0])
                if not (p.salas_livres(x, o, ignorar=b)[sala_b] and p.salas_livres(x, b, ignorar=o)[s]):
                    continue
                d = delta[s] + C[o, sala_b] - C[o, s]
                proibida = tabu_ate[b, s] >= it or tabu_ate[o, sala_b] >= it
                if so_melhorias and d >= 0:
                    continue
                if (not proibida or custo + d < melhor_custo) and d < melhor_delta:
                    melhor_jogada, melhor_delta = ("trocar", b, int(s), o), d

        if melhor_jogada is not None and not (so_melhorias and melhor_delta >= 0):
            duracao = int(rng.integers(7, 16))
            if melhor_jogada[0] == "mover":
                _, b, s = melhor_jogada
                tabu_ate[b, x[b]] = it + duracao
                x[b] = s
                custo_bloco[b] = C[b, s]
            else:
                _, b, s, o = melhor_jogada
                tabu_ate[b, x[b]] = tabu_ate[o, s] = it + duracao
                x[b], x[o] = s, x[b]
                custo_bloco[b], custo_bloco[o] = C[b, s], C[o, x[o]]
            custo += int(melhor_delta)
            if custo < melhor_custo:
                melhor_custo, melhor_x = custo, x.copy()

        decorrido = time.perf_counter() - inicio
        if it % 50 == 0:
            historico.append((decorrido, melhor_custo))
            if ao_progredir:
                ao_progredir(it / iteracoes if segundos is None else min(decorrido / segundos, 1.0))
        if segundos is not None and decorrido > segundos:
            break
    historico.append((time.perf_counter() - inicio, melhor_custo))
    return melhor_x, historico


# ------------------------------------------------------------------------ algoritmo genético
def genetico(p, pesos=PESOS, segundos=30, populacao=30, semente=0, x_inicial=None):
    """Algoritmo genético simples (só para comparar com o tabu, ver comparar_metodos.py).

    - Indivíduo: a sala de cada bloco.
    - Seleção: torneio entre 2 indivíduos ao acaso (ganha o de menor custo).
    - Cruzamento: o filho herda os blocos de alguns dias da semana do pai e os restantes da mãe.
      Como blocos de dias diferentes nunca chocam, o filho nunca tem choques.
    - Mutação: muda alguns blocos com problemas para a melhor sala livre (ou uma sala livre ao acaso).
    - Elitismo: os 2 melhores passam sempre para a geração seguinte.
    """
    rng = np.random.default_rng(semente)
    C = p.custos(pesos)
    custo = lambda x: int(C[p._todos, x].sum())
    dias = np.unique(p.dia_semana)

    def mutar(x, k):
        for _ in range(k):
            problemas = np.flatnonzero(C[p._todos, x] > C[:, :p.R].min(axis=1))
            b = int(rng.choice(problemas)) if len(problemas) and rng.random() < 0.8 else int(rng.integers(p.B))
            livres = p.salas_livres(x, b)
            if x[b] < p.R:
                livres[x[b]] = False
            if livres.any():
                x[b] = (int(np.argmin(np.where(livres, C[b, :p.R], np.inf))) if rng.random() < 0.5
                        else int(rng.choice(np.flatnonzero(livres))))
        return x

    base = guloso(p) if x_inicial is None else x_inicial
    pop = [base.copy()] + [mutar(base.copy(), int(rng.integers(10, 100))) for _ in range(populacao - 1)]
    custos = [custo(x) for x in pop]
    historico = [(0.0, min(custos))]
    inicio = time.perf_counter()
    while time.perf_counter() - inicio < segundos:
        ordem = np.argsort(custos)
        nova = [pop[ordem[0]], pop[ordem[1]]]                    # elitismo
        while len(nova) < populacao:
            i, j = rng.integers(populacao, size=2)
            pai = pop[i] if custos[i] <= custos[j] else pop[j]
            i, j = rng.integers(populacao, size=2)
            mae = pop[i] if custos[i] <= custos[j] else pop[j]
            dias_do_pai = dias[rng.random(len(dias)) < 0.5]
            filho = np.where(np.isin(p.dia_semana, dias_do_pai), pai, mae)
            nova.append(mutar(filho, int(rng.integers(1, 10))))
        pop, custos = nova, [custo(x) for x in nova]
        historico.append((time.perf_counter() - inicio, min(custos)))
    return pop[int(np.argmin(custos))], historico


# ------------------------------------------------------------------------ fase 2: mesma sala entre semanas
def consolidar_semanas(p, x, max_passagens=20, problemas_juntos=False):
    """Fase 2 (preferência): pôr as semanas da mesma aula semanal na mesma sala, SEM piorar nenhum problema.

    Pesquisa local. Para cada aula semanal com semanas em salas diferentes, tenta levar cada semana "fora" para a
    sala onde a aula está mais vezes (ou outra das salas que já usa, ou uma sala nova que esteja livre, sem piorar,
    em mais semanas do que a atual):
      - MOVER, se essa sala estiver livre nessa data e hora;
      - TROCAR com a única aula que a ocupa, se essa aula couber na sala de onde saímos.
    Só aceita a jogada se nenhuma das aulas envolvidas ficar com mais problemas e se o total de aulas fora da sala
    habitual descer. "Mais problemas" = mais sobrelotação ou mais tipo errado; com problemas_juntos=True (solução
    principal, onde os dois contam igual) = mais sobrelotação + tipo errado no total. Repete até não haver melhorias.
    Devolve a nova solução (a fase 1 - problemas - fica exatamente igual)."""
    x = x.copy()
    n = p.blocos["n_aulas"].to_numpy()
    serie = p.serie
    membros = pd.Series(np.arange(p.B)).groupby(serie).apply(list).to_dict()
    cont = {S: {} for S in membros}
    for b in range(p.B):
        cont[serie[b]][x[b]] = cont[serie[b]].get(x[b], 0) + n[b]

    def fora(S):
        c = cont[S]
        return sum(c.values()) - max(c.values())

    def mexer(b, de, para):
        c = cont[serie[b]]
        c[de] -= n[b]
        if c[de] == 0:
            del c[de]
        c[para] = c.get(para, 0) + n[b]

    P = p.sobre + p.tipo

    def nao_piora(b, s, de=None):
        de = x[b] if de is None else de
        if problemas_juntos:
            return P[b, s] <= P[b, de]
        return p.sobre[b, s] <= p.sobre[b, de] and p.tipo[b, s] <= p.tipo[b, de]

    for _ in range(max_passagens):
        melhorou = 0
        for S, bs in membros.items():
            if len(cont[S]) < 2:
                continue
            # salas candidatas: as que a aula já usa e, além dessas, a sala livre (sem piorar) para mais semanas
            livres_para = np.zeros(p.R)
            for b in bs:
                if x[b] < p.R:
                    if problemas_juntos:
                        ok = p.salas_livres(x, b) & (P[b, :p.R] <= P[b, x[b]])
                    else:
                        ok = p.salas_livres(x, b) & (p.sobre[b, :p.R] <= p.sobre[b, x[b]]) & (p.tipo[b, :p.R] <= p.tipo[b, x[b]])
                    ok[x[b]] = True
                    livres_para += ok * n[b]
            extra = [int(r) for r in np.argsort(-livres_para)[:3] if livres_para[r] > max(cont[S].values())]
            for alvo in extra + sorted(cont[S], key=cont[S].get, reverse=True):
                for b in bs:
                    de = x[b]
                    if de == alvo or de == p.R or not nao_piora(b, alvo) or p.bloqueada[b, alvo]:
                        continue
                    ocupantes = p.choca_com[b][x[p.choca_com[b]] == alvo]
                    if len(ocupantes) == 0:
                        antes = fora(S)
                        mexer(b, de, alvo)
                        if fora(S) < antes:
                            x[b] = alvo
                            melhorou += 1
                        else:
                            mexer(b, alvo, de)
                    elif len(ocupantes) == 1:
                        o = int(ocupantes[0])
                        So = serie[o]
                        if So == S or p.bloqueada[o, de] or not nao_piora(o, de):
                            continue
                        if not (p.salas_livres(x, o, ignorar=b)[de]):
                            continue
                        antes = fora(S) + fora(So)
                        mexer(b, de, alvo)
                        mexer(o, alvo, de)
                        if fora(S) + fora(So) < antes:
                            x[b], x[o] = alvo, de
                            melhorou += 1
                        else:
                            mexer(o, de, alvo)
                            mexer(b, alvo, de)
                if len(cont[S]) < 2:
                    break
        if melhorou == 0:
            break
    return x
