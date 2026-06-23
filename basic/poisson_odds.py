from math import exp, log, lgamma


def _poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return exp(-lam + k * log(lam) - lgamma(k + 1))


def _parse_scores(score_odds):
    listed = []
    for key, odd in score_odds.items():
        if key == 'Any other score':
            continue
        h, g = map(int, key.split('-'))
        listed.append((h, g, 1.0 / float(odd)))
    return listed


def fit_poisson(score_odds):
    listed = _parse_scores(score_odds)
    if not listed:
        return 1.0, 1.0

    total = sum(p for _, _, p in listed)
    probs = [(h, g, p / total) for h, g, p in listed]

    lh0 = max(0.1, sum(h * p for h, g, p in probs))
    la0 = max(0.1, sum(g * p for h, g, p in probs))

    best_ll = float('-inf')
    best_lh, best_la = lh0, la0
    for di in range(-40, 41):
        for dj in range(-40, 41):
            lh = lh0 + di * 0.02
            la = la0 + dj * 0.02
            if lh < 0.05 or la < 0.05:
                continue
            ll = sum(
                p * log(max(_poisson_pmf(h, lh) * _poisson_pmf(g, la), 1e-300))
                for h, g, p in probs)
            if ll > best_ll:
                best_ll = ll
                best_lh, best_la = lh, la

    return best_lh, best_la


def generate_score_odd(home, away, score_odds, dampening=0.5):
    """Generate an odd for a single score by extrapolating from the nearest listed score."""
    lh, la = fit_poisson(score_odds)
    listed_keys = {k for k in score_odds if k != 'Any other score'}

    target_prob = _poisson_pmf(home, lh) * _poisson_pmf(away, la)
    if target_prob < 1e-15:
        return 9999.0

    best_k = None
    best_dist = float('inf')
    best_prob = -1.0
    for k in listed_keys:
        h, g = map(int, k.split('-'))
        dist = abs(h - home) + abs(g - away)
        p = _poisson_pmf(h, lh) * _poisson_pmf(g, la)
        if dist < best_dist or (dist == best_dist and p > best_prob):
            best_dist = dist
            best_prob = p
            best_k = k

    if best_k is None:
        return 9999.0

    anchor_h, anchor_g = map(int, best_k.split('-'))
    anchor_prob = _poisson_pmf(anchor_h, lh) * _poisson_pmf(anchor_g, la)
    anchor_odd = float(score_odds[best_k])
    ratio = anchor_prob / target_prob
    return round(anchor_odd * (ratio ** dampening), 2)
