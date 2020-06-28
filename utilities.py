import csv
import statistics

CARD_ORDER = "23456789TJQKA"

def avg(vals):
    return safe_div(sum(vals), len(vals))


def safe_div(numer, denom) -> int:
    if denom == 0:
        return 0
    return numer / denom

def hand_ranks():
    return {row[1]: float(row[0]) for row in csv.reader(open("resources/hand_order.txt"))}

def median(vals):
    if len(vals) == 0:
        return 0
    return statistics.median(vals)