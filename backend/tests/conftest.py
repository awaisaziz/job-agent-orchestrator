"""Test configuration.

Isolates the test suite from any developer-local ``backend/.env`` file. Tests
assume an OpenAI-based default model with a dummy key; without pinning it here,
a local ``.env`` that sets a different ``LLM_DEFAULT_MODEL`` (e.g. an Anthropic
model) would make ``Settings`` validation fail at import time. ``os.environ``
values take precedence over the ``.env`` file, so these settings win.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_DEFAULT_MODEL", "gpt-4.1-mini")
os.environ.setdefault("LLM_ENABLED_MODELS", "gpt-4.1-mini,gpt-4o-mini")
