import builtins
import logging

import pytest

from cli import input as cli_input


def feed(monkeypatch, values):
    """Feeds canned responses to builtins.input(), one per call, in order."""
    it = iter(values)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(it))


def counting_input(monkeypatch, values):
    """Like feed(), but also returns the list of prompts input() was actually called
    with, so a test can assert how many times (and with what) it was invoked."""
    it = iter(values)
    calls = []

    def fake_input(prompt=""):
        calls.append(prompt)
        return next(it)

    monkeypatch.setattr(builtins, "input", fake_input)
    return calls


# ---------------------------------------------------------------------------
# base_input
# ---------------------------------------------------------------------------

class TestBaseInput:
    def test_lowercase_q_raises_stop_iteration(self, monkeypatch):
        feed(monkeypatch, ["q"])
        with pytest.raises(StopIteration):
            cli_input.base_input("prompt", str)

    def test_uppercase_q_also_cancels(self, monkeypatch):
        """Unlike expense_tracker.cli.is_cancel_requested (deliberately case-sensitive),
        base_input lowercases the input before comparing, so 'Q' cancels too."""
        feed(monkeypatch, ["Q"])
        with pytest.raises(StopIteration):
            cli_input.base_input("prompt", str)

    def test_whitespace_padded_q_cancels(self, monkeypatch):
        """strip() runs before the 'q' check, so surrounding whitespace doesn't defeat it."""
        feed(monkeypatch, ["  q  "])
        with pytest.raises(StopIteration):
            cli_input.base_input("prompt", str)

    def test_empty_string_raises_value_error(self, monkeypatch):
        feed(monkeypatch, [""])
        with pytest.raises(ValueError):
            cli_input.base_input("prompt", str)

    def test_whitespace_only_input_raises_value_error(self, monkeypatch):
        """Boundary: a string that is non-empty before strip() but empty after it must
        still be treated as blank, not as literal whitespace content."""
        feed(monkeypatch, ["   "])
        with pytest.raises(ValueError):
            cli_input.base_input("prompt", str)

    def test_str_type_returns_stripped_value(self, monkeypatch):
        feed(monkeypatch, ["  hello  "])
        assert cli_input.base_input("prompt", str) == "hello"

    def test_int_type_rejects_non_numeric_text(self, monkeypatch):
        feed(monkeypatch, ["abc"])
        with pytest.raises(ValueError):
            cli_input.base_input("prompt", int)

    def test_int_type_accepts_negative_numbers(self, monkeypatch):
        feed(monkeypatch, ["-5"])
        assert cli_input.base_input("prompt", int) == -5

    def test_float_type_rejects_non_numeric_text(self, monkeypatch):
        feed(monkeypatch, ["abc"])
        with pytest.raises(ValueError):
            cli_input.base_input("prompt", float)

    def test_float_type_accepts_integer_looking_text(self, monkeypatch):
        feed(monkeypatch, ["42"])
        assert cli_input.base_input("prompt", float) == 42.0

    def test_unsupported_data_type_raises_type_error(self, monkeypatch):
        feed(monkeypatch, ["whatever"])
        with pytest.raises(TypeError):
            cli_input.base_input("prompt", list)


# ---------------------------------------------------------------------------
# input_value
# ---------------------------------------------------------------------------

class TestInputValue:
    def test_cancel_returns_none_instead_of_raising(self, monkeypatch):
        feed(monkeypatch, ["q"])
        assert cli_input.input_value("prompt", str) is None

    def test_retries_after_invalid_input_until_valid(self, monkeypatch, capsys):
        feed(monkeypatch, ["abc", "", "7"])
        assert cli_input.input_value("prompt", int) == 7
        assert capsys.readouterr().out.count("Invalid input") == 2

    def test_custom_error_message_is_shown_on_invalid_input(self, monkeypatch, capsys):
        feed(monkeypatch, ["abc", "7"])
        cli_input.input_value("prompt", int, error_msg="Custom error")
        assert "Custom error" in capsys.readouterr().out

    def test_default_error_message_names_the_expected_type(self, monkeypatch, capsys):
        feed(monkeypatch, ["abc", "1.5"])
        cli_input.input_value("prompt", float)
        assert "valid float" in capsys.readouterr().out

    def test_unsupported_type_error_is_not_swallowed(self, monkeypatch):
        """TypeError (unsupported data_type) is a programming error, not a user-input
        mistake — input_value only catches StopIteration/ValueError, so it must propagate."""
        feed(monkeypatch, ["x"])
        with pytest.raises(TypeError):
            cli_input.input_value("prompt", dict)


# ---------------------------------------------------------------------------
# input_category
# ---------------------------------------------------------------------------

