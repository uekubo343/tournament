from dataclasses import dataclass, field
from typing import Optional

BYE = "__BYE__"


@dataclass
class Match:
    round_index: int
    match_index: int
    team1: Optional[str] = None
    team2: Optional[str] = None
    winner: Optional[str] = None
    bracket: str = "winners"  # "winners", "losers", "grand_final"

    @property
    def is_bye(self) -> bool:
        return self.team1 == BYE or self.team2 == BYE

    @property
    def display_team1(self) -> str:
        if self.team1 is None:
            return "TBD"
        if self.team1 == BYE:
            return "BYE"
        return self.team1

    @property
    def display_team2(self) -> str:
        if self.team2 is None:
            return "TBD"
        if self.team2 == BYE:
            return "BYE"
        return self.team2


@dataclass
class BracketData:
    winners_rounds: list[list[Match]]
    losers_rounds: list[list[Match]] = field(default_factory=list)
    grand_final: Optional[Match] = None
    total_slots: int = 0
    format: str = "single"  # "single" or "double"
