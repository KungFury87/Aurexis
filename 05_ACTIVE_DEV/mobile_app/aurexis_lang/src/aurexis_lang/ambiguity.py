from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

@dataclass
class CandidateInterpretation:
    candidate_type: str
    confidence: float
    payload: Dict[str, Any] = field(default_factory=dict)

def rank_candidates(candidates: List[CandidateInterpretation]) -> List[CandidateInterpretation]:
    return sorted(candidates, key=lambda c: c.confidence, reverse=True)

def summarize_candidates(candidates: List[CandidateInterpretation]) -> Dict[str, Any]:
    ranked = rank_candidates(candidates)
    return {
        "candidate_count": len(ranked),
        "best_candidate": asdict(ranked[0]) if ranked else None,
        "alternatives": [asdict(c) for c in ranked[1:]] if len(ranked) > 1 else [],
    }
