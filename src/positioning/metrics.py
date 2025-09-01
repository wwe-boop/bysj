import json
import math
import os
from typing import Any, Dict, List


def _safe_mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def metrics(t: int, users: List[Any]) -> Dict[str, Any]:
    """Return mock positioning metrics for given time and users.

    If experiments/results/positioning_ablation_example.json exists, use it to
    derive a stable example; otherwise synthesize values.
    """
    base_path = os.path.join(os.getcwd(), 'experiments', 'results', 'positioning_ablation_example.json')
    if os.path.isfile(base_path):
        try:
            with open(base_path, 'r') as f:
                data = json.load(f)
            # Pick FullFeatures as baseline
            full = data.get('FullFeatures', {})
            crlb_mean = float(full.get('crlb', {}).get('mean', 8.0))
            crlb_p95 = float(full.get('crlb', {}).get('p95', 14.0))
            pos_avail = float(full.get('pos_availability', 0.8))
            # Simple mock for others
            return {
                'crlb': {'mean': crlb_mean, 'p95': crlb_p95},
                'gdop': {'mean': max(1.0, crlb_mean / 2.0), 'p95': max(1.2, crlb_p95 / 2.0)},
                'visible_beams': 3.0,
                'coop_sats': 4.0,
                'pos_availability': pos_avail,
                'beam_hint': {'strategy': 'greedy', 'version': 1}
            }
        except Exception:
            pass

    # Fallback synthetic metrics (time-varying)
    phase = (t % 600) / 600.0
    crlb_mean = 6.0 + 2.0 * math.sin(2 * math.pi * phase)
    crlb_p95 = 10.0 + 3.0 * math.cos(2 * math.pi * phase)
    visible = 2 + int(2 * abs(math.sin(2 * math.pi * phase)))
    coop = 3 + int(2 * abs(math.cos(2 * math.pi * phase)))
    pos_avail = max(0.0, min(1.0, 0.75 + 0.1 * math.sin(2 * math.pi * phase)))
    return {
        'crlb': {'mean': crlb_mean, 'p95': crlb_p95},
        'gdop': {'mean': max(1.0, crlb_mean / 2.0), 'p95': max(1.2, crlb_p95 / 2.0)},
        'visible_beams': float(visible),
        'coop_sats': float(coop),
        'pos_availability': pos_avail,
        'beam_hint': {'strategy': 'greedy', 'version': 1}
    }


