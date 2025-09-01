from typing import Tuple
import random

from admission.env import AdmissionEnv


def train(episodes: int = 5) -> Tuple[float, float]:
    env = AdmissionEnv()
    total = 0.0
    steps = 0
    for _ in range(episodes):
        s = env.reset()
        done = False
        while not done:
            # random policy placeholder
            action = random.choice([env.ACCEPT, env.REJECT])
            s, r, done, info = env.step(action)
            total += r
            steps += 1
    return total, steps


if __name__ == '__main__':
    total, steps = train(episodes=3)
    print(f"Finished: reward_sum={total:.3f}, steps={steps}")


