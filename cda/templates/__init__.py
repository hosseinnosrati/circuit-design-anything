"""Parameterized Golden Circuit Synthesis Library."""

from cda.templates.library import (
    synthesize_sallen_key_lowpass,
    synthesize_twin_t_notch,
    synthesize_rc_lowpass,
    synthesize_instrumentation_amp,
)

__all__ = [
    "synthesize_sallen_key_lowpass",
    "synthesize_twin_t_notch",
    "synthesize_rc_lowpass",
    "synthesize_instrumentation_amp",
]
