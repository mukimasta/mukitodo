"""Input widgets - per-field behavior and rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from toflow.models import FieldSpec
from toflow.tui.input.intent import InputIntent
from toflow.tui.pane.base import FormattedText

if TYPE_CHECKING:
    from toflow.tui.input.form import InputForm


class InputWidget(Protocol):
    def handle(self, form: InputForm, spec: FieldSpec, intent: InputIntent, payload: str = "") -> None:
        ...

    def render_row(
        self, form: InputForm, spec: FieldSpec, *, active: bool, prefix: str, label: str
    ) -> FormattedText:
        ...

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        ...


class TextWidget:
    def handle(self, form: InputForm, spec: FieldSpec, intent: InputIntent, payload: str = "") -> None:
        if intent == InputIntent.SPACE:
            form.insert_char(" ")
            return
        if intent == InputIntent.SEG_PREV:
            form.move_text_cursor(-1)
        elif intent == InputIntent.SEG_NEXT:
            form.move_text_cursor(1)
        elif intent == InputIntent.BACKSPACE:
            form.delete_back()
        elif intent == InputIntent.CHAR and payload and payload.isprintable():
            form.insert_char(payload)
        elif intent == InputIntent.INC:
            form.insert_char(payload or "+")
        elif intent == InputIntent.DEC:
            form.insert_char("-")

    def render_row(
        self, form: InputForm, spec: FieldSpec, *, active: bool, prefix: str, label: str
    ) -> FormattedText:
        value = form.get_value_str(spec.field)
        if active:
            cursor_pos = min(form.text_cursor, len(value))
            before = value[:cursor_pos]
            char_under = value[cursor_pos] if cursor_pos < len(value) else " "
            after = value[cursor_pos + 1:] if cursor_pos < len(value) else ""
            return [
                ("", prefix),
                ("class:form.active", label),
                ("class:form.value", before),
                ("class:form.cursor", char_under),
                ("class:form.value", after),
            ]
        return [
            ("", prefix),
            ("class:form.dim", label),
            ("class:form.value", value),
        ]

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        value = form.get_value_str(spec.field)
        if active:
            return [("class:form.active", f"{spec.label} "), ("class:form.value.active", value)]
        return [("class:form.dim", f"{spec.label} "), ("class:form.value", value)]


class DateWidget:
    def handle(self, form: InputForm, spec: FieldSpec, intent: InputIntent, payload: str = "") -> None:
        if intent == InputIntent.SPACE:
            form.move_date_segment(1)
            return
        if intent == InputIntent.SEG_PREV:
            form.move_date_segment(-1)
        elif intent == InputIntent.SEG_NEXT:
            form.move_date_segment(1)
        elif intent == InputIntent.BACKSPACE:
            form.clear_date()
        elif intent == InputIntent.INC:
            form.adjust_date_segment(1)
        elif intent == InputIntent.DEC:
            form.adjust_date_segment(-1)
        elif intent == InputIntent.CHAR and payload.isdigit():
            form.insert_date_digit(payload)

    def render_row(
        self, form: InputForm, spec: FieldSpec, *, active: bool, prefix: str, label: str
    ) -> FormattedText:
        value = form.get_date_display(spec.field)
        parts = [value[0:4], value[5:7], value[8:10]] if len(value) == 10 else ["____", "__", "__"]
        line: FormattedText = [
            ("", prefix),
            ("class:form.active", label) if active else ("class:form.dim", label),
        ]
        seg = form.date_segment
        for i, part in enumerate(parts):
            if i > 0:
                line.append(("class:form.value", "-"))
            if active and i == seg:
                line.append(("class:form.cursor", part))
            else:
                line.append(("class:form.value", part))
        return line

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        value = form.get_date_display(spec.field)
        style = "class:form.active" if active else "class:form.dim"
        return [(style, f"{spec.label} "), ("class:form.value", value)]


class StageWidget:
    def handle(self, form: InputForm, spec: FieldSpec, intent: InputIntent, payload: str = "") -> None:
        if intent == InputIntent.SPACE:
            form.move_stage_segment(1)
            return
        if intent == InputIntent.SEG_PREV:
            form.move_stage_segment(-1)
        elif intent == InputIntent.SEG_NEXT:
            form.move_stage_segment(1)
        elif intent == InputIntent.BACKSPACE:
            form.clear_stage_segment()
        elif intent == InputIntent.INC:
            form.adjust_stage_segment(1)
        elif intent == InputIntent.DEC:
            form.adjust_stage_segment(-1)
        elif intent == InputIntent.CHAR and payload.isdigit():
            form.insert_stage_digit(payload)

    def render_row(
        self, form: InputForm, spec: FieldSpec, *, active: bool, prefix: str, label: str
    ) -> FormattedText:
        value = form.get_stage_display()
        cur, total = value.split("/", 1) if "/" in value else ("0", "1")
        line: FormattedText = [
            ("", prefix),
            ("class:form.active", label) if active else ("class:form.dim", label),
        ]
        if active and form.stage_segment == 0:
            line.extend([("class:form.cursor", cur), ("class:form.value", "/"), ("class:form.value", total)])
        elif active and form.stage_segment == 1:
            line.extend([("class:form.value", cur), ("class:form.value", "/"), ("class:form.cursor", total)])
        else:
            line.extend([("class:form.value", cur), ("class:form.value", "/"), ("class:form.value", total)])
        return line

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        style = "class:form.active" if active else "class:form.dim"
        return [(style, f"{spec.label} "), ("class:form.value", form.get_stage_display())]


class HintWidget:
    HINT_BARS = {0: "▁", 1: "▂", 2: "▅", 3: "█"}

    def handle(self, form: InputForm, spec: FieldSpec, intent: InputIntent, payload: str = "") -> None:
        if intent == InputIntent.SPACE:
            form.adjust_hint(1, wrap=True)
        elif intent == InputIntent.INC:
            form.adjust_hint(1, wrap=False)
        elif intent == InputIntent.DEC:
            form.adjust_hint(-1, wrap=False)

    def render_row(
        self, form: InputForm, spec: FieldSpec, *, active: bool, prefix: str, label: str
    ) -> FormattedText:
        # Hints are typically rendered in grouped chip line; keep row fallback.
        return [("", prefix)] + self.render_chip(form, spec, active=active)

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        raw = form.get_value_str(spec.field)
        try:
            n = int(raw)
        except (TypeError, ValueError):
            n = 0
        n = max(0, min(3, n))
        style = "class:form.active" if active else "class:form.dim"
        return [(style, f"{spec.label} "), (f"class:hint.{n}", self.HINT_BARS.get(n, "▁"))]


class SelectWidget:
    def handle(self, form: InputForm, spec: FieldSpec, intent: InputIntent, payload: str = "") -> None:
        if intent in (InputIntent.SPACE, InputIntent.SEG_NEXT, InputIntent.INC):
            form.cycle_option(1)
        elif intent == InputIntent.DEC:
            form.cycle_option(-1)

    def render_row(
        self, form: InputForm, spec: FieldSpec, *, active: bool, prefix: str, label: str
    ) -> FormattedText:
        value = form.get_value_str(spec.field)
        if active:
            return [("", prefix), ("class:form.active", label), ("class:form.value.active", value)]
        return [("", prefix), ("class:form.dim", label), ("class:form.value", value)]

    def render_chip(self, form: InputForm, spec: FieldSpec, *, active: bool) -> FormattedText:
        value = form.get_value_str(spec.field)
        style = "class:form.active" if active else "class:form.dim"
        return [(style, f"{spec.label} "), ("class:form.value", value)]

