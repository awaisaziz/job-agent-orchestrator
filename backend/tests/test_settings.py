import unittest

from app.core.config import Settings


class SettingsTests(unittest.TestCase):
    def test_single_provider_key_filters_enabled_models(self) -> None:
        settings = Settings(
            _env_file=None,
            OPENAI_API_KEY="test-key",
            LLM_DEFAULT_MODEL="gpt-4.1-mini",
            LLM_ENABLED_MODELS=[
                "gpt-4.1-mini",
                "gpt-4o-mini",
                "claude-3-5-sonnet",
                "grok-3-mini",
            ],
        )

        self.assertEqual(settings.llm_enabled_models, ["gpt-4.1-mini", "gpt-4o-mini"])

    def test_default_model_auto_switches_to_configured_provider(self) -> None:
        # Default names an Anthropic model but only an OpenAI key is set — the app
        # should auto-select a working OpenAI model instead of erroring, so dropping
        # in only OPENAI_API_KEY (or GROK_API_KEY) "just works".
        settings = Settings(
            _env_file=None,
            OPENAI_API_KEY="test-key",
            LLM_DEFAULT_MODEL="claude-3-5-sonnet",
            LLM_ENABLED_MODELS=["gpt-4.1-mini", "claude-3-5-sonnet"],
        )

        self.assertIn("gpt", settings.llm_default_model)
        self.assertTrue(all("gpt" in model for model in settings.llm_enabled_models))
        self.assertIn(settings.llm_default_model, settings.llm_enabled_models)

    def test_grok_key_only_auto_selects_grok_default(self) -> None:
        # Explicit empty keys override the dummy OPENAI_API_KEY set in conftest so
        # only Grok is configured for this case.
        settings = Settings(
            _env_file=None,
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="",
            GROK_API_KEY="test-key",
            LLM_DEFAULT_MODEL="claude-3-5-sonnet",
            LLM_ENABLED_MODELS=["grok-3-mini", "grok-3", "claude-3-5-sonnet"],
        )

        self.assertIn("grok", settings.llm_default_model)

    def test_no_keys_boots_in_deterministic_demo_mode(self) -> None:
        # No provider keys at all — the app must still boot (deterministic tailoring)
        # rather than raising, and keep the configured default name for display.
        settings = Settings(
            _env_file=None,
            OPENAI_API_KEY="",
            ANTHROPIC_API_KEY="",
            GROK_API_KEY="",
            LLM_DEFAULT_MODEL="claude-3-5-sonnet",
            LLM_ENABLED_MODELS=["claude-3-5-sonnet"],
        )

        self.assertFalse(settings.llm_live_mode)
        self.assertEqual(settings.llm_default_model, "claude-3-5-sonnet")
        self.assertEqual(settings.llm_enabled_models, ["claude-3-5-sonnet"])


if __name__ == "__main__":
    unittest.main()
