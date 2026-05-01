import math
from .models import Match, BYE, BracketData


def _next_power_of_2(n: int) -> int:
    if n < 2:
        raise ValueError("Need at least 2 teams")
    return 1 << (n - 1).bit_length()


def _normalize_seeds(teams: list[str], seeds: list) -> list[str]:
    result = []
    seen: set[str] = set()
    for s in seeds:
        if isinstance(s, int):
            if not (0 <= s < len(teams)):
                raise IndexError(f"Seed index {s} out of range for {len(teams)} teams")
            name = teams[s]
        elif isinstance(s, str):
            if s not in teams:
                raise ValueError(f"Seed '{s}' not found in teams list")
            name = s
        else:
            raise TypeError(f"Seeds must be str or int, got {type(s).__name__}")
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _arrange_slots(teams: list[str], seed_names: list[str], M: int) -> list[str]:
    """
    Arrange teams into M slots. Seeded teams are paired with BYE.
    Non-seeded teams are paired consecutively.
    Bye pairs and real pairs are interleaved evenly.
    """
    seed_set = set(seed_names)
    non_seeds = [t for t in teams if t not in seed_set]

    bye_pairs = [(s, BYE) for s in seed_names]
    real_pairs = [(non_seeds[i * 2], non_seeds[i * 2 + 1]) for i in range(len(non_seeds) // 2)]

    all_pairs = _interleave_evenly(bye_pairs, real_pairs)
    return [team for pair in all_pairs for team in pair]


def _interleave_evenly(a_list: list, b_list: list) -> list:
    """Interleave two lists as evenly as possible (Bresenham-style)."""
    total = len(a_list) + len(b_list)
    result = []
    ai = bi = 0
    a_total = len(a_list)
    for i in range(total):
        if ai < len(a_list) and (bi >= len(b_list) or ai * total <= i * a_total):
            result.append(a_list[ai])
            ai += 1
        else:
            result.append(b_list[bi])
            bi += 1
    return result


def _slots_to_rounds(slots: list[str], bracket: str = "winners") -> list[list[Match]]:
    M = len(slots)
    total_rounds = int(math.log2(M))

    round0 = []
    for i in range(M // 2):
        t1 = slots[i * 2]
        t2 = slots[i * 2 + 1]
        m = Match(round_index=0, match_index=i, team1=t1, team2=t2, bracket=bracket)
        if t2 == BYE:
            m.winner = t1
        elif t1 == BYE:
            m.winner = t2
        round0.append(m)

    rounds = [round0]
    for r in range(1, total_rounds):
        prev = rounds[-1]
        curr = []
        for i in range(len(prev) // 2):
            m1, m2 = prev[i * 2], prev[i * 2 + 1]
            curr.append(Match(
                round_index=r,
                match_index=i,
                team1=m1.winner,
                team2=m2.winner,
                bracket=bracket,
            ))
        rounds.append(curr)

    return rounds


def _get_loser(match: Match):
    if match.winner is None:
        return None
    if match.winner == match.team1:
        return match.team2
    return match.team1


def _build_losers_bracket(wb_rounds: list[list[Match]]) -> list[list[Match]]:
    """
    Build losers bracket rounds.
    LB alternates: "intake WB losers" rounds and "intra-LB" rounds.
    """
    lb_rounds: list[list[Match]] = []
    lb_round_idx = 0

    # LB R0: WB R0 losers paired up
    wb_r0_losers = [_get_loser(m) for m in wb_rounds[0]]
    lb_r0 = []
    for i in range(len(wb_r0_losers) // 2):
        l1 = wb_r0_losers[i * 2]
        l2 = wb_r0_losers[i * 2 + 1]
        lb_r0.append(Match(round_index=lb_round_idx, match_index=i,
                           team1=l1, team2=l2, bracket="losers"))
    lb_rounds.append(lb_r0)
    lb_round_idx += 1

    # For each subsequent WB round (except the final), alternate:
    #   1. LB intake: LB survivors vs WB round losers
    #   2. LB internal: survivors play each other (if > 1 match)
    for wb_r in range(1, len(wb_rounds) - 1):
        prev_lb = lb_rounds[-1]
        wb_losers = [_get_loser(m) for m in wb_rounds[wb_r]]

        # Intake round: LB survivors vs WB losers
        intake = []
        for i, (lb_m, wb_l) in enumerate(zip(prev_lb, wb_losers)):
            intake.append(Match(
                round_index=lb_round_idx, match_index=i,
                team1=lb_m.winner, team2=wb_l, bracket="losers",
            ))
        lb_rounds.append(intake)
        lb_round_idx += 1

        # Internal round: survivors play each other (reduce by half)
        if len(intake) > 1:
            intra = []
            for i in range(len(intake) // 2):
                m1, m2 = intake[i * 2], intake[i * 2 + 1]
                intra.append(Match(
                    round_index=lb_round_idx, match_index=i,
                    team1=m1.winner, team2=m2.winner, bracket="losers",
                ))
            lb_rounds.append(intra)
            lb_round_idx += 1

    # LB Final: last LB survivor vs WB Final loser
    prev_lb = lb_rounds[-1]
    # If there are multiple survivors, reduce first
    while len(prev_lb) > 1:
        intra = []
        for i in range(len(prev_lb) // 2):
            m1, m2 = prev_lb[i * 2], prev_lb[i * 2 + 1]
            intra.append(Match(
                round_index=lb_round_idx, match_index=i,
                team1=m1.winner, team2=m2.winner, bracket="losers",
            ))
        lb_rounds.append(intra)
        lb_round_idx += 1
        prev_lb = intra

    wb_final_loser = _get_loser(wb_rounds[-1][0])
    lb_final = [Match(
        round_index=lb_round_idx, match_index=0,
        team1=prev_lb[0].winner, team2=wb_final_loser, bracket="losers",
    )]
    lb_rounds.append(lb_final)

    return lb_rounds


def build_bracket(
    teams: list[str],
    seeds: list | None,
    format: str,
) -> BracketData:
    if format not in ("single", "double"):
        raise ValueError(f"format must be 'single' or 'double', got {format!r}")
    n = len(teams)
    if n < 2:
        raise ValueError("Need at least 2 teams")

    M = _next_power_of_2(n)
    byes_needed = M - n

    if byes_needed > 0:
        if not seeds:
            raise ValueError(
                f"Team count {n} is not a power of 2 (next: {M}). "
                f"Specify {byes_needed} seeded team(s) — they receive a first-round bye. "
                "Use seeds=[name, ...] or seeds=[index, ...]."
            )
        seed_names = _normalize_seeds(teams, seeds)
        if len(seed_names) < byes_needed:
            raise ValueError(
                f"Need {byes_needed} seeds for {n} teams, got {len(seed_names)}."
            )
        seed_names = seed_names[:byes_needed]
    else:
        seed_names = []

    slots = _arrange_slots(teams, seed_names, M)
    wb_rounds = _slots_to_rounds(slots, bracket="winners")

    if format == "single":
        return BracketData(
            winners_rounds=wb_rounds,
            total_slots=M,
            format="single",
        )

    # Double elimination
    lb_rounds = _build_losers_bracket(wb_rounds)
    gf = Match(
        round_index=999, match_index=0,
        team1=wb_rounds[-1][0].winner,
        team2=lb_rounds[-1][0].winner,
        bracket="grand_final",
    )
    return BracketData(
        winners_rounds=wb_rounds,
        losers_rounds=lb_rounds,
        grand_final=gf,
        total_slots=M,
        format="double",
    )
