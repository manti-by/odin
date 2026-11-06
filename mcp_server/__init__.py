import inspect
import typing


def _patch_typing_eval_type() -> None:
    """Drop pydantic's `prefer_fwd_module` keyword on Python 3.14 pre-releases.

    pydantic (>= 2.13) forwards this keyword to `typing._eval_type`, which only accepts it from the
    final 3.14 release. On the betas `import mcp` raises `TypeError`; the keyword only tweaks
    forward-reference handling, so ignoring it is safe until the interpreter is upgraded.
    """
    original = getattr(typing, "_eval_type", None)
    if original is None or "prefer_fwd_module" in inspect.signature(original).parameters:
        return

    def eval_type(*args: object, **kwargs: object) -> object:
        kwargs.pop("prefer_fwd_module", None)
        return original(*args, **kwargs)

    setattr(typing, "_eval_type", eval_type)  # noqa: B010 - the attribute is private/version-dependent


_patch_typing_eval_type()
