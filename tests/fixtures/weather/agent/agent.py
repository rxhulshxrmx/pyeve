from pyeve import define_agent
from pyeve.adapters.mock import MockAdapter

agent = define_agent(
    model="mock",
    adapter=MockAdapter(responses=["The weather in Berlin is sunny and 72°F."]),
)
