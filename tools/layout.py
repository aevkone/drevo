"""Автокомпоновка древа: пересчитывает x у людей в data/base.json.

Порядок людей внутри поколения берётся из текущих x (или из ORDER ниже),
а сами x подбираются так, чтобы дети стояли под родителями, родители — над
детьми, супруги — рядом, а карточки не налезали друг на друга.
Запуск:  python tools/layout.py  &&  python tools/build.py
"""
import json
import pathlib

D = pathlib.Path(__file__).resolve().parent.parent / 'data'
GAP_SPOUSE, GAP_SIB, GAP_OTHER = 1.0, 1.06, 1.18

# Порядок слева направо по поколениям. Отцовская линия слева, материнская справа,
# прямая линия Валерии Валерьевны — ось посередине. Кого нет в списке — встаёт по старому x.
ORDER = {
    3: 'PUR DAS AKI TCH TSK',
    4: 'VDS VCS JDS KZE ELS OMS VKS KMS BOF AAS AHN THN DSP EDP',
    5: 'AUR PUK AMK MMK ANT FPT MKI AGL LDS SMD BGS ANL ADS ATS FAS SES FRS ALA AGN SAN MMA SDP YDP ETP',
    6: 'OSA AN2 KZA IGA JGD ANA SNL FMD FSA MKO ASA KKU MPM ANS PVK EPZ AYP PYP OYP AKP MYP KOK ALB ELN HPN',
    7: 'IGO OSO BSK MSK2 MSL AVS DFS PKP AGK AG2 NZK NFK EPK PMM EBF PPK IKR VSL RAI VBN EP1 NAP AAP MPN',
    8: 'HGR HBS MPB VLO TAO ANO RAS VAS EAS AN3 VST NPM PYU FPM PPM APM GIK LVS MRA NVK',
    9: 'TGR AGR MGR ABS OBS SVV VAV ISV ASV IYP IRO LMB IMB',
    10: 'AVT ICS MIP UIP',
    11: 'LIC',
}
# Прямая линия (ось): её карточки весят больше, остальные подстраиваются вокруг
SPINE = 'LIC AVT VAV VLO OSO OSA ANT KZE DAS JS2 JSK PSK'.split()
SPINE_W = 6.0


