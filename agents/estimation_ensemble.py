"""Ensemble estimation: Optimist, Pessimist, Realist (Phase 7)."""

from typing import Optional
from librarian import Librarian
from agents.estimator_agent import EstimatorAgent
from contracts import EstimationResult


class OptimistEstimator(EstimatorAgent):
    """Assumes best-case: experienced team, clean code, no surprises."""

    BIAS_PROMPT = """
## Estimation Bias: OPTIMISTIC
You are estimating the BEST REALISTIC CASE. Assume:
- The team is experienced with the tech stack
- Code quality is good, technical debt is manageable
- Integration points work as documented
- No major requirement changes mid-project
Still use PERT, but your 'likely' estimate should lean toward 'optimistic'.
"""
    SYSTEM_PROMPT = BIAS_PROMPT + "\n\n" + EstimatorAgent.SYSTEM_PROMPT


class PessimistEstimator(EstimatorAgent):
    """Assumes worst-case: legacy blocks, scope creep, integration failures."""

    BIAS_PROMPT = """
## Estimation Bias: PESSIMISTIC
You are estimating the WORST REALISTIC CASE. Assume:
- Legacy code is worse than described (Feathers: 'code without tests')
- Integration points have undocumented quirks
- Requirements will change at least once
- The team will encounter at least one major technical block
Still use PERT, but your 'likely' estimate should lean toward 'pessimistic'.
"""
    SYSTEM_PROMPT = BIAS_PROMPT + "\n\n" + EstimatorAgent.SYSTEM_PROMPT


class RealistEstimator(EstimatorAgent):
    """Applies reference class forecasting — what ACTUALLY happens on similar projects."""

    BIAS_PROMPT = """
## Estimation Bias: REALIST (Reference Class Forecasting)
You are estimating based on WHAT ACTUALLY HAPPENS, not what should happen.
- Use the Outside View (Kahneman): how long do projects like this ACTUALLY take?
- Apply the Planning Fallacy correction: add 30-50% to your initial gut estimate
- If legacy systems are involved, multiply integration estimates by 1.5x
Use PERT as normal, but anchor your 'likely' estimate to historical reality, not the plan.
"""
    SYSTEM_PROMPT = BIAS_PROMPT + "\n\n" + EstimatorAgent.SYSTEM_PROMPT
