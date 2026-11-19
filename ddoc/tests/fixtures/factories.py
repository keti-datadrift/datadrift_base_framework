"""Compatibility path for the toy-data factories.

The generators live in :mod:`ddoc.examples.factories` so they ship with
the package. Tests import them through this path, including the
underscore-prefixed constants, so re-export the whole module namespace.
"""
import ddoc.examples.factories as _factories

globals().update(
    {name: value for name, value in vars(_factories).items() if not name.startswith("__")}
)
