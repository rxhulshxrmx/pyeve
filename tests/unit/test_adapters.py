def test_anthropic_adapter_importable():
    from pyeve.adapters.anthropic import AnthropicAdapter
    assert AnthropicAdapter is not None


def test_anthropic_adapter_satisfies_protocol():
    from pyeve.adapters.anthropic import AnthropicAdapter
    from pyeve.types import ModelAdapter
    assert isinstance(AnthropicAdapter(), ModelAdapter)


def test_openai_adapter_importable():
    from pyeve.adapters.openai import OpenAIAdapter
    assert OpenAIAdapter is not None


def test_openai_adapter_satisfies_protocol():
    from pyeve.adapters.openai import OpenAIAdapter
    from pyeve.types import ModelAdapter
    assert isinstance(OpenAIAdapter(), ModelAdapter)


def test_sap_adapter_importable():
    from pyeve.adapters.sap import SAPAICoreAdapter
    assert SAPAICoreAdapter is not None


def test_mistral_adapter_importable():
    from pyeve.adapters.mistral import MistralAdapter
    assert MistralAdapter is not None
