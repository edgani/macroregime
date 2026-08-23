from __future__ import annotations
import numpy as np
import pandas as pd


def _finite(x):
    try:
        return np.isfinite(float(x))
    except Exception:
        return False


def _scenario_counts(row):
    sup = str(row.get('supporting_evidence', ''))
    con = str(row.get('contradicting_evidence', ''))
    ns = 0 if not sup or sup.startswith('None') else len([x for x in sup.split(';') if x.strip()])
    nc = 0 if not con or con.startswith('None') else len([x for x in con.split(';') if x.strip()])
    return ns, nc


def operational_posture(state, scenario_df, crash):
    """Operational/research posture, deliberately not an alpha signal."""
    active = crash.get('active_phases') or []
    watch = crash.get('watch_phases') or []
    if active:
        return {
            'posture': 'RISK REVIEW',
            'read': 'An acute crash-mechanism phase has active evidence in the loaded subset.',
            'do': 'Prioritize exposure reduction / hedge review before adding directional risk.',
            'next': 'Wait for funding, credit and liquidation pressure to normalize before re-entry research.',
            'trade_action': 'NO TRADE',
        }

    balances = {}
    if isinstance(scenario_df, pd.DataFrame) and len(scenario_df):
        for _, r in scenario_df.iterrows():
            ns, nc = _scenario_counts(r)
            balances[str(r.get('type'))] = ns - nc
    base = balances.get('BASE', 0)
    comp = balances.get('COMPETING', 0)
    tail = balances.get('TAIL', 0)

    if tail >= 2 or watch:
        return {
            'posture': 'DEFENSIVE / SELECTIVE',
            'read': 'Deterioration evidence is strong enough to keep broad risk-taking selective.',
            'do': 'Avoid broad beta. Focus only on opportunities with company-specific cash-flow capture or clean hedges.',
            'next': 'Credit/funding normalization would relax the defensive posture; further deterioration would escalate it.',
            'trade_action': 'NO TRADE',
        }
    if comp >= 2 and comp > base:
        return {
            'posture': 'RATE-SENSITIVE SELECTIVITY',
            'read': 'Sticky inflation / long-rate pressure currently has the stronger evidence balance.',
            'do': 'Prefer research on cash-flow resilience and beneficiaries of the bottleneck; avoid indiscriminate long-duration exposure.',
            'next': 'Cooling inflation plus falling real yields/term premium would weaken this posture.',
            'trade_action': 'NO TRADE',
        }
    if base >= 2 and base > comp:
        return {
            'posture': 'SELECTIVE RISK-ON RESEARCH',
            'read': 'Resilient-growth / cooling-inflation evidence currently leads the competing macro set.',
            'do': 'Prioritize assets with favorable forward asymmetry and confirmed fundamental capture; do not buy broad beta automatically.',
            'next': 'HY spread acceleration, claims deterioration or renewed inflation would weaken this posture.',
            'trade_action': 'NO TRADE',
        }
    return {
        'posture': 'MIXED / WAIT',
        'read': 'No competing scenario clearly dominates the loaded evidence.',
        'do': 'Do not force a macro trade. Use relative-value or company-specific bottleneck research instead.',
        'next': 'Wait for the next discriminating growth, inflation, rates or credit observation to break the tie.',
        'trade_action': 'NO TRADE',
    }


def heatmap_guidance(heat_df):
    if heat_df is None or heat_df.empty or 'percentile' not in heat_df:
        return {'read': 'Relative-state data are unavailable.', 'do': 'Do not infer regime from an empty heatmap.', 'next': 'Restore macro feed coverage.'}
    d = heat_df.dropna(subset=['percentile']).copy()
    if d.empty:
        return {'read': 'Relative-state data are unavailable.', 'do': 'Do not infer regime from an empty heatmap.', 'next': 'Restore macro feed coverage.'}
    hi = d.sort_values('percentile', ascending=False).head(2)
    lo = d.sort_values('percentile').head(2)
    hi_txt = ', '.join(f"{r.driver} {r.percentile:.0%}" for _, r in hi.iterrows())
    lo_txt = ', '.join(f"{r.driver} {r.percentile:.0%}" for _, r in lo.iterrows())
    return {
        'read': f'Highest relative states: {hi_txt}. Lowest: {lo_txt}.',
        'do': 'Treat extremes as constraints to investigate, not directional signals. Check whether the same drivers also dominate the shock chart and scenario evidence.',
        'next': 'A regime view becomes more credible when relative level, recent change and causal confirmation point the same way.',
    }


