"""Transparent probability updates with evidence-family de-duplication."""
import math
from pydantic import BaseModel, Field


class EvidenceUpdate(BaseModel):
    evidence_id: str
    likelihood_ratio: float = Field(gt=0.0)
    reliability: float = Field(ge=0.0, le=1.0)
    freshness: float = Field(ge=0.0, le=1.0)
    cluster: str
    regime_applicability: float = Field(default=1.0, ge=0.0, le=1.0)


class BayesianUpdateResult(BaseModel):
    prior_probability: float
    posterior_probability: float
    cluster_count: int
    adjusted_log_likelihood: float


def _logit(probability: float) -> float:
    if not 0.0 < probability < 1.0:
        raise ValueError("probability must be strictly between zero and one")
    return math.log(probability / (1.0 - probability))


def update_probability(prior_probability: float, evidence: list[EvidenceUpdate], missing_evidence_penalty: float = 0.0) -> BayesianUpdateResult:
    by_cluster: dict[str, list[float]] = {}
    for item in evidence:
        adjusted = math.log(item.likelihood_ratio) * item.reliability * item.freshness * item.regime_applicability
        by_cluster.setdefault(item.cluster, []).append(adjusted)
    cluster_updates = [max(values, key=abs) for values in by_cluster.values()]
    total = sum(cluster_updates) - missing_evidence_penalty
    posterior = 1.0 / (1.0 + math.exp(-(_logit(prior_probability) + total)))
    return BayesianUpdateResult(prior_probability=prior_probability, posterior_probability=posterior, cluster_count=len(by_cluster), adjusted_log_likelihood=total)
