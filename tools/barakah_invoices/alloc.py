"""Pick the lines of the 10 «زيادة البركة» invoices from ``items.json``.

Each invoice's lines must add up exactly to its pre-tax amount, and every line
amount is a multiple of 0.20 SAR so its 15% VAT is a whole halala (the per-line
VAT then sums exactly to the Excel VAT). No item appears in two invoices.
Writes ``alloc.json``; needs ``ortools`` (``pip install ortools``).

Run:  python tools/barakah_invoices/alloc.py
"""

from __future__ import annotations

import json
import math
import os
import random

from ortools.sat.python import cp_model

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = [26800, 23400, 29000, 18000, 23500, 24000, 27400, 30400, 21000, 27800]

items = json.load(open(os.path.join(HERE, "items.json"), encoding="utf-8"))
pc = [int(round(float(it["price"]) * 100)) for it in items]
step = [20 // math.gcd(c, 20) for c in pc]
n, J = len(items), len(TARGETS)

# Shuffle the catalogue and give each invoice its own pool of items, so no
# item repeats across invoices and each invoice mixes different kinds.
rng = random.Random(2026)
order = list(range(n))
rng.shuffle(order)
pools = [order[j::J] for j in range(J)]


def solve(pool: list[int], T: int) -> dict[int, int]:
    m = cp_model.CpModel()
    k, y = {}, {}
    for i in pool:
        cap = min(400 // step[i], int(T * 100 * 0.30) // (pc[i] * step[i]))
        k[i] = m.NewIntVar(0, cap, f"k{i}")
        y[i] = m.NewBoolVar(f"y{i}")
        m.Add(k[i] == 0).OnlyEnforceIf(y[i].Not())
        # at least 5 units and at least 3% of the invoice on every line
        m.Add(k[i] * step[i] >= 5).OnlyEnforceIf(y[i])
        m.Add(k[i] * step[i] * pc[i] >= int(T * 100 * 0.03)).OnlyEnforceIf(y[i])
    m.Add(sum(k[i] * step[i] * pc[i] for i in pool) == T * 100)
    # the printed invoice shows names, not codes: no two lines with the same name
    for name in {items[i]["name"] for i in pool}:
        m.Add(sum(y[i] for i in pool if items[i]["name"] == name) <= 1)
    m.Add(sum(y.values()) >= 6)
    m.Add(sum(y.values()) <= 7)
    m.Maximize(sum(rng.randint(0, 100) * y[i] for i in pool))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = 20
    s.parameters.num_workers = 8
    s.parameters.random_seed = 11
    status = s.Solve(m)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), (T, s.StatusName(status))
    return {i: s.Value(k[i]) * step[i] for i in pool}


qty = [solve(pool, T) for pool, T in zip(pools, TARGETS)]

out = []
for j, T in enumerate(TARGETS):
    lines = []
    for i in sorted(qty[j], key=lambda i: items[i]["code"]):
        q = qty[j][i]
        if q:
            it = items[i]
            lines.append({"code": it["code"], "name": it["name"], "qty": q, "price": it["price"]})
    total = sum(ln["qty"] * int(round(float(ln["price"]) * 100)) for ln in lines) / 100
    print(T, total, len(lines))
    out.append(lines)
with open(os.path.join(HERE, "alloc.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
