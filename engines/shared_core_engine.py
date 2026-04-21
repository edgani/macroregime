"""engines/shared_core_engine.py"""
from __future__ import annotations
from typing import Dict

from config.settings import REGIME_PRIOR_MODE, get_prior_strength, get_regime_prior
from utils.math_utils import clamp01, softmax_dict


def _compute_global_quad(quad: dict, macro: dict) -> str:
    """Compute global quad from structural + EM cross-check."""
    s_quad = quad.get('structural_quad', quad.get('current_quad', 'Q?'))
    m_quad = quad.get('monthly_quad', s_quad)
    eem_1m = macro.get('eem_1m', 0.0)
    oil_3m = macro.get('oil_3m', 0.0)
    dxy_1m = macro.get('dxy_1m', 0.0)
    lei_3m = macro.get('lei_3m', 0.0)

    em_score = 0.0
    if eem_1m > 0.03:
        em_score += 0.2
    if oil_3m > 0.05:
        em_score += 0.2
    if dxy_1m < -0.01:
        em_score += 0.15
    if lei_3m < -0.01:
        em_score -= 0.15

    if s_quad == m_quad:
        return s_quad
    if s_quad in ('Q2', 'Q3') and m_quad in ('Q2', 'Q3'):
        return s_quad if s_quad == 'Q3' else m_quad
    if s_quad in ('Q1', 'Q4') and m_quad in ('Q1', 'Q4'):
        return s_quad if s_quad == 'Q1' else m_quad
    if em_score > 0.2 and s_quad in ('Q2', 'Q3'):
        return s_quad
    if em_score < -0.1 and m_quad in ('Q1', 'Q4'):
        return m_quad
    return s_quad


class SharedCoreEngine:
    """Shared regime resolution logic."""

    def _resolve_regime_stack(self, *, quad: dict, features: dict) -> dict:
        macro = features.get('macro', {})
        global_q = _compute_global_quad(quad, macro)
        return {
            'global_quad': global_q,
            'structural_quad': quad.get('structural_quad', quad.get('current_quad', 'Q?')),
            'monthly_quad': quad.get('monthly_quad', 'Q?'),
        }
