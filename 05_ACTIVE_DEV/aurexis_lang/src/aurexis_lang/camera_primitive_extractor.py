import json
from pathlib import Path
from typing import Dict, List, Any

from .visual_tokenizer import PrimitiveObservation

def load_zone_manifest(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def extract_primitives_from_zone_data(zone_data: Dict[str, Any]) -> List[PrimitiveObservation]:
    observations: List[PrimitiveObservation] = []

    # Extremely early coarse extraction scaffold:
    # convert known family/zone metadata into primitive candidates
    family = zone_data.get("family", "unknown")
    zones = zone_data.get("zones", [])

    observations.append(
        PrimitiveObservation(
            primitive_type="region",
            attributes={"role": "identifier", "value": family},
            confidence=0.75,
        )
    )

    for zone in zones:
        zone_name = zone.get("zone_name", "unknown_zone")
        zone_role = zone.get("role", "region")
        observations.append(
            PrimitiveObservation(
                primitive_type="region",
                attributes={"role": zone_role, "value": zone_name},
                confidence=float(zone.get("confidence", 0.7)),
            )
        )

    return observations

def zone_json_to_parser_bundle(path: str) -> Dict[str, Any]:
    zone_data = load_zone_manifest(path)
    observations = extract_primitives_from_zone_data(zone_data)
    return {
        "source": path,
        "observation_count": len(observations),
        "primitive_observations": [
            {
                "primitive_type": obs.primitive_type,
                "attributes": obs.attributes,
                "confidence": obs.confidence,
            }
            for obs in observations
        ],
    }
