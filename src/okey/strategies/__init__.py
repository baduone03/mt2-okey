"""Karar politikaları: rastgele, açgözlü, seçici ve Monte Carlo."""

from okey.strategies.base import Policy
from okey.strategies.greedy import GreedyPolicy
from okey.strategies.random_policy import RandomPolicy
from okey.strategies.selective import SelectivePolicy

__all__ = ["GreedyPolicy", "Policy", "RandomPolicy", "SelectivePolicy"]
