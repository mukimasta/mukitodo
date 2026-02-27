"""Input intents - abstract actions from key events."""

from enum import Enum


class InputIntent(str, Enum):
    FIELD_NEXT = "field_next"
    FIELD_PREV = "field_prev"
    SPACE = "space"
    SEG_NEXT = "seg_next"
    SEG_PREV = "seg_prev"
    INC = "inc"
    DEC = "dec"
    BACKSPACE = "backspace"
    CHAR = "char"