class TestInputCategory:
    CATEGORIES = {"food": 15000, "rent": 10000, "medicine": 5000}

    def test_cancel_before_any_choice_returns_none(self, monkeypatch):
        feed(monkeypatch, ["q"])
        assert cli_input.input_category(self.CATEGORIES) is None

    def test_first_option_boundary(self, monkeypatch):
        feed(monkeypatch, ["1"])
        assert cli_input.input_category(self.CATEGORIES) == "food"

    def test_last_option_boundary(self, monkeypatch):
        feed(monkeypatch, ["3"])
        assert cli_input.input_category(self.CATEGORIES) == "medicine"

    def test_zero_is_rejected_as_out_of_range(self, monkeypatch, capsys):
        """Boundary: index 0 must not be accepted even though the list is 1-indexed for
        display."""
        feed(monkeypatch, ["0", "1"])
        assert cli_input.input_category(self.CATEGORIES) == "food"
        assert "between 1 and 3" in capsys.readouterr().out

    def test_negative_number_is_rejected(self, monkeypatch, capsys):
        feed(monkeypatch, ["-1", "2"])
        assert cli_input.input_category(self.CATEGORIES) == "rent"
        assert "between 1 and 3" in capsys.readouterr().out

    def test_number_past_the_end_is_rejected(self, monkeypatch, capsys):
        feed(monkeypatch, ["4", "2"])
        assert cli_input.input_category(self.CATEGORIES) == "rent"
        assert "between 1 and 3" in capsys.readouterr().out

    def test_non_numeric_choice_is_rejected_then_recovers(self, monkeypatch):
        feed(monkeypatch, ["abc", "2"])
        assert cli_input.input_category(self.CATEGORIES) == "rent"

    def test_cancel_after_an_invalid_attempt_still_cancels(self, monkeypatch):
        """Regression guard: the retry loop must check for None (cancel) on every
        iteration, not only exit via a valid selection."""
        feed(monkeypatch, ["99", "q"])
        assert cli_input.input_category(self.CATEGORIES) is None

    def test_single_category_dict_only_choice_is_one(self, monkeypatch):
        feed(monkeypatch, ["1"])
        assert cli_input.input_category({"only": 100}) == "only"

    def test_menu_lists_every_category_with_its_budget(self, monkeypatch, capsys):
        feed(monkeypatch, ["1"])
        cli_input.input_category(self.CATEGORIES)
        out = capsys.readouterr().out
        assert "food (budget: 15000)" in out
        assert "rent (budget: 10000)" in out
        assert "medicine (budget: 5000)" in out


# ---------------------------------------------------------------------------
# input_transaction1
# ---------------------------------------------------------------------------

class TestInputTransaction1:
    def test_plain_fields_are_collected_in_order(self, monkeypatch):
        feed(monkeypatch, ["100", "food"])
        result = cli_input.input_transaction1({"amount": float, "category": str})
        assert result == {"amount": 100.0, "category": "food"}

    def test_dict_spec_field_routes_through_category_picker(self, monkeypatch):
        feed(monkeypatch, ["100", "2"])
        categories = {"food": 15000, "rent": 10000}
        result = cli_input.input_transaction1({"amount": float, "category": categories})
        assert result == {"amount": 100.0, "category": "rent"}

    def test_cancel_on_first_field_does_not_prompt_for_the_rest(self, monkeypatch):
        calls = counting_input(monkeypatch, ["q"])
        result = cli_input.input_transaction1({"amount": float, "category": str})
        assert result is None
        assert len(calls) == 1

    def test_cancel_on_later_field_returns_none_not_a_partial_dict(self, monkeypatch):
        feed(monkeypatch, ["100", "q"])
        result = cli_input.input_transaction1({"amount": float, "category": str})
        assert result is None

    def test_cancel_inside_category_picker_cancels_whole_transaction(self, monkeypatch):
        feed(monkeypatch, ["q"])
        categories = {"food": 15000, "rent": 10000}
        result = cli_input.input_transaction1({"category": categories, "amount": float})
        assert result is None

    def test_empty_spec_dict_returns_empty_transaction(self, monkeypatch):
        """No fields to collect -> nothing is ever read from input()."""
        calls = counting_input(monkeypatch, [])
        assert cli_input.input_transaction1({}) == {}
        assert calls == []


# ---------------------------------------------------------------------------
# input_int / input_index_to_delete
# ---------------------------------------------------------------------------

class TestInputIntAndIndexToDelete:
    def test_input_int_cancel_returns_none(self, monkeypatch):
        feed(monkeypatch, ["q"])
        assert cli_input.input_int("prompt") is None

    def test_input_int_retries_on_non_numeric_input(self, monkeypatch):
        feed(monkeypatch, ["abc", "5"])
        assert cli_input.input_int("prompt") == 5

    def test_input_index_to_delete_cancel_returns_none(self, monkeypatch):
        feed(monkeypatch, ["q"])
        assert cli_input.input_index_to_delete("prompt") is None

    def test_input_index_to_delete_accepts_zero_and_negative_values(self, monkeypatch):
        """input_index_to_delete itself does no range checking — that's left to the
        caller (ExpenseTracker.remove_transaction), so 0/negative values must pass through."""
        feed(monkeypatch, ["0"])
        assert cli_input.input_index_to_delete("prompt") == 0

        feed(monkeypatch, ["-3"])
        assert cli_input.input_index_to_delete("prompt") == -3
