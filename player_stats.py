import statistics
from termcolor import colored
from collections import defaultdict
from utilities import avg, safe_div, median


class WinStats:
    def __init__(self, evening):
        # # of wins
        # avg size of wins
        self.evening = evening
        wins = defaultdict(list)
        showdown_wins = defaultdict(list)
        preshowdown_wins = defaultdict(list)
        for round in evening.get_rounds():
            for (player, hand, amt, _) in round.winners:
                wins[player].append(amt)
                if hand is None:
                    preshowdown_wins[player].append(amt)
                else:
                    showdown_wins[player].append(amt)
        self.wins = wins
        self.showdown_wins = showdown_wins
        self.preshowdown_wins = preshowdown_wins

    def print(self):
        showdown_wins = self.showdown_wins
        preshowdown_wins = self.preshowdown_wins

        print(colored("Win Stats (Where did your money come from?)", "white", attrs=["underline"]))
        for player in self.evening.players.keys():
            num_wins = len(showdown_wins[player]) + len(preshowdown_wins[player])
            pct_at_showdown = safe_div(len(showdown_wins[player]),  num_wins ) * 100
            pct_at_preshowdown = safe_div(len(preshowdown_wins[player]), num_wins ) * 100
            win_amts = showdown_wins[player] + preshowdown_wins[player]

            median_win_amt = median(win_amts)
            median_showdown_amt = median(showdown_wins[player])
            median_preshowdown_amt = median(preshowdown_wins[player])

            print(colored(f"  {player}", "white", attrs=["bold"]))
            print(f"    # wins (median): {num_wins:>2} ({median_win_amt:0.0f})")
            print(f"       %    showdown (median): {pct_at_showdown:>6.2f}% ({median_showdown_amt:0.0f})")
            print(f"       % preshowdown (median): {pct_at_preshowdown:>6.2f}% ({median_preshowdown_amt:0.0f})")
        print()


class PlayStats:
    def __init__(self, evening, win_stats: WinStats):
        self.evening = evening
        self.win_stats = win_stats
        rounds_present = defaultdict(int)
        rounds_contributed = defaultdict(int)
        showdowns_played = defaultdict(int)
        for round in evening.get_rounds():
            for player in round.names_in_showdown():
                showdowns_played[player] += 1

            for player in round.voluntary_contributors():
                rounds_contributed[player] += 1

            for player in round.players_present():
                rounds_present[player] += 1

        self.rounds_present = rounds_present
        self.rounds_contributed = rounds_contributed
        self.showdowns_played = showdowns_played

    def print(self):
        # % How often you saw each stage
        # % Showdowns won

        print(colored("Play Stats (What happened when you played in a round?)", "white", attrs=["underline"]))
        max_rounds = len(self.evening.get_rounds())
        print(f"Rounds: {max_rounds}")
        for player in self.evening.players.keys():
            total_rounds = self.rounds_present[player]
            player_wins = len(self.win_stats.wins[player])
            player_showdown_wins = len(self.win_stats.showdown_wins[player])
            pct_played = safe_div(self.rounds_contributed[player], total_rounds) * 100
            pct_played_wins = safe_div(player_wins, self.rounds_contributed[player]) * 100
            pct_showdown_wins = safe_div(player_showdown_wins, self.showdowns_played[player]) * 100

            print(colored(f"  Player: {player}", "white", attrs=["bold"]))
            print(
                f"   Num. Voluntary / Rounds Played   (VPIP) : "
                f"{self.rounds_contributed[player]:>3d} / {total_rounds:>3d} ({pct_played:>6.2f}%)")
            print(
                f"       Rounds Won / Num. Voluntary (% won) : "
                f"{player_wins:>3d} / {self.rounds_contributed[player]:>3d} ({pct_played_wins:>6.2f}%)")
            print(
                f"    Showdowns Won / Num. Showdown  (% won) : "
                f"{player_showdown_wins:>3d} / {self.showdowns_played[player]:>3d} ({pct_showdown_wins:>6.2f}%)")
        print()


class PreFlopStats:
    def __init__(self, evening, play_stats: PlayStats):
        # How many times did you limp
        # How many times did you call, what was your avg call
        # How many times did you raise, what was your avg raise
        self.evening = evening
        self.play_stats = play_stats
        limp_rounds = defaultdict(list)
        raise_amts = defaultdict(list)
        raise_rounds = defaultdict(list)
        three_bet_amts = defaultdict(list)
        three_bet_rounds = defaultdict(list)

        for round in evening.get_rounds():
            preflop_amounts = round.money_in_round(round.preflop_moves)
            for player, amt in preflop_amounts.items():
                if amt == round.big_blind[1] and 0 == len(round.find_moves(player, "fold", round.preflop_moves)):
                    limp_rounds[player].append(round)

            # In case there are multiple raises in a single round
            round_raises = {}
            round_3bets = {}
            open_raise = False
            three_bet = False
            for move in round.preflop_moves:
                if move.action_name == "raise":
                    round_raises[move.player] = move.amount
                    if not open_raise:
                        open_raise = True
                    elif not three_bet:
                        round_3bets[move.player] = move.amount
                        three_bet = True

            for player, amt in round_raises.items():
                raise_amts[player].append(amt)
                raise_rounds[player].append(round)

            for player, amt in round_3bets.items():
                three_bet_amts[player].append(amt)
                three_bet_rounds[player].append(round)

        self.limp_rounds = limp_rounds
        self.raise_amts = raise_amts
        self.raise_rounds = raise_rounds
        self.three_bet_amts = three_bet_amts
        self.three_bet_rounds = three_bet_rounds

    def print(self):
        print(colored("Preflop Behavior:", "white", attrs=["underline"]))
        for player in self.evening.players.keys():
            total_rounds = self.play_stats.rounds_present[player]
            pct_played = safe_div(self.play_stats.rounds_contributed[player], total_rounds) * 100
            pct_limped = safe_div(len(self.limp_rounds[player]), self.play_stats.rounds_contributed[player]) * 100
            pct_raised = safe_div(len(self.raise_rounds[player]), total_rounds) * 100
            pct_3bet = safe_div(len(self.three_bet_rounds[player]), total_rounds) *100
            print(colored(f"  Player: {player}", "white", attrs=["bold"]))
            print(f"                        Avg Raise Amount  : {avg(self.raise_amts[player]):>3.0f}")
            print(f"                        Avg 3-Bet Amount  : {avg(self.three_bet_amts[player]):>3.0f}")
            print(
                f"   Num. Voluntary / Rounds Played  (VPIP) : "
                f"{self.play_stats.rounds_contributed[player]:>3d} / {total_rounds:>3d} ({pct_played:>6.2f}%)")
            print(
                f"Rounds Raised / Rounds Present      (PFR) : "
                f"{len(self.raise_rounds[player]):>3d} / {self.play_stats.rounds_present[player]:>3d} ({pct_raised:>6.2f}%)")
            print(
                f" Rounds 3-Bet / Rounds Present     (3BET) : "
                f"{len(self.three_bet_rounds[player]):>3d} / {self.play_stats.rounds_present[player]:>3d} ({pct_3bet:>6.2f}%)")
            print(
                f"Rounds Limped / Num. Voluntary (% limped) : "
                f"{len(self.limp_rounds[player]):>3d} / {self.play_stats.rounds_contributed[player]:>3d} ({pct_limped:>6.2f}%)")
        print()


def fold_stats():
    # What amount causes a person to fold (absolute) vs (relative to pot)
    pass