def shock_guidance(shock_df):
    if shock_df is None or shock_df.empty or 'z_13w' not in shock_df:
        return {'read': 'No standardized shock data.', 'do': 'Do not rank drivers.', 'next': 'Restore macro history.'}
    d = shock_df.dropna(subset=['z_13w']).copy()
    if d.empty:
        return {'read': 'No standardized shock data.', 'do': 'Do not rank drivers.', 'next': 'Restore macro history.'}
    d['absz'] = d['z_13w'].abs()
    top = d.sort_values('absz', ascending=False).head(3)
    txt = ', '.join(f"{r.driver} {r.z_13w:+.1f}σ" for _, r in top.iterrows())
    lead = top.iloc[0]
    return {
        'read': f'Largest 13-week moves vs own history: {txt}.',
        'do': f'Start relationship/scenario analysis with {lead.driver}; it is the most abnormal current driver in this panel.',
        'next': 'If the shock persists and receives credit/funding/earnings confirmation, its decision relevance increases; mean reversion weakens it.',
    }


def scenario_guidance(scenario_df):
    if scenario_df is None or scenario_df.empty:
        return {'read': 'Scenario evidence unavailable.', 'do': 'Stay NO TRADE.', 'next': 'Restore the underlying data.'}
    rows = []
    for _, r in scenario_df.iterrows():
        ns, nc = _scenario_counts(r)
        rows.append((str(r.get('type')), str(r.get('scenario')), ns, nc, ns-nc))
    rows.sort(key=lambda x: x[4], reverse=True)
    lead = rows[0]
    second = rows[1] if len(rows) > 1 else None
    tied = second is not None and lead[4] == second[4]
    if tied:
        do = 'No scenario has a unique evidence lead. Avoid a broad macro expression; use selective/relative-value research.'
    else:
        do = f'Use {lead[0]} as the first scenario to stress-test opportunities, while keeping the competing scenario explicit.'
    return {
        'read': f'Leading evidence balance: {lead[0]} — {lead[1]} ({lead[2]} support / {lead[3]} contradiction).',
        'do': do,
        'next': 'The view should change only when a discriminating observation changes the evidence balance; evidence counts are not probabilities.',
    }


def projection_guidance(stats, horizon='3M'):
    if stats is None or stats.empty:
        return {'read': 'Projection unavailable.', 'do': 'Do not infer a forward range.', 'next': 'Need overlapping macro and asset history.', 'row': None}
    d = stats.copy()
    if horizon not in set(d['horizon'].astype(str)):
        horizon = str(d.iloc[min(1, len(d)-1)]['horizon'])
    row = d[d['horizon'].astype(str) == horizon].iloc[0]
    med = float(row.get('median', np.nan)); p10 = float(row.get('p10', np.nan)); p90 = float(row.get('p90', np.nan))
    pp = float(row.get('p_positive', np.nan)); pl = float(row.get('p_loss10', np.nan))
    if all(np.isfinite(x) for x in [med,p10,p90,pp,pl]):
        read = f'{horizon} analog range: P10 {p10:+.1%}, median {med:+.1%}, P90 {p90:+.1%}; P(positive) {pp:.0%}, P(loss >10%) {pl:.0%}.'
        if med > 0 and pp > .5:
            do = 'Forward analogs lean positive, so prioritize long-side research only if the causal/pricing gates also pass.'
        elif med < 0 and pp < .5:
            do = 'Forward analogs lean negative, so prioritize hedge/short research only if the causal/pricing gates also pass.'
        else:
            do = 'Forward analogs are mixed; do not force direction.'
    else:
        read = f'{horizon} projection exists but key summary fields are incomplete.'
        do = 'Treat it as incomplete research context.'
    return {
        'read': read,
        'do': do,
        'next': 'Re-run after the next material macro release; a meaningful change in the nearest-state set should move the distribution.',
        'row': row,
    }


def company_gate_guidance(detail, projection_available=False):
    status = str(detail.get('reason', ''))
    chain = detail.get('chain', {}) or {}
    mech = bool(chain.get('constraint_evidence') and chain.get('demand_capture_evidence'))
    mon = bool(chain.get('sec_revenue_capture') and (chain.get('sec_operating_capture') or chain.get('monetization_language')))
    stages = [
        ('Mechanism', 'PASS' if mech else 'FAIL'),
        ('Monetization', 'PASS' if mon else ('WATCH' if mech else 'FAIL')),
        ('Pricing gap', 'DATA GATED'),
        ('Catalyst', 'DATA GATED'),
        ('Projection', 'PARTIAL' if projection_available else 'DATA GATED'),
    ]
    if mech and mon:
        research_state = 'PRIORITY WATCHLIST'
        do = 'Mechanism and monetization deserve priority. Next unlock is pricing/revisions/catalyst; trade action remains NO TRADE until those gates are defensible.'
    elif mech:
        research_state = 'WATCH — NEED MONETIZATION'
        do = 'Keep on watchlist but require revenue/operating/FCF capture before spending time on valuation or entry.'
    else:
        research_state = 'LOW PRIORITY / DROP'
        do = 'Do not chase the narrative. Revisit only when a complete constraint→capture chain appears.'
    return {'research_state': research_state, 'read': status or 'No evidence summary.', 'do': do, 'stages': stages}
