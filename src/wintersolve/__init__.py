"""WinterSolve: offline-first repository intelligence for developers.

The public entry points are the ``wintersolve`` command (see ``wintersolve.cli``)
and the analyzer functions in ``wintersolve.modules``, which return plain
dataclasses you can render or serialise however you like.
"""

from wintersolve.logging_config import configure_logging, get_logger, set_log_level

# Single source of truth for the version; pyproject.toml reads it at build time.
__version__ = "0.3.1"

__all__ = ["__version__", "configure_logging", "get_logger", "set_log_level"]
