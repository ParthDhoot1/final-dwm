"""Frequent signal-rule mining on the chronological training segment."""

from functools import lru_cache
from typing import Any

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth

from app.services.analytics import SIGNAL_COLUMNS, SIGNAL_LABELS, chronological_split, market_frame


@lru_cache(maxsize=64)
def mine_rules(min_support: float = 0.01, min_confidence: float = 0.5, train_ratio: float = 0.7, algorithm: str = "apriori") -> dict[str, Any]:
    """Mine frequent signal itemsets and next-day rules using training rows only."""
    split, valid = chronological_split(market_frame(), train_ratio)
    # Each training row is labeled with its *next day's* return. Drop the
    # last pre-split row so its label cannot use the first test day's close.
    train = valid.iloc[:max(split - 1, 0)]
    if train.empty:
        return {"rules": [], "train_rows": 0, "test_rows": 0, "split_date": None, "base_rates": {}}

    n = len(train)
    transactions = train[SIGNAL_COLUMNS].fillna(False).astype(bool).copy()
    transactions["NEXT_DAY_UP"] = train["NEXT_DAY_UP"].astype(bool)
    transactions["NEXT_DAY_DOWN"] = train["NEXT_DAY_DOWN"].astype(bool)
    miner = apriori if algorithm == "apriori" else fpgrowth
    itemsets = miner(transactions, min_support=min_support, use_colnames=True, max_len=3)
    rules = []
    base_up = float(transactions["NEXT_DAY_UP"].mean())
    base_down = float(transactions["NEXT_DAY_DOWN"].mean())
    if not itemsets.empty:
        mined_rules = association_rules(itemsets, metric="confidence", min_threshold=min_confidence)
        for _, rule in mined_rules.iterrows():
            antecedent = tuple(sorted(rule["antecedents"]))
            consequent_items = set(rule["consequents"])
            if len(antecedent) not in (1, 2) or not set(antecedent).issubset(SIGNAL_COLUMNS):
                continue
            if consequent_items not in ({"NEXT_DAY_UP"}, {"NEXT_DAY_DOWN"}):
                continue
            consequent = next(iter(consequent_items))
            confidence = float(rule["confidence"])
            lift = float(rule["lift"])
            support = float(rule["support"])
            rules.append({
                "rule_id": "&".join(antecedent) + "=>" + consequent,
                "antecedent": list(antecedent),
                "antecedent_labels": [SIGNAL_LABELS[item] for item in antecedent],
                "consequent": consequent,
                "consequent_label": "Next day up" if consequent == "NEXT_DAY_UP" else "Next day down",
                "support": support,
                "confidence": confidence,
                "lift": lift,
                "count": int(round(support * n)),
                "actionable": lift > 1,
            })

    rules.sort(key=lambda rule: (rule["lift"], rule["confidence"], rule["support"]), reverse=True)
    return {
        "algorithm": algorithm,
        "frequent_itemsets": [
            {"items": sorted(items), "support": float(support), "count": int(round(float(support) * n))}
            for items, support in zip(itemsets["itemsets"], itemsets["support"])
        ] if not itemsets.empty else [],
        "rules": rules[:100],
        "train_rows": n,
        "test_rows": len(valid) - split,
        "split_date": valid.iloc[split]["Date"].date().isoformat() if split < len(valid) else None,
        "train_end_date": train.iloc[-1]["Date"].date().isoformat(),
        "base_rates": {"NEXT_DAY_UP": base_up, "NEXT_DAY_DOWN": base_down},
        "min_support": min_support,
        "min_confidence": min_confidence,
    }
