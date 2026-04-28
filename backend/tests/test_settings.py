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

    def test_default_model_provider_key_is_still_required(self) -> None:
        with self.assertRaises(ValueError):
            Settings(
                _env_file=None,
                OPENAI_API_KEY="test-key",
                LLM_DEFAULT_MODEL="claude-3-5-sonnet",
                LLM_ENABLED_MODELS=["gpt-4.1-mini", "claude-3-5-sonnet"],
            )


if __name__ == "__main__":
    unittest.main()
