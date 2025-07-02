from enum import Enum, auto

class FilterType(Enum):
    PRICE = auto()
    NOVELTY = auto()
    TEMPLATE = auto()

class GiftPriority(Enum):
    CHEAPEST_FIRST = auto()
    NEWEST_FIRST = auto()
    BEST_VALUE = auto()