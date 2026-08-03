"""Competing-thesis discovery contracts."""

from pydantic import BaseModel, Field, field_validator, model_validator


class ThesisCandidate(BaseModel):
    thesis_id: str
    thesis_type: str
    claim: str
    distinct_prediction: str
    prior_probability: float = Field(ge=0.0, le=1.0)

    @field_validator("prior_probability", mode="before")
    @classmethod
    def reject_boolean_prior(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("thesis prior cannot be boolean")
        return value

    @model_validator(mode="after")
    def validate_candidate(self) -> "ThesisCandidate":
        if any(
            not value.strip()
            for value in (
                self.thesis_id,
                self.thesis_type,
                self.claim,
                self.distinct_prediction,
            )
        ):
            raise ValueError("thesis candidate fields must be nonblank")
        return self


def validate_competing_set(candidates: list[ThesisCandidate]) -> None:
    if not 3 <= len(candidates) <= 7:
        raise ValueError("each observation requires three to seven competing hypotheses")
    if not any(candidate.thesis_type == "null" for candidate in candidates):
        raise ValueError("a null hypothesis is mandatory")
    predictions = {candidate.distinct_prediction for candidate in candidates}
    if len(predictions) != len(candidates):
        raise ValueError("each thesis must predict a distinct observable")
