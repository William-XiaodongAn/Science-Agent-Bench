"""dq: automatic data-quality verifier for Harbor-format science-agent tasks.

A first filter before the human review committee: programmatic checks (structure, configuration, instruction/verifier
coherence, verifier sanity, answer leakage and reward-hacking surfaces, URLs, categorisation), optional execution
checks (docker build, oracle passes, nop fails) and an optional advisory LLM judge (solvable, verifiable, domain and
tier fit, capability gain). Every result carries a pass/warn/fail status and a reason.
"""
__version__ = "0.1.0"