def main():
    base = json.loads((D / 'base.json').read_text(encoding='utf-8'))
    P = base['P']
    couples = [c for c in base['C'] if c[3] != 'sib']
    gen = {p: v[0] for p, v in P.items()}
    x = {p: float(v[1]) for p, v in P.items()}

    rows = {}
    for p in P:
        rows.setdefault(gen[p], []).append(p)
    for g, ids in rows.items():
        want = ORDER.get(g, '').split()
        rank = {p: i for i, p in enumerate(want)}
        ids.sort(key=lambda p: (0, rank[p]) if p in rank else (1, x[p]))
        if want:  # люди не из списка встают по своему старому месту среди упорядоченных
            fixed = [p for p in ids if p in rank]
            rest = [p for p in ids if p not in rank]
            for p in rest:
                i = next((k for k, q in enumerate(fixed) if x[q] > x[p]), len(fixed))
                fixed.insert(i, p)
            ids[:] = fixed

    parents = {}   # ребёнок -> список пар родителей
    unions = {}    # человек -> список (супруг или None, дети)
    spouses = set()
    for a, b, kids, _ in couples:
        for k in kids:
            parents.setdefault(k, []).append((a, b))
        for p, q in ((a, b), (b, a)):
            if p:
                unions.setdefault(p, []).append((q, kids))
        if a and b:
            spouses.add(frozenset((a, b)))
    sibs = set()
    for a, b, kids, _ in couples:
        for k in kids:
            for j in kids:
                if k != j:
                    sibs.add(frozenset((k, j)))

    def gap(a, b):
        f = frozenset((a, b))
        if f in spouses or any(frozenset((a, c)) in spouses and frozenset((b, c)) in spouses for c in P):
            return GAP_SPOUSE
        return GAP_SIB if f in sibs else GAP_OTHER

    def marker(a, b):
        return (x[a] + x[b]) / 2 if b else x[a]

    def down(p):
        ps = parents.get(p)
        return sum(marker(a, b) for a, b in ps) / len(ps) if ps else None

    def up(p):
        vals = []
        for q, kids in unions.get(p, []):
            ks = [k for k in kids if k in x]
            if not ks:
                continue
            m = sum(x[k] for k in ks) / len(ks)
            vals.append(m + (0 if not q else (-0.5 if x[p] < x[q] else 0.5)))
        return sum(vals) / len(vals) if vals else None

    def pack(ids, want):
        # соседние супруги — жёсткий блок; блоки сдвигаются минимально от желаемых x
        # при заданных зазорах (изотоническая регрессия)
        def tied(a, b):  # супруги или два супруга одного человека, стоящего рядом
            if frozenset((a, b)) in spouses:
                return True
            return any(frozenset((a, c)) in spouses and frozenset((b, c)) in spouses for c in ids)

        units = []
        for p in ids:
            if units and tied(units[-1][-1], p):
                units[-1].append(p)
            else:
                units.append([p])
        inner = {}
        for u in units:
            o = 0.0
            for i, p in enumerate(u):
                if i:
                    o += gap(u[i - 1], p)
                inner[p] = o
        wt = lambda p: SPINE_W if p in SPINE else 1.0
        uw = [sum((want[p] - inner[p]) * wt(p) for p in u) / sum(wt(p) for p in u) for u in units]
        off = [0.0]
        for i in range(1, len(units)):
            prev = units[i - 1]
            off.append(off[-1] + inner[prev[-1]] + gap(prev[-1], units[i][0]))
        blocks = []
        for i, u in enumerate(units):
            blocks.append([uw[i] - off[i], sum(wt(p) for p in u), i, i])
            while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
                v2, w2, s2, e2 = blocks.pop()
                v1, w1, s1, _ = blocks.pop()
                blocks.append([(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2, s1, e2])
        for v, _, s, e in blocks:
            for i in range(s, e + 1):
                for p in units[i]:
                    x[p] = v + off[i] + inner[p]

    def sweep(gens, first, second):
        for g in gens:
            ids = rows[g]
            want = {}
            for p in ids:
                vals = [v for v in (first(p), second(p)) if v is not None]
                want[p] = sum(vals) / len(vals) if vals else x[p]
            # супруг без своих связей держится рядом с партнёром
            for p in ids:
                if first(p) is None and second(p) is None:
                    for q, _ in unions.get(p, []):
                        if q in want:
                            want[p] = want[q] + (1 if ids.index(p) > ids.index(q) else -1)
            pack(ids, want)

    gs = sorted(rows)

    def place(iters):
        for g in gs:  # стартовая плотная расстановка в нужном порядке
            pack(rows[g], {p: i * 1.0 for i, p in enumerate(rows[g])})
        for _ in range(iters):
            sweep(gs, down, up)
            sweep(gs[::-1], up, down)

    links = [(a, b, k) for a, b, kids, _ in couples for k in kids]

    def cost():
        # пересечения линий родитель→ребёнок дороже всего, затем ширина и длина линий
        ed = [(gen[a], marker(a, b), x[k]) for a, b, k in links]
        cr = sum(1 for i, e in enumerate(ed) for f in ed[i + 1:]
                 if e[0] == f[0] and (e[1] - f[1]) * (e[2] - f[2]) < -1e-9)
        dev = sum(abs(m - k) for _, m, k in ed)
        # чужие карточки внутри группы братьев и сестёр сбивают с толку
        mix = 0
        for _, _, kids, _ in couples:
            ks = [k for k in kids if k in gen]
            if len(ks) > 1:
                row = rows[gen[ks[0]]]
                ii = [row.index(k) for k in ks]
                mix += sum(1 for p in row[min(ii):max(ii) + 1] if p not in ks and not any(
                    frozenset((p, k)) in spouses for k in ks))
        sp = sum(abs(x[a] - x[b]) for a, b, _, _ in couples if a and b)
        return cr * 20 + mix * 40 + dev + sp * 3 + (max(x.values()) - min(x.values())) * 2

    # поиск порядка: меняем местами соседние блоки (супруги — один блок), пока это
    # уменьшает пересечения и растяжку линий; прямая линия (ось) не двигается
    def blocks(ids):
        out = []
        for p in ids:
            if out and (frozenset((out[-1][-1], p)) in spouses or
                        any(frozenset((out[-1][-1], c)) in spouses and frozenset((p, c)) in spouses for c in ids)):
                out[-1].append(p)
            else:
                out.append([p])
        return out

    place(25)
    best = cost()
    for _ in range(3):
        better = False
        for g in gs:
            i = 0
            while True:
                bl = blocks(rows[g])
                if i >= len(bl) - 1:
                    break
                if any(p in SPINE for p in bl[i] + bl[i + 1]):
                    i += 1
                    continue
                old = rows[g][:]
                bl[i], bl[i + 1] = bl[i + 1], bl[i]
                rows[g][:] = [p for u in bl for p in u]
                place(25)
                c = cost()
                if c < best - 1e-6:
                    best, better = c, True
                else:
                    rows[g][:] = old
                i += 1
        if not better:
            break
    place(80)
    print('порядок:')
    for g in gs:
        print('    %d: %r,' % (g, ' '.join(rows[g])))

    lo = min(x.values())
    for p in P:
        P[p][1] = round(x[p] - lo, 3)
    (D / 'base.json').write_text(json.dumps(base, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('компоновка: ширина %.1f карточек' % (max(x.values()) - lo + 1))


if __name__ == '__main__':
    main()
