"""Basic usage examples for tournament-maker."""

from tournament_maker import TournamentBracket

# ------------------------------------------------------------------
# 1. Simple 8-team single elimination
# ------------------------------------------------------------------
TournamentBracket(teams=["Alpha", "Beta", "Gamma", "Delta",
                          "Epsilon", "Zeta", "Eta", "Theta"]) \
    .set_layout("left_to_right") \
    .render("example_8team_ltr.svg")

print("Saved: example_8team_ltr.svg")

# ------------------------------------------------------------------
# 2. 5 teams with 3 seeds (auto byes for seeds)
# ------------------------------------------------------------------
TournamentBracket(
    teams=["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
    seeds=["Alpha", "Beta", "Gamma"],   # these 3 get first-round byes
) \
    .set_style(highlight_winner=False) \
    .render("example_5team_seeds.svg")

print("Saved: example_5team_seeds.svg")

# ------------------------------------------------------------------
# 3. 2-column layout with winner highlight
# ------------------------------------------------------------------
TournamentBracket(teams=["A", "B", "C", "D", "E", "F", "G", "H"]) \
    .set_style(highlight_winner=True, winner_color="#27ae60") \
    .set_layout("left_to_right_2col") \
    .render("example_2col.svg")

print("Saved: example_2col.svg")

# ------------------------------------------------------------------
# 4. Top-to-bottom layout with circle names
# ------------------------------------------------------------------
TournamentBracket(teams=["Team1", "Team2", "Team3", "Team4"]) \
    .set_style(circle_names=True) \
    .set_layout("top_to_bottom") \
    .render("example_ttb_circle.svg")

print("Saved: example_ttb_circle.svg")

# ------------------------------------------------------------------
# 5. Double elimination, 8 teams
# ------------------------------------------------------------------
TournamentBracket(
    teams=["A", "B", "C", "D", "E", "F", "G", "H"],
    format="double",
) \
    .set_style(show_round_labels=True) \
    .render("example_double_elim.svg")

print("Saved: example_double_elim.svg")
