import logging

import pytest

from expense_tracker import cli


# ---------------------------------------------------------------------------
# input_transaction
# ---------------------------------------------------------------------------

class TestInputTransaction:
    def test_returns_none_and_logs_when_user_cancels(self, monkeypatch, caplog, capsys):
        monkeypatch.setattr(cli, "input_transaction1", lambda d: None)

        with caplog.at_level(logging.WARNING, logger="expense_tracker.cli"):
            result = cli.input_transaction("income")

        assert result is None
        assert any("canceled" in r.message.lower() for r in caplog.records)
        assert "canceled" in capsys.readouterr().out.lower()

    def test_treats_any_falsy_result_as_cancellation(self, monkeypatch):
        """`if not transaction:` treats ANY falsy value, not just None, as a cancellation —
        an empty dict from input_transaction1 is (incorrectly) indistinguishable from a
        real cancel here."""
        monkeypatch.setattr(cli, "input_transaction1", lambda d: {})
        assert cli.input_transaction("income") is None

    @pytest.mark.parametrize("transaction_type", ["income", "expense"])
    def test_attaches_type_for_known_transaction_types(self, monkeypatch, transaction_type):
        monkeypatch.setattr(cli, "input_transaction1", lambda d: {"amount": 10, "category": "food"})
        result = cli.input_transaction(transaction_type)
        assert result["type"] == transaction_type

    @pytest.mark.parametrize("transaction_type", ["", "unknown", "transfer"])
    def test_does_not_attach_type_for_unrecognized_transaction_types(self, monkeypatch, transaction_type):
        """Edge case: for any transaction_type outside {"income", "expense"} (including the
        default ""), the returned dict silently has no "type" key at all."""
        monkeypatch.setattr(cli, "input_transaction1", lambda d: {"amount": 10, "category": "food"})
        result = cli.input_transaction(transaction_type)
        assert "type" not in result
