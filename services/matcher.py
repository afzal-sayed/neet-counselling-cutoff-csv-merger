from collections import defaultdict
from rapidfuzz import fuzz
import pandas as pd
from services.normalizer import expand_abbreviations
from typing import Optional

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
    # Track ALL rounds each (name, state) appears in — used to block same-round merges.
    seen: dict = {}
    for df in sorted(dfs, key=lambda d: int(d['_round'].iloc[0])):
        round_label = ROUND_LABELS.get(int(df['_round'].iloc[0]), 'Unknown')
        for name, state in zip(df['Allotted Institute'], df['State']):
            key = (str(name), str(state))
            seen.setdefault(key, set()).add(round_label)

    by_state: dict = defaultdict(list)
    for (name, state), rounds in seen.items():
        by_state[state].append((name, expand_abbreviations(name), rounds))

    mapping: dict = {}
    match_log: list = []

    for state, entries in by_state.items():
        if len(entries) < 2:
            continue
        originals    = [e[0] for e in entries]
        expanded     = [e[1] for e in entries]
        name_rounds  = [e[2] for e in entries]   # set of round_labels per name
        n = len(originals)

        parent = list(range(n))
        # cluster_rounds[root] = union of all round-sets for every member of that cluster.
        # Before each merge we check whether the two clusters share any round.  If they do,
        # merging them would imply that two different colleges (both appearing in that round)
        # are actually the same college — which cannot be true.  This check is cluster-wide
        # so it also catches transitivity: A⊂clusterX and B⊂clusterY share a round even if
        # A and B themselves don't share one directly.
        cluster_rounds: dict = {i: set(name_rounds[i]) for i in range(n)}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i in range(n):
            for j in range(i + 1, n):
                if fuzz.token_sort_ratio(expanded[i], expanded[j]) < threshold:
                    continue
                ri, rj = find(i), find(j)
                if ri == rj:
                    continue
                if cluster_rounds[ri] & cluster_rounds[rj]:
                    continue  # merging would put same-round colleges in one cluster
                parent[rj] = ri
                cluster_rounds[ri] |= cluster_rounds.pop(rj)

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
                    'round':    sorted(name_rounds[idx])[0],
                    'state':    state,
                })

    return mapping, match_log


def build_course_context(
    dfs: list,
    review_log: list,
    full_log: Optional[list] = None,
) -> list:
    """
    Post-processing step: for each match in review_log, find all (variant, course, round)
    triples across dfs and detect same-round conflicts.
    Returns enriched match groups (one per review_log entry).
    full_log is used for conflict detection so auto-approved variants are included.
    """
    if not review_log:
        return []

    all_log = full_log if full_log is not None else review_log

    # variant → (canonical, state) — from all known matches
    variant_info: dict = {m['original']: (m['matched'], m['state']) for m in all_log}
    # canonical → state — so we can track canonical appearances in the data for conflict detection
    canonical_state: dict = {m['matched']: m['state'] for m in all_log}

    # (canonical, variant, state) → {course → set of round_labels}
    group_courses: dict = defaultdict(lambda: defaultdict(set))
    # (canonical, course) → set of (name, round_label) for conflict detection
    conflict_index: dict = defaultdict(set)
    # canonical → set of round_labels where the canonical name itself appears
    canonical_rounds: dict = defaultdict(set)

    for df in dfs:
        round_label = ROUND_LABELS.get(int(df['_round'].iloc[0]), 'Unknown')
        for inst, course in zip(df['Allotted Institute'], df['Alloted Course']):
            if inst in variant_info:
                canonical, state = variant_info[inst]
                group_courses[(canonical, inst, state)][course].add(round_label)
                conflict_index[(canonical, course)].add((inst, round_label))
            elif inst in canonical_state:
                # The canonical form itself appears in the data — track for conflict detection
                conflict_index[(inst, course)].add((inst, round_label))
                canonical_rounds[inst].add(round_label)

    # Pre-compute conflicting (canonical, course) pairs
    conflict_pairs: set = set()
    for (canonical, course), vr_set in conflict_index.items():
        by_round: dict = defaultdict(set)
        for variant, rnd in vr_set:
            by_round[rnd].add(variant)
        if any(len(vs) > 1 for vs in by_round.values()):
            conflict_pairs.add((canonical, course))

    result = []
    for m in review_log:
        original, canonical, score, state = m['original'], m['matched'], m['score'], m['state']
        courses_raw = group_courses.get((canonical, original, state), {})
        courses = sorted(
            [{'name': c, 'rounds': sorted(rs), 'conflict': (canonical, c) in conflict_pairs}
             for c, rs in courses_raw.items()],
            key=lambda c: (not c['conflict'], c['name']),
        )
        result.append({
            'original': original, 'matched': canonical,
            'score': score, 'state': state, 'courses': courses,
            'canonical_rounds': sorted(canonical_rounds.get(canonical, [])),
        })

    return result


def apply_mapping(df: pd.DataFrame, mapping: dict, exclude_pairs: Optional[set] = None) -> pd.DataFrame:
    df = df.copy()
    if not exclude_pairs:
        df['Allotted Institute'] = df['Allotted Institute'].map(lambda x: mapping.get(x, x))
    else:
        def _remap(row):
            inst = row['Allotted Institute']
            if (inst, row['Alloted Course']) in exclude_pairs:
                return inst
            return mapping.get(inst, inst)
        df['Allotted Institute'] = df.apply(_remap, axis=1)
    return df
