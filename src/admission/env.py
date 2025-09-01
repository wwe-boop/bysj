from typing import Any, Dict, Tuple
import random


class AdmissionEnv:
    """Minimal admission environment with two actions: ACCEPT/REJECT.

    State is mocked as (utilization, pos_availability)
    Reward favors QoE proxy and positioning availability.
    """

    ACCEPT = 1
    REJECT = 0

    def __init__(self) -> None:
        self.t = 0
        self.state = (0.5, 0.8)

    def reset(self) -> Tuple[float, float]:
        self.t = 0
        self.state = (0.5, 0.8)
        return self.state

    def step(self, action: int) -> Tuple[Tuple[float, float], float, bool, Dict[str, Any]]:
        util, apos = self.state
        # Dynamics (mock)
        util = min(1.0, max(0.0, util + random.uniform(-0.05, 0.05)))
        apos = min(1.0, max(0.0, apos + random.uniform(-0.05, 0.05)))

        # Reward: if accept under low util and decent apos, reward higher
        reward = 0.0
        if action == self.ACCEPT:
            reward = (1.0 - util) * 1.0 + apos * 0.5
        else:
            reward = 0.1  # conservative small reward

        self.t += 1
        done = self.t >= 50
        self.state = (util, apos)
        info = {'t': self.t}
        return self.state, reward, done, info


