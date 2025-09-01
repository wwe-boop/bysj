from typing import Any, Dict


def beam_schedule_hint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a mock beam scheduling hint.

    Input payload example: {"time": t, "users": [...], "budget": {...}}
    Output provides a simple per-user recommended number of beams/sats.
    """
    users = payload.get('users', [])
    hint = {
        'policy': 'cooperative-min',
        'assignments': []
    }
    for u in users:
        hint['assignments'].append({
            'user': u,
            'recommended_beams': 3,
            'recommended_sats': 4
        })
    return hint


