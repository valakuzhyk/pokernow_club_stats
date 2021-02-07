import sys
import csv
import colorama
import re
import argparse
from typing import List, Set
from collections import defaultdict
from player_stats import WinStats, PlayStats, PreFlopStats
colorama.init()


# Ideas for analyses
# Win statistics
# Position analysis
# Time analysis
# Winning hand analysis
# "luck" analysis
# Bluffing analysis
#   Money throughout the game
# Superlatives
#   quick vs slow
#   efficient with wins
#   Most wins
#   biggest comeback
#   Won the most without showing cards
#   Won the most by showing cards
#   Ratio of showing cards to not showing cards
#   Willingly shared cards


class Player:
    def __init__(self, starting_amount):
        self.stack_amt = starting_amount


class Evening:
    def __init__(self, username):
        self.username = username
        self.rounds = []
        self.players = {}
        self.historical_amounts = defaultdict(list)

    def get_rounds(self):
        return [x for x in self.rounds if x.total_money_in_round()]

    def plot_progression(self):
        import matplotlib.pyplot as plt

        for player, round_amts in self.historical_amounts.items():
            rounds, amts = list(zip(*round_amts))
            player_name = player.split("@")[0].strip()
            plt.plot(rounds, amts, label=player_name)

        plt.xlabel("Round #")
        plt.ylabel("# of Chips")

        plt.legend()
        plt.show()

    def add_player(self, name, amount):
        if name in self.players:
            # rebuy
            pass
        self.players[name] = amount

    def add_round(self, dealer):
        if len(self.rounds) != 0:
            self._update_amounts()
        self._record_amounts()
        new_round = Round(dealer, self.players, len(self.rounds) + 1)
        self.rounds.append(new_round)
        return new_round

    def _record_amounts(self):
        for player, amt in self.players.items():
            self.historical_amounts[player].append((len(self.rounds), amt))

    def _update_amounts(self):
        last_round = self.rounds[-1]
        spent = last_round.money_spent()
        pot_size = sum(spent.values())
        for user, amount in spent.items():
            self.players[user] -= amount

        if len(last_round.winners) == 1:
            for (winner_name, hand, amt, _) in last_round.winners:
                self.players[winner_name] += pot_size
        elif len(last_round.winners) > 1:
            for (winner_name, hand, amt, _) in last_round.winners:
                self.players[winner_name] += amt


class Action:
    def __init__(self, player, action_name, amount, time_stamp):
        self.player = player
        self.action_name = action_name
        self.amount = amount
        self.time_stamp = time_stamp

    def __str__(self):
        return f"{self.player} {self.action_name} {self.amount}"

    def __repr__(self):
        return self.__str__()


