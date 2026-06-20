from pyeve.adapters.mistral import MistralAdapter
from pyeve.adapters.sap import SAPAICoreAdapter
from pyeve.adapters.mock import MockAdapter
from pyeve.types import ModelAdapter


def test_mistral_adapter_importable():
    assert MistralAdapter is not None


def test_mistral_adapter_satisfies_protocol():
    assert isinstance(MistralAdapter.__new__(MistralAdapter), ModelAdapter)


def test_sap_adapter_importable():
    assert SAPAICoreAdapter is not None


def test_mock_adapter_importable():
    assert MockAdapter is not None


def test_mock_adapter_satisfies_protocol():
    assert isinstance(MockAdapter(responses=[]), ModelAdapter)
