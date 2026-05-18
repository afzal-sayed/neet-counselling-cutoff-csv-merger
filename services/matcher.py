from collections import defaultdict
from rapidfuzz import fuzz
import pandas as pd
from services.normalizer import expand_abbreviations

ROUND_LABELS = {
    1: 'Round 1', 2: 'Round 2', 3: 'Round 3',
    4: 'Stray Vacancy', 5: 'Sp.Stray Vacancy',
}
THRESHOLD = 90
MATCH_THRESHOLD = 88


def build_fuzzy_mapping(
    dfs: list,
    threshold: int = MATCH_THRESHOLD,
) -> tuple:
    seen: dict = {}
    for df in sorted(dfs, key=lambda d: int(d['_round'].iloc[0])):
        round_label = ROUND_LABELS.get(int(df['_round'].iloc[0]), 'Unknown')
        for name, state in zip(df['Allotted Institute'], df['State']):
            key = (str(name), str(state))
            if key not in seen:
                seen[key] = round_label

    by_state: dict = defaultdict(list)
    for (name, state), round_label in seen.items():
        by_state[state].append((name, expand_abbreviations(name), round_label))

    mapping: dict = {}
    match_log: list = []

    for state, entries in by_state.items():
        if len(entries) < 2:
            continue
        originals = [e[0] for e in entries]
        expanded  = [e[1] for e in entries]
        round_labels = [e[2] for e in entries]
        n = len(originals)

        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i in range(n):
            for j in range(i + 1, n):
                if fuzz.token_sort_ratio(expanded[i], expanded[j]) >= threshold:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[rj] = ri

        clusters: dict = defaultdict(list)
        for i in range(n):
            clusters[find(i)].append(i)

        for root, members in clusters.items():
            if len(members) < 2:
                continue
            canonical_idx = members[0]
            canonical_name = originals[canonical_idx]
            for idx in members[1:]:
                variant = originals[idx]
                score = fuzz.token_sort_ratio(expanded[canonical_idx], expanded[idx])
                mapping[variant] = canonical_name
                match_log.append({
                    'original': variant,
                    'matched':  canonical_name,
                    'score':    score,
                    'round':    round_labels[idx],
                    'state':    state,
                })

    return mapping, match_log


def apply_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    df = df.copy()
    df['Allotted Institute'] = df['Allotted Institute'].map(
        lambda x: mapping.get(x, x)
    )
    return df
