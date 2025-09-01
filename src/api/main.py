from flask import Flask, request, jsonify
import json
import time
from statistics import mean

from positioning.metrics import metrics as pos_metrics
from positioning.beam_hint import beam_schedule_hint
from dsroq.core import DSROQEngine
from hypatia.hypatia_adapter import HypatiaAdapter
from admission.env import AdmissionEnv


app = Flask(__name__)
_hypatia = HypatiaAdapter()
_dsroq = DSROQEngine()
_adm_env = AdmissionEnv()


@app.get('/api/positioning/metrics')
def get_positioning_metrics():
    try:
        t = int(request.args.get('time', int(time.time())))
    except Exception:
        t = int(time.time())
    users_raw = request.args.get('users', '[]')
    try:
        users = json.loads(users_raw)
    except Exception:
        users = []
    return jsonify(pos_metrics(t, users))


@app.post('/api/positioning/beam_hint')
def get_beam_hint():
    payload = request.json or {}
    return jsonify(beam_schedule_hint(payload))


@app.get('/api/stats/qoe')
def get_qoe_stats():
    # Mock QoE stats for dashboard
    return jsonify({'mean': 4.1, 'ci95': 0.08})


@app.get('/api/stats/admission')
def get_admission_stats():
    # Mock rates for dashboard
    return jsonify({'admission_rate': 0.76, 'rejection_rate': 0.18, 'degradation_rate': 0.06})


@app.post('/api/admission/decision')
def admission_decision():
    """Minimal decision: heuristic based on utilization and positioning availability."""
    payload = request.json or {}
    try:
        t = int(payload.get('time', int(time.time())))
    except Exception:
        t = int(time.time())
    users = payload.get('users', [])
    pos = pos_metrics(t, users)
    util = mean(_hypatia.get_link_utilization()) if _hypatia.get_link_utilization() else 0.5
    a_pos = float(pos.get('pos_availability', 0.75))
    # Heuristic: accept if utilization below 0.7 and positioning availability >= 0.75
    action = 'ACCEPT' if (util < 0.7 and a_pos >= 0.75) else 'REJECT'
    return jsonify({'action': action, 'util_avg': util, 'pos_availability': a_pos, 'time': t})


@app.post('/api/admission/allocate')
def admission_allocate():
    """Route and allocate for a flow using DSROQ engine over Hypatia topology."""
    payload = request.json or {}
    flow = payload.get('flow', {})
    try:
        t = int(payload.get('time', int(time.time())))
    except Exception:
        t = int(time.time())
    topo = _hypatia.get_topology_at_time(t)
    caps = _hypatia.get_link_capacity()
    route, bw = _dsroq.route_and_allocate(flow, topo, caps)
    _hypatia.add_flow_to_network(flow, route, bw)
    _dsroq.apply_schedule(_hypatia.get_current_flows())
    return jsonify({'accepted': True, 'route': route, 'bandwidth': bw, 'time': t})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


