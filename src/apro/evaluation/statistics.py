"""Pure deterministic statistical computation, bootstrap, and CIs."""

import math
import random
from collections.abc import Callable, Sequence


def compute_proportion_ci(
    successes: int,
    total: int,
    confidence_level: float = 0.95,
) -> tuple[float, float]:
    """Compute Wilson score interval for binary proportions.

    Follows NIST e-Handbook recommendations for bounded discrete proportions.
    """
    if total <= 0:
        return 0.0, 0.0

    p = successes / total
    # Critical value z for given confidence level (e.g. 1.96 for 95%)
    if abs(confidence_level - 0.95) < 0.01:
        z = 1.95996
    elif abs(confidence_level - 0.99) < 0.01:
        z = 2.57583
    elif abs(confidence_level - 0.90) < 0.01:
        z = 1.64485
    else:
        z = 1.95996

    z2 = z * z
    denom = 1 + z2 / total
    center = (p + z2 / (2 * total)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z2 / (4 * total)) / total)) / denom

    ci_lower = max(0.0, center - margin)
    ci_upper = min(1.0, center + margin)
    return round(ci_lower, 4), round(ci_upper, 4)


def bootstrap_case_metric(
    records: list[object],
    metric_fn: Callable[[list[object]], float],
    confidence_level: float = 0.95,
    iterations: int = 1000,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Compute deterministic bootstrap CI with CASE as the resampling unit."""
    n = len(records)
    if n == 0:
        return 0.0, 0.0, 0.0

    point_estimate = metric_fn(records)
    if n == 1 or iterations <= 1:
        return point_estimate, point_estimate, point_estimate

    rng = random.Random(seed)
    boot_estimates: list[float] = []

    for _ in range(iterations):
        sample = [records[rng.randint(0, n - 1)] for _ in range(n)]
        val = metric_fn(sample)
        boot_estimates.append(val)

    boot_estimates.sort()
    alpha = 1.0 - confidence_level
    lower_idx = int(math.floor((alpha / 2.0) * iterations))
    upper_idx = int(math.ceil((1.0 - alpha / 2.0) * iterations)) - 1

    lower_idx = max(0, min(lower_idx, iterations - 1))
    upper_idx = max(0, min(upper_idx, iterations - 1))

    ci_lower = round(boot_estimates[lower_idx], 4)
    ci_upper = round(boot_estimates[upper_idx], 4)
    return round(point_estimate, 4), ci_lower, ci_upper


def compute_paired_bootstrap_ci(
    differences: Sequence[int | float],
    confidence_level: float = 0.95,
    iterations: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute deterministic bootstrap CI for paired case-level differences."""
    n = len(differences)
    if n == 0:
        return 0.0, 0.0

    if n == 1 or iterations <= 1:
        val = float(differences[0])
        return round(val, 4), round(val, 4)

    rng = random.Random(seed)
    boot_means: list[float] = []

    for _ in range(iterations):
        sample = [differences[rng.randint(0, n - 1)] for _ in range(n)]
        boot_means.append(sum(sample) / n)

    boot_means.sort()
    alpha = 1.0 - confidence_level
    lower_idx = int(math.floor((alpha / 2.0) * iterations))
    upper_idx = int(math.ceil((1.0 - alpha / 2.0) * iterations)) - 1

    lower_idx = max(0, min(lower_idx, iterations - 1))
    upper_idx = max(0, min(upper_idx, iterations - 1))

    return round(boot_means[lower_idx], 4), round(boot_means[upper_idx], 4)


def compute_paired_randomization_p_value(
    differences: Sequence[int | float],
    iterations: int = 1000,
    seed: int = 42,
) -> float:
    """Compute a deterministic two-sided paired randomization (sign-flip) p-value.

    Under the null hypothesis of no differential effect (H0: E[difference] = 0),
    each pair difference is equally likely to be positive or negative.
    The test evaluates how frequently a random sign-flip permutation produces
    an absolute sum at least as extreme as the observed absolute sum.

    Methodology:
        1. Compute observed absolute sum: T_obs = |sum(differences)|.
        2. If T_obs == 0 or empty, return 1.0 (no evidence against H0).
        3. For each iteration b in {1, ..., B}, assign an independent random sign
           s_i in {-1, +1} to each non-zero difference and compute
           T_b = |sum(s_i * d_i)|.
        4. Calculate two-sided p-value as:
           p = (sum(I(T_b >= T_obs)) + 1) / (B + 1)
           following standard exact permutation test formulation
           (Davison & Hinkley 1997, Phipson & Smyth 2010), ensuring p in (0, 1]
           and strictly avoiding p = 0.

    Args:
        differences: Sequence of case-level paired differences (e.g. APRO - Baseline).
        iterations: Number of Monte Carlo sign-flip iterations.
        seed: Deterministic random seed for reproducibility.

    Returns:
        Two-sided p-value in the range [0.0, 1.0].
    """
    n = len(differences)
    if n == 0:
        return 1.0

    obs_stat = abs(sum(differences))
    if obs_stat == 0:
        return 1.0

    if iterations <= 0:
        return 1.0

    non_zeros = [d for d in differences if d != 0]
    if not non_zeros:
        return 1.0

    rng = random.Random(seed)
    extreme_count = 0

    for _ in range(iterations):
        perm_sum = sum(d if rng.getrandbits(1) else -d for d in non_zeros)
        if abs(perm_sum) >= obs_stat - 1e-9:
            extreme_count += 1

    p_val = (extreme_count + 1) / (iterations + 1)
    return float(round(p_val, 6))


def adjust_p_values_holm(p_values: list[float]) -> list[float]:
    """Adjust p-values using the Holm step-down method (Holm-Bonferroni)."""
    m = len(p_values)
    if m <= 1:
        return p_values

    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * m

    cum_max = 0.0
    for rank, (orig_idx, p_val) in enumerate(indexed):
        multiplier = m - rank
        adj = min(1.0, p_val * multiplier)
        adj = max(adj, cum_max)  # enforce monotonicity
        cum_max = adj
        adjusted[orig_idx] = round(adj, 6)

    return adjusted


def compute_cohens_h(p1: float, p2: float) -> float:
    """Compute Cohen's h effect size for the difference between two proportions."""
    phi1 = 2 * math.asin(math.sqrt(max(0.0, min(1.0, p1))))
    phi2 = 2 * math.asin(math.sqrt(max(0.0, min(1.0, p2))))
    return float(round(phi1 - phi2, 4))


def compute_cohens_d(x: list[float], y: list[float]) -> float:
    """Compute Cohen's d effect size for two continuous samples."""
    nx = len(x)
    ny = len(y)
    if nx < 2 or ny < 2:
        return 0.0

    mean_x = sum(x) / nx
    mean_y = sum(y) / ny
    var_x = sum((val - mean_x) ** 2 for val in x) / (nx - 1)
    var_y = sum((val - mean_y) ** 2 for val in y) / (ny - 1)

    pooled_sd = math.sqrt(((nx - 1) * var_x + (ny - 1) * var_y) / (nx + ny - 2))
    if pooled_sd == 0:
        return 0.0
    return float(round((mean_x - mean_y) / pooled_sd, 4))
