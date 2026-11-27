"""Offline evaluation infrastructure for the RAGIN causal ablation.

This package is deliberately side-effect free at import time. It provides the
run-contract preflight, the two-track record contract, closed-loop scripted
attacker policies, the prespecified session-level competing-risks analysis, the
blind human-evaluation packet hooks, and the immutable release-manifest builder.

No module here invokes a language model, opens a public listener, pulls an
image, contacts a provider, or treats an unmeasured arm as measured. Anything
that is not established is reported as ``NOT_ESTABLISHED`` or ``NOT_READY``.
"""

from ragin.evaluation.ablation_contract import (
    DESIGN_INVALID,
    DESIGN_VALID,
    EXECUTION_NOT_READY,
    EXECUTION_READY,
    Blocker,
    ContractRefusal,
    ReadinessReport,
    assert_execution_ready,
    build_child_env,
    evaluate_readiness,
    load_contract,
    validate_design,
)

__all__ = [
    "DESIGN_INVALID",
    "DESIGN_VALID",
    "EXECUTION_NOT_READY",
    "EXECUTION_READY",
    "Blocker",
    "ContractRefusal",
    "ReadinessReport",
    "assert_execution_ready",
    "build_child_env",
    "evaluate_readiness",
    "load_contract",
    "validate_design",
]
