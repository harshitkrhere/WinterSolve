# Plugins (status: not yet)

WinterSolve has no plugin loader today, on purpose. The internal structure is
already plugin-shaped, so a loader can be added when real third-party
analyzers exist, without redesigning the core.

## What is already in place

- Every analyzer is a module with one public function and a frozen result type.
- The workflow registry (`workflows/registry.py`) is the single list of public
  commands and their output formats.
- The AI provider interface (`providers/base.py`) is a one-method protocol that
  vendors and local models can implement in a few dozen lines.
- Renderers are pure functions from result to string.

## What a future plugin would need

- A stable result-type contract (frozen dataclasses with documented fields).
- Explicit registration (no import-time magic, no scanning site-packages).
- The same rules as built-in modules: offline unless documented, structured
  output, tests, redaction before anything leaves the machine.

## How to propose one

Open an issue describing the developer problem, the inputs, and the output
shape. If the analyzer is broadly useful it probably belongs in the core; if it
is specific to one stack or company, it is the first candidate for the plugin
surface.