class Round:
    def __init__(self, dealer, players, number):
        self.initial_amounts = {name: amt for (name, amt) in players.items()}
        self.dealer = dealer
        self.winners = []
        self.number = number  # start numbering from 1

        # Username to hand
        self.known_hands = {}

        self.flop = None
        self.turn = None
        self.river = None

        # Only populated if a round is "run twice"
        self.second_flop = None
        self.second_turn = None
        self.preflop_moves: List[Action] = []
        self.flop_moves: List[Action] = []
        self.turn_moves: List[Action] = []
        self.river_moves: List[Action] = []

    @property
    def small_blind(self) -> (str, int):
        small_blind_action = [x for x in self.preflop_moves if x.action_name == "small_blind"][0]
        return small_blind_action.player, small_blind_action.amount

    @property
    def big_blind(self) -> (str, int):
        big_blind_action = [x for x in self.preflop_moves if x.action_name == "big_blind"][0]
        return big_blind_action.player, big_blind_action.amount

    @staticmethod
    def find_moves(player, action_name, moves):
        return [move for move in moves if (move.player == player and move.action_name == action_name)]

    @staticmethod
    def money_in_round(moves):
        """
        How much money was spent by each player in a round
        """
        spent = {}
        for m in moves:
            if m.amount != 0:  # ignore all moves that don't involve money
                if m.action_name == 'uncalled_bet':
                    spent[m.player] -= m.amount
                else:
                    spent[m.player] = m.amount

        for m in moves:
            if m.action_name == "missing_small_blind":
                spent[m.player] += m.amount
            if m.action_name == "missing_big_blind" and not Round.find_moves(m.player, "missing_small_blind", moves):
                spent[m.player] += m.amount

        return spent

    def total_money_in_round(self):
        return sum(self.money_spent().values())

    def money_spent(self):
        spent = defaultdict(int)
        for moves in [self.preflop_moves, self.flop_moves, self.turn_moves, self.river_moves]:
            for player, amount in Round.money_in_round(moves).items():
                spent[player] += amount
        return spent

    def voluntary_contributors(self) -> Set[str]:
        voluntary_contributors = set()
        for m in self.preflop_moves:
            if (
                m.action_name not in ["small_blind", "big_blind", "missing_big_blind", "missing_small_blind"]
                and m.amount > 0
            ):
                voluntary_contributors.add(m.player)
        return voluntary_contributors

    def players_present(self) -> Set[str]:
        present = set()
        for m in self.preflop_moves:
            present.add(m.player)
        return present

    def names_in_showdown(self):
        names = set()
        for move in self.river_moves:
            if move.action_name != "fold":
                names.add(move.player)
        return list(names)

    def add_move(self, player, action_name, amount, time_stamp):
        action = Action(player, action_name, amount, time_stamp)
        if self.flop is None:
            self.preflop_moves.append(action)
        elif self.turn is None:
            self.flop_moves.append(action)
        elif self.river is None:
            self.turn_moves.append(action)
        else:
            self.river_moves.append(action)

    def __str__(self):
        s = f"Round {self.number}\n"
        s += f"Game: {self.initial_amounts}\n"
        s += f"  {self.preflop_moves}\n"
        s += f"  {self.flop_moves}\n"
        s += f"  {self.turn_moves}\n"
        s += f"  {self.river_moves}\n"
        if self.flop is not None:
            s += f"  cards -> {' '.join(self.flop)} {self.turn} {self.river}\n"
        else:
            s += f"  cards -> None\n"
        s += f"  winner(s) -> {self.winners}\n"
        return s


