"""Karar politikaları: rastgele, açgözlü ve (ileride) Monte Carlo."""

from okey.strategies.base import Policy
from okey.strategies.greedy import GreedyPolicy
from okey.strategies.random_policy import RandomPolicy

__all__ = ["GreedyPolicy", "Policy", "RandomPolicy"]
