"""LiteLLM cost tracking callback (Phase 2.3)."""


def _get_swarm_logger_impl():
    try:
        from litellm.integrations.custom_logger import CustomLogger
    except ImportError:
        return None

    class SwarmCostLogger(CustomLogger):
        """Tracks per-call cost and total for the swarm run."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.total_cost = 0.0
            self.calls = []

        def log_success_event(self, kwargs, response_obj, start_time, end_time):
            cost = 0.0
            if response_obj is not None:
                hidden = getattr(response_obj, "_hidden_params", None) or {}
                cost = float(hidden.get("response_cost", 0) or 0)
            self.total_cost += cost
            litellm_params = kwargs.get("litellm_params") or {}
            meta = (litellm_params.get("metadata") or kwargs.get("metadata") or {})
            if not isinstance(meta, dict):
                meta = {}
            model = kwargs.get("model", "unknown")
            tier = meta.get("tier", "?")
            agent = meta.get("agent", "unknown")
            print(f"  [{agent} tier:{tier} {model}] → ${cost:.4f}")
            self.calls.append({"agent": agent, "tier": tier, "model": model, "cost": cost})

        def reset(self):
            self.total_cost = 0.0
            self.calls = []

    return SwarmCostLogger


# Singleton for the cost controller to read
_swarm_cost_logger = None


def get_swarm_cost_logger():
    """Return the global SwarmCostLogger instance (create and register if needed)."""
    global _swarm_cost_logger
    if _swarm_cost_logger is not None:
        return _swarm_cost_logger
    impl = _get_swarm_logger_impl()
    if impl is None:
        class FallbackLogger:
            total_cost = 0.0
            calls = []
            def log_success_event(self, *a, **k): pass
            def reset(self): self.total_cost = 0.0; self.calls = []
        _swarm_cost_logger = FallbackLogger()
    else:
        _swarm_cost_logger = impl()
        try:
            import litellm
            if not litellm.callbacks:
                litellm.callbacks = []
            if _swarm_cost_logger not in litellm.callbacks:
                litellm.callbacks.append(_swarm_cost_logger)
        except Exception:
            pass
    return _swarm_cost_logger
