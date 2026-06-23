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


def generate_score_odd(home, away, score_odds):
    """Generate an odd for a single score using Poisson fitted to existing odds."""
    lh, la = fit_poisson(score_odds)
    listed_keys = {k for k in score_odds if k != 'Any other score'}

    target_prob = _poisson_pmf(home, lh) * _poisson_pmf(away, la)
    if target_prob < 1e-15:
        return 9999.0

    listed_poisson = sum(
        _poisson_pmf(int(k.split('-')[0]), lh) * _poisson_pmf(int(k.split('-')[1]), la)
        for k in listed_keys)
    unlisted_poisson = 1.0 - listed_poisson

    if 'Any other score' in score_odds:
        any_other_implied = 1.0 / float(score_odds['Any other score'])
    else:
        listed_implied = sum(1.0 / float(score_odds[k]) for k in listed_keys)
        margin = listed_implied / listed_poisson if listed_poisson > 1e-15 else 1.0
        any_other_implied = unlisted_poisson * margin

    if unlisted_poisson < 1e-15:
        return 9999.0

    share = target_prob / unlisted_poisson
    return round(1.0 / (share * any_other_implied), 2)
