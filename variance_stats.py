import statistics
from collections import defaultdict
from utilities import CARD_ORDER, hand_ranks


def hand_variance(evening):
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

    val_counts = {k: v / card_count for k, v in val_counts.items()}
    sorted_keys = sorted(val_counts.keys())
    for k in sorted_keys:
        print(f"{k} : {val_counts[k] * 100:>3.2f}%")

    ranks = [hand_ranks()[hand] for hand in hands]

    print("Median: ", statistics.median(ranks))

def flop_variance(evening):
    flops =  [round.flop for round in evening.rounds if round.flop is not None]

    same_suit_flops = [flop for flop in flops if flop[0][1] == flop[1][1] and flop[1][1] == flop[2][1]]
    print(same_suit_flops)

    print(f"Percentage of flops that were the same suit is {len(same_suit_flops)/len(flops)}")    