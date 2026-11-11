"""Test bootstrap for the MCP server suite.

``pydantic`` 2.14 (pulled in through ``mcp``) targets CPython 3.14 final and passes
``prefer_fwd_module`` to ``typing._eval_type``. Pre-release 3.14 interpreters, such as the
3.14.0b4 build some development machines still use, reject that keyword, so every import
through ``mcp`` fails during collection. CI runs a stable 3.14 where the keyword exists and
the shim below does nothing.
"""

import inspect
import typing


def _patch_eval_type() -> None:
    """Drop the ``prefer_fwd_module`` keyword when the interpreter does not accept it."""
    # `_eval_type` is private and missing from the type stubs, hence the module dict access.
    original = typing.__dict__["_eval_type"]
    if "prefer_fwd_module" in inspect.signature(original).parameters:
        return

    def eval_type(*args, **kwargs):
        kwargs.pop("prefer_fwd_module", None)
        return original(*args, **kwargs)

    typing.__dict__["_eval_type"] = eval_type


_patch_eval_type()
