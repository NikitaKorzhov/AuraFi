"""Homework 23: settings for the one-shot CLI (`cli.py`/`main.py`'s `run_cli()`).

Only `config.ini` loading lives here — `.env` is already loaded as a side
effect of importing `database` (every entry point already does, directly or
transitively), so a second `.env` reader would just duplicate that.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path

import database  # noqa: F401 — import side effect: loads .env into os.environ

_BASE_DIR = Path(__file__).resolve().parent
_CONFIG_INI_PATH = _BASE_DIR / "config.ini"


def load_config(config_path: Path | str = _CONFIG_INI_PATH) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    return config


def get_settings() -> dict:
    config = load_config()

    return {
        # .env — environment-dependent / secret-shaped
        "debug": os.environ.get("DEBUG", "false").lower() == "true",
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        "base_currency": os.environ.get("BASE_CURRENCY", "UAH"),
        "exchange_api_key": os.environ.get("EXCHANGE_API_KEY", ""),
        "cli_user_id": int(os.environ.get("CLI_USER_ID", "1")),
        # config.ini — public
        "app_name": config.get("app", "name", fallback="AuraFi"),
        "app_version": config.get("app", "version", fallback="0.3.0"),
        "export_dir": config.get("storage", "export_dir", fallback="exports/"),
        "warn_budget_pct": config.getfloat("limits", "warn_budget_pct", fallback=80.0),
    }
