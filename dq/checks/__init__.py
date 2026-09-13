"""Import every check module so that the registry is populated. Order here is the report order."""
from . import structure, config_checks, instruction_checks, verifier_checks, leakage_checks, solution_checks  # noqa: F401
from . import category_checks, url_checks, extra_checks, execution_checks, llm_judge  # noqa: F401
from .base import REGISTRY, Check, register  # noqa: F401
