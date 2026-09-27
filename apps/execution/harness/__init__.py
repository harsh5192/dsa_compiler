"""Harness registry: maps a language slug onto a source generator."""

from __future__ import annotations

from . import c_harness, cpp_harness, java_harness, javascript_harness, nodes, python_harness

#: language slug -> callable(source, problem) -> str | dict[str, str]
#: A ``str`` return is a single-file program; a ``dict`` maps filenames to
#: contents (used by Java, which needs two files).
RENDERERS = {
    "python": python_harness.render,
    "javascript": javascript_harness.render,
    "cpp": cpp_harness.render,
    "java": java_harness.render,
    "c": c_harness.render,
}

__all__ = [
    "RENDERERS",
    "nodes",
    "python_harness",
    "javascript_harness",
    "cpp_harness",
    "java_harness",
    "c_harness",
    "render",
]


def render(language_slug: str, source: str, problem):
    try:
        renderer = RENDERERS[language_slug]
    except KeyError as exc:  # pragma: no cover - guarded by Language validation
        raise ValueError(
            f"No harness is registered for language '{language_slug}'. "
            "Add one in apps.execution.harness.RENDERERS."
        ) from exc
    return renderer(source, problem)
