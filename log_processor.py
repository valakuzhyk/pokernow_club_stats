import sys
import csv
import statistics
import colorama 
from typing import List, Set
from termcolor import colored
colorama.init()


from collections import defaultdict



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

CARD_ORDER = ['2', '3','4', '5','6','7','8','9','T','J','Q','K','A']

class Player():
    def __init__(self, starting_amount):
        self.stack_amt = starting_amount

class Evening():
    def __init__(self, username):
        self.username = username
        self.rounds = []
        self.players = {}
        self.historical_amounts = defaultdict(list)

    def plot_progression(self):
        import matplotlib.pyplot as plt 

        for player, amts in self.historical_amounts.items():
            plt.plot(range(len(amts)), amts, label= player)
        
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
        new_round = Round(dealer, self.players)
        self.rounds.append(new_round)
        return new_round

    def _record_amounts(self):
        for player, amt in self.players.items():
            self.historical_amounts[player].append(amt)

    def _update_amounts(self):
        last_round = self.rounds[-1]
        spent = last_round.money_spent()
        pot_size = sum(spent.values())
        for user, amount in spent.items():
            self.players[user] -= amount

        for (winner_name, hand, amt, _) in last_round.winners:
            if hand is None:
                self.players[winner_name] += pot_size
                assert len(last_round.winners) == 1
                break
            else:
                self.players[winner_name] += amt

class Action():
    def __init__(self, player, action_name, amount, time_stamp):
        self.player = player
        self.action_name = action_name
        self.amount = amount
        self.time_stamp = time_stamp

    def __str__(self):
        return f"{self.player} {self.action_name} {self.amount}"

    def __repr__(self):
        return self.__str__()

class Round():
    def __init__(self, dealer, players):
        self.initial_amounts = {name: amt for (name, amt) in players.items()}
        self.dealer = dealer
        self.winners = []

        # Username to hand
        self.known_hands = {}

        self.flop = None
        self.turn = None
        self.river = None

        self.preflop_moves : List[Action] = []
        self.flop_moves : List[Action] = []
        self.turn_moves : List[Action] = []
        self.river_moves : List[Action] = []

    @property
    def small_blind(self) -> (str, int):
        small_blind_action = [x for x in self.preflop_moves if x.action_name == "small_blind"][0]
        return (small_blind_action.player, small_blind_action.amount)

    @property
    def big_blind(self) -> (str, int):
        big_blind_action = [x for x in self.preflop_moves if x.action_name == "big_blind"][0]
        return (big_blind_action.player, big_blind_action.amount)
    
    def find_moves(self, player, action_name, moves):
        return [move for move in moves if (move.player == player and move.action_name == action_name)]


    def money_in_round(self, moves):
        """
        How much money was spent by each player in a round
        """
        spent = {}
        for m in moves:
            if m.amount > 0: # ignore all moves that don't involve money
                spent[m.player] = m.amount
        return spent

    def money_spent(self):
        spent = defaultdict(int)
        for moves in [self.preflop_moves, self.flop_moves, self.turn_moves, self.river_moves]:
            for player, amount in self.money_in_round(moves).items():
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
        s = f"Game: {self.initial_amounts}\n"
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


