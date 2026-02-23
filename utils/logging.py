"""Structured logging setup for Meta-Factory."""

import json
import logging
from pathlib import Path
from typing import Any

import structlog


def setup_logging(run_id: str, output_dir: Path, verbose: bool = False) -> structlog.BoundLogger:
    """Configure structlog for this run.

    Logs to both console (INFO+) and file (DEBUG+).
    File: output_dir/run.log (JSON lines).
    Console: ConsoleRenderer when verbose, else JSON.
    """
    log_path = output_dir / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _file_stream = open(log_path, "a", encoding="utf-8")

    def _write_to_file(
        logger: Any, method_name: str, event_dict: dict
    ) -> dict:
        """Processor: append JSON line to run.log."""
        try:
            line = json.dumps(event_dict, default=str) + "\n"
            _file_stream.write(line)
            _file_stream.flush()
        except Exception:
            pass
        return event_dict

    shared = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _write_to_file,
    ]
    console_renderer = (
        structlog.dev.ConsoleRenderer()
        if verbose
        else structlog.processors.JSONRenderer()
    )
    processors = shared + [console_renderer]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # Ensure stdlib root logger sends INFO+ to console
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for h in list(root.handlers):
        root.removeHandler(h)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    root.addHandler(console)
    return structlog.get_logger()
