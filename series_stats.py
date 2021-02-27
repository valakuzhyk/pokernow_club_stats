"""
This module calculates statistics of players over a series of tournament poker games.

In tournament games (as opposed to cash games) we are interested in the order in which players are eliminated
and this affects awarded prizes. The chips are not that important and are not directly tied to cash.
"""
import argparse
from collections import defaultdict
from typing import Dict, List, Callable

import matplotlib.pyplot as plt

from log_processor import Parser


class NameMapping:
    """
    Class used to resolve name synonyms. This is useful when players change their nicknames
    from one game to another and you want to map all those aliases to a single player.
    """
    def __init__(self, mapping: Dict[str, str]):
        """
        `mapping` is a dict which maps an alias to the real name of the player.

        For example, if you have a series of games where some player A was known as A in one game and
        as A2 in another game, and you want his canonical name to be A, you use `NameMapping({'A2': 'A'})`
        which maps the alias A2 to the canonical name A.

        Also additionally this function gets rid of `@ some_id` suffix of Pokernow.club names, because
        they obviously may change from one game to another.
        """
        self.mapping = mapping

    def normalise_name(self, name: str):
        actual_name = name.split("@")[0].strip()
        return self.mapping.get(actual_name, actual_name)


class TournamentSpec:
    def __init__(self, prize_fractions: Dict[int, float], start_amount: float):
        """
        `prize_fractions` is a dictionary describing fractions of the tournaments prize awarded for
        finishing at a particular position.

        For example `{1: 0.7, 2: 0.3}` describes that the winner (1st place) gets 70%
        of the prize and the last eliminated player (2nd place) gets 30%.
        Other players which have been eliminated earlier - get nothing.

        `start_amount` describes amount cash each player contributes to the pot (it's used for absolute cash winnings
        calculations). Presumably this is the same for all players at the start, so we just pass it here rather than
        parsing from the log.
        """
        self.prize_fractions = prize_fractions
        self.start_amount = start_amount

    def prize_fraction_for_position(self, pos: int) -> float:
        """
        Fractions of the tournament prize to be received from finish at position `pos`.
        Note: position is numbered from 1, that is the winner is at position 1,
        the last eliminated player is at position 2 and so on.
        """
        return self.prize_fractions.get(pos, 0.0)

    def __repr__(self):
        return 'TournamentSpec(%r)' % self.prize_fractions


class PlayerStats:
    def __init__(self):
        # Game numbers where player was present (indexing starts from 1)
        self.game_numbers = []

        self.wins = []
        self.spending = []

        self.cumulated_wins = []
        self.cumulated_spending = []

        # Won / spent ratios cumulated over time.
        self.ratios = []

        # Won - spent diff, i.e. absolute winnings, over time.
        self.diffs = []

    def record_game(self, game_no, won, spent):
        self.game_numbers.append(game_no)

        self.wins.append(won)
        self.spending.append(spent)

        prev_won = self.cumulated_wins[-1] if self.cumulated_wins else 0.0
        total_won = prev_won + won
        self.cumulated_wins.append(total_won)

        prev_spent = self.cumulated_spending[-1] if self.cumulated_spending else 0.0
        total_spent = prev_spent + spent
        self.cumulated_spending.append(total_spent)

        self.ratios.append(total_won / total_spent)
        self.diffs.append(total_won - total_spent)

    def total_won_amount(self) -> float:
        return self.cumulated_wins[-1] if self.cumulated_wins else 0.0

    def total_spent_amount(self) -> float:
        return self.cumulated_spending[-1] if self.cumulated_spending else 0.0