class Parser():
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
        if "created the game with a stack of" in line or "The admin approved" in line:
            player_name = line.split('"')[1]
            start_amount = int(line.split()[-1][:-1])
            self.evening.add_player(player_name, start_amount)
        elif line == "entry":
            pass
        elif "requested a seat" in line:
            pass
        elif "stand up with the stack" in line:
            print(line)
        elif "sit back with the stack" in line:
            pass
        elif "quits the game with a stack of" in line:
            pass
        elif "joined the game with a stack of" in line:
            pass
        elif "passed the room ownership" in line:
            pass
        elif "-- starting hand" in line:
            if "dead button" in line:
                dealer_name = "None"
            else:
                dealer_name = line.split('"')[1]
            print(f"Started hand dealer: {dealer_name}")
            self.evening.add_round(dealer_name)
        elif line.startswith("Your hand is "):
            cards = line[len("Your hand is "): ].split(", ")
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
            small_blind = int(line.split()[-1])
            self._current_round.add_move(player_name, "missing_big_blind", small_blind, time)
        elif "posts a big blind of" in line:
            player_name = line.split('"')[1]
            big_blind = int(line.split()[-1])
            self._current_round.add_move(player_name, "big_blind", big_blind, time)
        elif line.endswith("folds"):
            player_name = line.split('"')[1]
            self._current_round.add_move(player_name, "fold", 0, time)
        elif line.endswith("checks"):
            player_name = line.split('"')[1]
            self._current_round.add_move(player_name, "check", 0, time)
        elif "calls with" in line:
            player_name = line.split('"')[1]
            call_amount = int(line.split()[-1])
            self._current_round.add_move(player_name, "call", call_amount, time)
        elif "calls and all in with" in line:
            player_name = line.split('"')[1]
            raise_amount = int(line.split()[-1])
            self._current_round.add_move(player_name, "call (all in)", raise_amount, time)
        elif "raises with" in line:
            player_name = line.split('"')[1]
            raise_amount = int(line.split()[-1])
            self._current_round.add_move(player_name, "raise", raise_amount, time)
        elif "raises and all in with" in line:
            player_name = line.split('"')[1]
            raise_amount = int(line.split()[-1])
            self._current_round.add_move(player_name, "raise (all in)", raise_amount, time)
        elif line.startswith("flop"):
            card_string = line.split('[')[1].split(']')[0]
            cards = card_string.split(', ')
            self._current_round.flop = cards
        elif line.startswith("turn"):
            card = line.split('[')[1].split(']')[0]
            self._current_round.turn = card
        elif line.startswith("river"):
            card = line.split('[')[1].split(']')[0]
            self._current_round.river = card
        elif " gained " in line:
            winner_name = line.split('"')[1]
            win_amount = int(line.split()[-1])
            self._current_round.winners.append((winner_name, None, win_amount, time))
        elif " wins " in line:
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
            print(line)
            assert False

class WinStats:
    def __init__(self, evening):
        # # of wins
        # avg size of wins
        self.evening = evening
        wins = defaultdict(list)
        showdown_wins = defaultdict(list)
        preshowdown_wins = defaultdict(list)
        for round in evening.rounds:
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
            median_win_amt = statistics.median(win_amts)
            median_showdown_amt = statistics.median(showdown_wins[player])
            median_preshowdown_amt = statistics.median(preshowdown_wins[player])

            print(colored(f"  {player}", "white", attrs=["bold"]))
            print(f"    # wins (median): {num_wins:>2} ({median_win_amt:0.0f})")
            print(f"       %    showdown (median): {pct_at_showdown:>6.2f}% ({median_showdown_amt:0.0f})")
            print(f"       % preshowdown (median): {pct_at_preshowdown:>6.2f}% ({median_preshowdown_amt:0.0f})")
        print()

class PlayStats:
    def __init__(self, evening: Evening, win_stats: WinStats):
        self.evening = evening
        self.win_stats = win_stats
        rounds_present = defaultdict(int)
        rounds_contributed = defaultdict(int)
        showdowns_played = defaultdict(int)
        for round in evening.rounds:
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
        total_rounds = len(self.evening.rounds)
        print(f"Rounds: {total_rounds}")
        for player in self.evening.players.keys():
            total_rounds = self.rounds_present[player]
            player_wins = len(self.win_stats.wins[player])
            player_showdown_wins = len(self.win_stats.showdown_wins[player])
            pct_played = safe_div(self.rounds_contributed[player], total_rounds) * 100
            pct_played_wins = safe_div(player_wins, self.rounds_contributed[player]) *  100
            pct_showdown_wins = safe_div(player_showdown_wins, self.showdowns_played[player]) * 100
    
            print(colored(f"  Player: {player}", "white", attrs=["bold"]))
            print(f"    Voluntary Contrib.  / Present  (VC%) : {self.rounds_contributed[player]:>3d} / {total_rounds:>3d} ({pct_played:>6.2f}%)")
            print(f"    Games     won / VC (% won)           : {player_wins:>3d} / {self.rounds_contributed[player]:>3d} ({pct_played_wins:>6.2f}%)" )
            print(f"    Showdowns won / VC (% won)           : {player_showdown_wins:>3d} / {self.showdowns_played[player]:>3d} ({pct_showdown_wins:>6.2f}%)")
        print()

