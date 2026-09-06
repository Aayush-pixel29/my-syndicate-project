from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any


@dataclass
class Skill:
    """Minimal, strongly typed representation for reusable agent tool-use experience."""
    skill_id: str
    name: str
    description: str
    trigger: str
    procedure: List[str]
    source_trajectory_id: str
    failure_type: str
    evidence: List[str]
    version: int = 1
    validated: bool = False
    promoted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """
        Validate the skill data.
        Returns True only when required fields are valid.
        """
        if not self.skill_id or not isinstance(self.skill_id, str): return False
        if not self.name or not isinstance(self.name, str): return False
        if not self.trigger or not isinstance(self.trigger, str): return False
        if not self.source_trajectory_id or not isinstance(self.source_trajectory_id, str): return False
        if not self.procedure or not isinstance(self.procedure, list): return False
        if len(self.procedure) == 0: return False
        if not isinstance(self.version, int) or self.version < 1: return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dictionary containing every field."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """Reconstruct a Skill from a dictionary safely handling optional metadata and required fields."""
        required_fields = [
            "skill_id", "name", "description", "trigger", "procedure",
            "source_trajectory_id", "failure_type", "evidence"
        ]
        for f in required_fields:
            if f not in data:
                raise ValueError(f"Missing required field: {f}")

        # Extract values
        skill_id = data["skill_id"]
        name = data["name"]
        description = data["description"]
        trigger = data["trigger"]
        procedure = data["procedure"]
        source_trajectory_id = data["source_trajectory_id"]
        failure_type = data["failure_type"]
        evidence = data["evidence"]
        
        # Optional fields
        version = data.get("version", 1)
        validated = data.get("validated", False)
        promoted = data.get("promoted", False)
        metadata = data.get("metadata", {})

        return cls(
            skill_id=skill_id,
            name=name,
            description=description,
            trigger=trigger,
            procedure=procedure,
            source_trajectory_id=source_trajectory_id,
            failure_type=failure_type,
            evidence=evidence,
            version=version,
            validated=validated,
            promoted=promoted,
            metadata=metadata
        )