class Parser:
    def __init__(self):
        self.username = None

    @property
    def _current_round(self):
        return self.evening.rounds[-1]

    def parse(self, username, file_name) -> Evening:
        self.evening = Evening(username)
        self.username = username
        f = open(file_name, 'r')
        csv_reader = csv.reader(f)
        for row in reversed([row for row in csv_reader]):
            try:
                self.parse_line(row)
            except Exception as e:
                print(row)
                raise e
        evening = self.evening
        self.evening = None
        return evening

    def parse_line(self, row):
        line, time, token = row
        normline = line.lower()
        if "created the game with a stack of" in line or "The admin approved" in line:
            player_name = line.split('"')[1]
            start_amount = int(line.split()[-1][:-1])
            self.evening.add_player(player_name, start_amount)
        elif line == "entry":
            pass
        elif "requested a seat" in line:
            pass
        elif "canceled the seat request" in line:
            pass
        elif "rejected the seat request" in line:
            pass
        elif "changed the ID from" in line:
            pass
        elif "stand up with the stack" in line:
            pass
        elif "sit back with the stack" in line:
            pass
        elif "quits the game with a stack of" in line:
            pass
        elif "joined the game with a stack of" in line:
            pass
        elif "passed the room ownership" in line:
            pass
        elif "queued the stack change for the player" in line:
            pass
        elif "enqueued the removal of the player " in line:
            pass
        elif "updated the player" in line:
            pass
        elif "small blind was changed from" in line:
            pass
        elif "big blind was changed from" in line:
            pass
        elif "dead small blind" in normline or "dead big blind" in normline:
            pass
        elif "uncalled bet" in normline:
            for amount, player_name in re.findall(r'Uncalled bet of (\d+) returned to "(.*)"', line):
                self._current_round.add_move(player_name, "uncalled_bet", int(amount), time)
                break
        elif re.search("run it twice", line):
            pass
        elif line.startswith("Player stacks:"):
            line = line[len("Player stacks: "):]
            entries = line.split(" | ")
            stack_sizes = [x.strip().rsplit(' ', 1)[1] for x in entries]
            stack_size_counts = [int(x.strip('()')) for x in stack_sizes]
            players = [x.split('"')[1] for x in entries]
            player_amounts = {player: stack_size for (player, stack_size) in zip(players, stack_size_counts)}
            for player, amount in player_amounts.items():
                if amount != self.evening.players[player]:
                    round_no = self._current_round.number
                    print(f"**WARNING** start of round #{round_no}: "
                          f"{player}: {amount} (amount from log) != {self.evening.players[player]} (our amount)")
                    print("winners in prev round: ", self.evening.rounds[-2].winners)
                    self.evening.players[player] = amount
        elif "-- starting hand" in line:
            if "dead button" in line:
                dealer_name = "None"
            else:
                dealer_name = line.split('"')[1]
            print(f"Started hand dealer: {dealer_name}")
            self.evening.add_round(dealer_name)
        elif line.startswith("Your hand is "):
            cards = line[len("Your hand is "):].split(", ")
            self._current_round.known_hands[self.username] = cards
        elif " shows a " in line:
            player_name = line.split('"')[1]
            assert line.endswith('.')
            cards = line.split(" shows a ")[1][:-1].split(", ")
            self._current_round.known_hands[player_name] = cards
            self._current_round.add_move(player_name, "show", 0, time)
        elif "posts a missing small blind of" in line:
            player_name = line.split('"')[1]
            small_blind = int(line.split()[-1])
            self._current_round.add_move(player_name, "missing_small_blind", small_blind, time)
        elif "posts a small blind of" in line:
            player_name = line.split('"')[1]
            small_blind = int(line.split()[-1])
            self._current_round.add_move(player_name, "small_blind", small_blind, time)
        elif "posts a missed big blind of" in line:
            player_name = line.split('"')[1]
            big_blind = int(line.split()[-1])
            self._current_round.add_move(player_name, "missing_big_blind", big_blind, time)
        elif re.search(r'"(.*)" posts a big blind of (\d+)', line):
            match = re.search(r'"(.*)" posts a big blind of (\d+)', line)
            player_name = match.group(1)
            big_blind = int(match.group(2))
            self._current_round.add_move(player_name, "big_blind", big_blind, time)
        elif re.search('"(.*)" posts a straddle of (\d+)', line):
            match = re.search('"(.*)" posts a straddle of (\d+)', line)
            player_name = match.group(1)
            straddle = int(match.group(2))
            self._current_round.add_move(player_name, "straddle", straddle, time)
        elif re.search('"(.*)" posts a straddle of (\d+)', line):
            match = re.search('"(.*)" posts a straddle of (\d+)', line)
            player_name = match.group(1)
            straddle = int(match.group(2))
            self._current_round.add_move(player_name, "straddle", straddle, time)
        elif line.endswith("folds"):
            player_name = line.split('"')[1]
            self._current_round.add_move(player_name, "fold", 0, time)
        elif line.endswith("checks"):
            player_name = line.split('"')[1]
            self._current_round.add_move(player_name, "check", 0, time)
        elif re.search(r'"(.*)" calls (\d+)$', line):
            match = re.search(r'"(.*)" calls (\d+)$', line)
            player_name = match.group(1)
            call_amount = int(match.group(2))
            self._current_round.add_move(player_name, "call", call_amount, time)
        elif re.search(r'"(.*)" calls (\d+) and go all ', line):
            match = re.search(r'"(.*)" calls (\d+) and go all ', line)
            player_name = match.group(1)
            call_amount = int(match.group(2))
            self._current_round.add_move(player_name, "call (all in)", call_amount, time)
        elif re.search(r'"(.*)" raises to (\d+)$', line):
            match = re.search(r'"(.*)" raises to (\d+)$', line)
            player_name = match.group(1)
            raise_amount = int(match.group(2))
            self._current_round.add_move(player_name, "raise", raise_amount, time)
        elif re.search(r'"(.*)" raises to (\d+) and go all ', line):
            match = re.search(r'"(.*)" raises to (\d+) and go all ', line)
            player_name = match.group(1)
            raise_amount = int(match.group(2))
            self._current_round.add_move(player_name, "raise (all in)", raise_amount, time)
        elif re.search(r'"(.*)" bets (\d+)$', line):
            # TODO: This is the first bet in a round, should be treated differently
            match = re.search(r'"(.*)" bets (\d+)$', line)
            player_name = match.group(1)
            raise_amount = int(match.group(2))
            self._current_round.add_move(player_name, "raise", raise_amount, time)
        elif re.search(r'"(.*)" bets (\d+) and go all ', line):
            # TODO: This is the first bet in a round, should be treated differently
            match = re.search(r'"(.*)" bets (\d+) and go all ', line)
            player_name = match.group(1)
            raise_amount = int(match.group(2))
            self._current_round.add_move(player_name, "raise (all in)", raise_amount, time)
        elif "raises and all in with" in line:
            player_name = line.split('"')[1]
            raise_amount = int(line.split()[-1])
            self._current_round.add_move(player_name, "raise (all in)", raise_amount, time)
        elif normline.startswith("flop"):
            card_string = line.split('[')[1].split(']')[0]
            cards = card_string.split(', ')
            self._current_round.flop = cards
        elif normline.startswith("turn (second run):"):
            card = line.split('[')[1].split(']')[0]
            self._current_round.second_turn = card
        elif normline.startswith("river (second run):"):
            card = line.split('[')[1].split(']')[0]
            self._current_round.second_river = card
        elif normline.startswith("turn:"):
            card = line.split('[')[1].split(']')[0]
            self._current_round.turn = card
        elif normline.startswith("river:"):
            card = line.split('[')[1].split(']')[0]
            self._current_round.river = card
        elif re.search(r'"(.*)" collected (\d+) from pot$', line):
            match = re.search(r'"(.*)" collected (\d+) from pot$', line)
            winner_name = match.group(1)
            win_amount = int(match.group(2))
            self._current_round.winners.append((winner_name, None, win_amount, time))
        elif re.search(r'"(.*)" collected (\d+) from pot with .* \(combination: (.*)\)', line):
            match = re.search(r'"(.*)" collected (\d+) from pot with .* \(combination: (.*)\)', line)
            winner_name = match.group(1)
            win_amount = int(match.group(2))
            combination = match.group(3)
            winning_hand = combination.split(", ")
            self._current_round.known_hands[winner_name] = winning_hand
            self._current_round.winners.append((winner_name, winning_hand, win_amount, time))
        elif " collected " in line:  # obsoleted and covered by the previous case?
            winner_name = line.split('"')[1]
            win_amount = int(line.split()[-1])
            self._current_round.winners.append((winner_name, None, win_amount, time))
        elif " wins " in line:  # obsoleted?
            winner_name, rest = line.split('"')[1:]
            amount = int(rest.split()[1])
            assert rest.endswith(')')
            winning_hand = rest.split("hand: ")[1][:-1].split(", ")
            self._current_round.known_hands[winner_name] = winning_hand
            self._current_round.winners.append((winner_name, winning_hand, amount, time))
        elif "-- ending hand" in line:
            print(self._current_round)
            # self._current_round = None
        else:
            print("**WARNING**: Unexpected line found in log. "
                  "Likely the log format has changed and this script needs to be updated.")
            print(line)
            assert False


def compute_stats(evening, args):
    win_stats = WinStats(evening)
    play_stats = PlayStats(evening, win_stats)
    preflop_stats = PreFlopStats(evening, play_stats)
    play_stats.print()
    win_stats.print()
    preflop_stats.print()
    evening.plot_progression()
    # hand_variance(evening)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("log_file", help='Path to a log file from pokernow.com')
    arg_parser.add_argument("--output", help='File to write results to')
    arg_parser.add_argument("--plot_chips", help='Attempts to plot the progression of chips')

    args = arg_parser.parse_args()

    filename = args.log_file

    p = Parser()
    evening = p.parse("", filename)
    compute_stats(evening, args)


if __name__ == "__main__":
    main()