class SeriesStats:
    def __init__(self, evenings, name_mapping, tournament_spec):
        self.evenings = evenings
        self.name_mapping = name_mapping
        self.tournament_spec = tournament_spec
        self.player_stats = defaultdict(PlayerStats)

    def run(self):
        self.calc_stats()
        self.print_stats()
        self.plot_ratios()
        self.plot_diffs()

    @staticmethod
    def evening_ranking(evening) -> List[str]:
        elimination = {}

        # For each player find the round when they were eliminated (first reached 0.0).
        # Also track chip amount for tie breakers.
        for player, rounds_amts in evening.historical_amounts.items():
            eliminated_round = next((round_no for round_no, amt in rounds_amts if amt == 0.0), None)

            if eliminated_round is None:
                _, last_amount = rounds_amts[-1]
                never = float("inf")
                elimination[player] = (never, last_amount)
            else:
                _, amount_at_prev_round = rounds_amts[eliminated_round - 1] if eliminated_round > 0 else 0
                elimination[player] = (eliminated_round, amount_at_prev_round)

        # Now calculate the rankings by sorting based on eliminated round (the greater the better)
        # and last non-zero amounts as a potential tie breaker (also the greater the better).
        rankings = sorted(elimination.items(), key=lambda kv: kv[1], reverse=True)

        return [player for player, rank in rankings]

    def calc_stats(self):
        for game_no, evening in enumerate(self.evenings, 1):
            ranking = SeriesStats.evening_ranking(evening)
            total_pot = self.tournament_spec.start_amount * len(ranking)
            for pos, player in enumerate(ranking, 1):
                spent = self.tournament_spec.start_amount
                won = int(self.tournament_spec.prize_fraction_for_position(pos) * total_pot)
                normalised_name = self.name_mapping.normalise_name(player)
                self.player_stats[normalised_name].record_game(game_no, won, spent)

    def reshape_stats(self):
        total_won = {p: stats.cumulated_wins[-1] for p, stats in self.player_stats.items()}
        total_spent = {p: stats.cumulated_spending[-1] for p, stats in self.player_stats.items()}
        last_ratio = {p: stats.ratios[-1] for p, stats in self.player_stats.items()}
        last_diff = {p: stats.diffs[-1] for p, stats in self.player_stats.items()}

        def sorted_by_value(d):
            return sorted(d.items(), key=lambda kv: kv[1], reverse=True)

        return (
            sorted_by_value(total_won),
            sorted_by_value(total_spent),
            sorted_by_value(last_ratio),
            sorted_by_value(last_diff)
        )

    def print_stats(self):
        won, spent, ratios, diffs = self.reshape_stats()
        print(self.tournament_spec)

        print("Total wins:")
        for player_name, v in won:
            print(f"{player_name:>16s}: {v:.0f}")
        print()

        print("Total spending:")
        for player_name, v in spent:
            print(f"{player_name:>16s}: {v:.0f}")
        print()

        print("Won/spent ratios:")
        for player_name, v in ratios:
            print(f"{player_name:>16s}: {v:.2f}")
        print()

        print("Absolute winnings:")
        for player_name, v in diffs:
            print(f"{player_name:>16s}: {v:.0f}")
        print()

    def plot_ratios(self):
        title = "Won/Spent ratios over time"
        ylabel = "Won/Spent ratio"
        self.plot(self.player_stats, lambda s: s.ratios, title, ylabel)

    def plot_diffs(self):
        title = "Total winnings over time"
        ylabel = "Total winnings, chips"
        self.plot(self.player_stats, lambda s: s.diffs, title, ylabel)

    def plot(self,
             data: Dict[str, PlayerStats],
             key: Callable[[PlayerStats], List[float]],
             title: str,
             ylabel: str):

        plt.style.use('seaborn-bright')

        # Other nice styles to try: Solarize_Light2
        #
        # See: https://matplotlib.org/3.1.1/gallery/style_sheets/style_sheets_reference.html

        # Use a color map which supports many distinguishable colors, since we have many players.
        # This one supports 20 colors.
        color_map = plt.get_cmap('tab20')

        # Other colormaps to try: tab20b, tab20c
        #
        # See qualitative colormaps here:
        # https://matplotlib.org/3.1.1/tutorials/colors/colormaps.html#qualitative

        fig, ax = plt.subplots(1)

        # Use colors from the palette above.
        n = len(self.player_stats)
        ax.set_prop_cycle('color', [color_map(i / n) for i in range(n)])

        for player, stats in data.items():
            ax.plot(stats.game_numbers, key(stats), label=player)

        ax.set_title(title)
        ax.set_xlabel("Game #")
        ax.set_ylabel(ylabel)
        ax.legend(loc="upper right")

        plt.tight_layout()
        plt.show()


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("log_files", nargs="+", help='Paths to log files from pokernow.club')
    args = arg_parser.parse_args()

    p = Parser()
    evenings = [p.parse("", file) for file in args.log_files]

    # TODO: move that to a config file.
    name_mapping = NameMapping({
        'some player alias': 'player',
        'another_alias': 'player',
    })

    # 70% to the winner, 30% to the runner-up, everyone starts with 2000 chips.
    spec = TournamentSpec({1: 0.7, 2: 0.3}, 2000)

    # Other interesting specs to try:
    # spec = TournamentSpec({1: 1.0}, 2000)
    # spec = TournamentSpec({1: 0.5, 2: 0.3, 3: 0.2}, 2000)

    series_stats = SeriesStats(evenings, name_mapping, spec)
    series_stats.run()


if __name__ == "__main__":
    main()
