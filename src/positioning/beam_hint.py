from typing import Any, Dict, List, Tuple
import math


def _normalize(value: float, min_v: float, max_v: float) -> float:
    if max_v <= min_v:
        return 0.0
    return max(0.0, min(1.0, (value - min_v) / (max_v - min_v)))


def _angular_distance_deg(a1: float, a2: float) -> float:
    diff = abs(a1 - a2) % 360.0
    return min(diff, 360.0 - diff)


def beam_schedule_hint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Backward-compatible placeholder used by legacy API.

    Prefer using `generate_beam_hint_with_state` when network_state and positioning_calculator
    are available in the caller.
    """
    users = payload.get('users', [])
    k = payload.get('budget', {}).get('beams_per_user', 2)
    return {
        'policy': 'heuristic-fallback',
        'assignments': [
            {'user': u, 'recommendations': [{'sat_id': i, 'score': 0.5} for i in range(k)}]
            for u in users
        ]
    }


def generate_beam_hint_with_state(
    time_s: float,
    users: List[Dict[str, Any]],
    budget: Dict[str, Any],
    network_state: Any,
    positioning_calculator: Any,
) -> Dict[str, Any]:
    """Generate beam/satellite recommendations per user.

    Scoring (greedy): 0.5*fim_proxy + 0.3*sinr_norm + 0.2*geometry_diversity
    - fim_proxy: elevation_norm as a proxy of FIM gain (higher elevation -> better geometry/FIM)
    - sinr_norm: normalized SINR derived from signal_strength_dbm - noise_power_dbm
    - geometry_diversity: prefer larger azimuthal spread among selected candidates
    """
    beams_per_user = budget.get('beams_per_user', 2)
    noise_dbm = getattr(positioning_calculator, 'noise_power_dbm', -140.0)

    assignments = []

    for user in users:
        lat = user.get('lat') or user.get('latitude')
        lon = user.get('lon') or user.get('longitude')
        user_id = user.get('id') or user.get('userId') or user.get('user_id')
        if lat is None or lon is None:
            assignments.append({'user': user, 'recommendations': []})
            continue

        # 1) enumerate visible satellites with positioning attributes
        visible_sats = positioning_calculator.get_visible_satellites((lat, lon), time_s, network_state)

        # Pre-compute min/max for normalization
        if visible_sats:
            min_sig = min(s['signal_strength_dbm'] for s in visible_sats)
            max_sig = max(s['signal_strength_dbm'] for s in visible_sats)
        else:
            min_sig, max_sig = -140.0, -80.0

        # 2) Greedy selection maximizing composite score with geometry diversity
        selected: List[Dict[str, Any]] = []
        selected_azimuths: List[float] = []

        candidates = []
        for sat in visible_sats:
            elevation = sat.get('elevation', 0.0)
            azimuth = sat.get('azimuth', 0.0)
            sig_dbm = sat.get('signal_strength_dbm', -120.0)
            sinr_db = sig_dbm - noise_dbm
            fim_proxy = elevation / 90.0  # [0,1]
            sinr_norm = _normalize(sinr_db, (min_sig - noise_dbm), (max_sig - noise_dbm))
            # first pass without geometry
            base_score = 0.5 * fim_proxy + 0.3 * sinr_norm
            candidates.append({
                'sat_id': sat['id'],
                'elevation': elevation,
                'azimuth': azimuth,
                'sinr_db': sinr_db,
                'base_score': base_score,
            })

        # Greedy picking with geometry spread bonus
        for _ in range(max(0, int(beams_per_user))):
            best = None
            best_score = -1.0
            for cand in candidates:
                # geometry diversity: distance to nearest selected azimuth
                if selected_azimuths:
                    min_dist = min(_angular_distance_deg(cand['azimuth'], az) for az in selected_azimuths)
                    geometry_norm = min_dist / 180.0  # [0,1]
                else:
                    geometry_norm = 1.0
                score = cand['base_score'] + 0.2 * geometry_norm
                if score > best_score:
                    best_score = score
                    best = cand
            if best is None:
                break
            selected.append({'sat_id': best['sat_id'], 'score': round(best_score, 4)})
            selected_azimuths.append(best['azimuth'])
            # remove chosen id
            candidates = [c for c in candidates if c['sat_id'] != best['sat_id']]

        assignments.append({
            'user': {'id': user_id, 'lat': lat, 'lon': lon},
            'recommendations': selected
        })

    return {
        'policy': 'visibility-fim-sinr-geometry-greedy',
        'assignments': assignments
    }