class PreFlopStats:
    def __init__(self, evening: Evening):
        # How many times did you limp
        # How many times did you call, what was your avg call
        # How many times did you raise, what was your avg raise
        self.evening = evening
        limp_rounds = defaultdict(list)
        raise_amts = defaultdict(list)
        raise_rounds = defaultdict(list)

        for round in evening.rounds:
            preflop_amounts = round.money_in_round(round.preflop_moves)
            for player, amt in preflop_amounts.items():
                if amt == round.big_blind[1] and len(round.find_moves(player, "fold", round.preflop_moves)):
                    limp_rounds[player].append(round)

            # In case there are multiple raises in a single round
            round_raises = {}
            for move in round.preflop_moves:
                if move.action_name == "raise":
                    round_raises[move.player] = move.amount

            for player, amt in round_raises.items():
                raise_amts[player].append(amt)
                raise_rounds[player].append(round)

        self.limp_rounds = limp_rounds
        self.raise_amts = raise_amts
        self.raise_rounds = raise_rounds

    def print(self):
        print(colored("Preflop Behavior:", "white", attrs=["underline"]))
        for player in self.evening.players.keys():

    
            print(colored(f"  Player: {player}", "white", attrs=["bold"]))
            print(f"    # Limped           : {len(self.limp_rounds[player]):>3}")
            print(f"    # Raise (avg amt)  : {len(self.raise_rounds[player]):>3} ({avg(self.raise_amts[player]):.0f})") 
        print()


def fold_stats():
    # What amount causes a person to fold (absolute) vs (relative to pot)
    pass

def RandomnessStats(evening: Evening):
    player = evening.username
    player_hands = [round.known_hands[player] for round in evening.rounds if player in round.known_hands]
    
    val_counts = defaultdict(int)
    hands = []
    for c1, c2 in player_hands:
        c1 = c1.replace("10", "T")
        c2 = c2.replace("10", "T")
        val_counts[c1[0]] += 1
        val_counts[c1[-1]] += 1
        val_counts[c2[0]] += 1
        val_counts[c2[-1]] += 1

        if c1[0] != c2[0]:
            if c1[-1] == c2[-1]:
                suited = "s"
            else:
                suited = "o"
            if CARD_ORDER.index(c1[0]) > CARD_ORDER.index(c2[0]):
                hands.append(c1[0] + c2[0] + suited)
            else:
                hands.append(c2[0] + c1[0] + suited)
        else:
            hands.append(c1[0] + c2[0])
            
    card_count = len(player_hands) * 2

    val_counts = {k:v/card_count for k,v in val_counts.items()}
    sorted_keys = sorted(val_counts.keys())
    for k in sorted_keys:
        print(f"{k} : {val_counts[k] * 100:>3.2f}%")
    


    hand_ranks = {row[1]:float(row[0]) for row in csv.reader(open("hand_order.txt"))}
    ranks = [hand_ranks[hand] for hand in hands]

    print("Median: ", statistics.median(ranks)) 



def compute_stats(evening):
    win_stats = WinStats(evening)
    play_stats = PlayStats(evening, win_stats)
    preflop_stats = PreFlopStats(evening)
    play_stats.print()
    win_stats.print()
    preflop_stats.print()
    # evening.plot_progression()
    # RandomnessStats(evening)

def main():
    filename = sys.argv[1]
    p = Parser()
    evening = p.parse("", filename)
    compute_stats(evening)

def avg(vals):
    return safe_div(sum(vals), len(vals))

def safe_div(numer, denom) -> int:
    if denom == 0:
        return 0
    return numer / denom


if __name__ == "__main__":
    main()