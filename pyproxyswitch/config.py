"""Persistent application settings and upstream proxy-list management."""

from __future__ import annotations

import json
import logging
import math
from collections.abc import ItemsView, Iterable, KeysView, Sequence, ValuesView
from pathlib import Path
from typing import Any

from .atomic_write import atomic_write_text
from .paths import CONFIG_FILE, PROXY_LIST_FILE, initialize_user_config
from .proxy_list import ProxyEntry, load_proxy_list, save_proxy_list

logger = logging.getLogger("PyProxySwitch")


class ConfigManager:
    """Load, mutate, and persist application configuration.

    The application uses a singleton by default. Tests and isolated callers can
    pass ``use_singleton=False`` and explicit paths.
    """

    _instance: ConfigManager | None = None
    _initialized = False

    def __new__(
        cls,
        config_path: str | Path | None = None,
        proxy_list_path: str | Path | None = None,
        use_singleton: bool = True,
    ) -> ConfigManager:
        if use_singleton and cls._instance is not None:
            return cls._instance
        instance = super().__new__(cls)
        if use_singleton:
            cls._instance = instance
        return instance

    def __init__(
        self,
        config_path: str | Path | None = None,
        proxy_list_path: str | Path | None = None,
        use_singleton: bool = True,
    ) -> None:
        if use_singleton and self._initialized:
            return

        self.config_path = CONFIG_FILE if config_path is None else Path(config_path).resolve()
        self.proxy_list_path = (
            PROXY_LIST_FILE if proxy_list_path is None else Path(proxy_list_path).resolve()
        )

        if config_path is None and proxy_list_path is None:
            try:
                initialize_user_config(self.config_path, self.proxy_list_path)
            except OSError as exc:
                logger.warning("Unable to initialize the user configuration: %s", exc)

        self._config: dict[str, Any] = {}
        self._proxies: list[ProxyEntry] = []
        self._proxy_names: list[str] = []
        self.load()

        if use_singleton:
            self._initialized = True

    def load(self) -> None:
        """Reload settings and proxies from disk."""

        defaults = self._get_default_config()
        try:
            if self.config_path.exists():
                with self.config_path.open(encoding="utf-8") as config_file:
                    loaded = json.load(config_file)
                if not isinstance(loaded, dict):
                    raise ValueError("The configuration root must be an object")
                if "FISRT_RUN" in loaded and "FIRST_RUN" not in loaded:
                    loaded["FIRST_RUN"] = loaded.pop("FISRT_RUN")
                self._config = self._normalize_config(defaults | loaded, defaults)
            else:
                self._config = defaults
        except (OSError, ValueError) as exc:
            logger.error("Failed to load configuration: %s", exc)
            self._config = defaults

        # Obsolete backend-selection settings are deliberately not persisted.
        self._config.pop("CMD", None)
        self._load_proxies()

    def _load_proxies(self) -> None:
        try:
            self._proxies = (
                load_proxy_list(self.proxy_list_path) if self.proxy_list_path.exists() else []
            )
        except OSError as exc:
            logger.error("Failed to load proxy list: %s", exc)
            self._proxies = []
        self._sync_proxy_names()

    def _sync_proxy_names(self) -> None:
        self._proxy_names = [proxy[0] for proxy in self._proxies]

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key == "CMD":
            self._config.pop(key, None)
            return
        old_value = self._config.get(key)
        self._config[key] = value
        if key == "LOG_PATH" and old_value != value:
            try:
                from .logger_config import update_log_path

                update_log_path()
            except Exception as exc:
                logger.warning("Failed to update log path: %s", exc)

    def update(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            self.set(key, value)

    def reload(self) -> None:
        self.load()

    def save(self) -> bool:
        """Persist settings atomically and report whether the write succeeded."""

        try:
            content = json.dumps(
                self._config,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            atomic_write_text(self.config_path, content + "\n")
        except (OSError, TypeError) as exc:
            logger.error("Failed to save configuration: %s", exc)
            return False
        return True

    def get_proxies(self) -> list[ProxyEntry]:
        return list(self._proxies)

    def get_proxy_names(self) -> list[str]:
        return list(self._proxy_names)

    def set_proxies(self, proxies: Iterable[Sequence[Any]]) -> None:
        normalized: list[ProxyEntry] = []
        for proxy in proxies:
            if len(proxy) < 3:
                continue
            fields = [str(value) for value in proxy[:6]]
            fields.extend("" for _ in range(6 - len(fields)))
            fields[3] = (fields[3] or "HTTP").upper()
            normalized.append((fields[0], fields[1], fields[2], fields[3], fields[4], fields[5]))
        self._proxies = normalized
        self._sync_proxy_names()

    def save_proxies(self) -> bool:
        """Persist the proxy list atomically and report whether the write succeeded."""

        try:
            save_proxy_list(self._proxies, self.proxy_list_path)
        except (OSError, ValueError) as exc:
            logger.error("Failed to save proxy list: %s", exc)
            return False
        return True

    def reset_to_default(self) -> None:
        self._config = self._get_default_config()

    @staticmethod
    def _normalize_config(values: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
        """Repair malformed persisted values that would otherwise crash the UI or listener."""

        normalized = dict(values)

        lang = values.get("LANG")
        normalized["LANG"] = lang if lang in {"zh_CN", "en"} else defaults["LANG"]

        for key in ("DEBUG", "FIRST_RUN", "SHOW_WELCOME"):
            value = values.get(key)
            if isinstance(value, bool):
                flag = int(value)
            elif isinstance(value, (str, int, float)):
                try:
                    flag = int(value)
                except (OverflowError, ValueError):
                    flag = defaults[key]
            else:
                flag = defaults[key]
            normalized[key] = flag if flag in (0, 1) else defaults[key]

        value = values.get("LOCAL_PORT")
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            try:
                local_port = int(value)
            except (OverflowError, ValueError):
                local_port = defaults["LOCAL_PORT"]
        else:
            local_port = defaults["LOCAL_PORT"]
        normalized["LOCAL_PORT"] = (
            local_port if 1 <= local_port <= 65535 else defaults["LOCAL_PORT"]
        )

        value = values.get("CONNECT_TIMEOUT")
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            try:
                connect_timeout = float(value)
            except ValueError:
                connect_timeout = float(defaults["CONNECT_TIMEOUT"])
        else:
            connect_timeout = float(defaults["CONNECT_TIMEOUT"])
        if not math.isfinite(connect_timeout) or connect_timeout <= 0:
            connect_timeout = float(defaults["CONNECT_TIMEOUT"])
        normalized["CONNECT_TIMEOUT"] = (
            int(connect_timeout) if connect_timeout.is_integer() else connect_timeout
        )

        local_address = values.get("LOCAL_ADDRESS")
        normalized["LOCAL_ADDRESS"] = (
            local_address.strip()
            if isinstance(local_address, str) and local_address.strip()
            else defaults["LOCAL_ADDRESS"]
        )

        for key in ("DEFAULT_ITEM", "LAST_ITEM"):
            value = values.get(key)
            normalized[key] = (
                value.strip()
                if isinstance(value, str) and value.strip()
                else defaults[key]
            )

        log_path = values.get("LOG_PATH")
        normalized["LOG_PATH"] = log_path if isinstance(log_path, str) else defaults["LOG_PATH"]
        return normalized

    @staticmethod
    def _get_default_config() -> dict[str, Any]:
        return {
            "CONNECT_TIMEOUT": 15,
            "DEBUG": 0,
            "DEFAULT_ITEM": "NoProxy",
            "FIRST_RUN": 0,
            "LANG": "zh_CN",
            "LAST_ITEM": "NoProxy",
            "LOCAL_ADDRESS": "127.0.0.1",
            "LOCAL_PORT": 8888,
            "LOG_PATH": "",
            "SHOW_WELCOME": 0,
        }

    def __getitem__(self, key: str) -> Any:
        return self._config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return key in self._config

    def keys(self) -> KeysView[str]:
        return self._config.keys()

    def values(self) -> ValuesView[Any]:
        return self._config.values()

    def items(self) -> ItemsView[str, Any]:
        return self._config.items()

    def __repr__(self) -> str:
        return f"ConfigManager(config_path={self.config_path}, proxies={len(self._proxies)})"

    def get_config_path(self) -> Path:
        return self.config_path

    def get_proxy_list_path(self) -> Path:
        return self.proxy_list_path

    @classmethod
    def get_instance(cls) -> ConfigManager | None:
        return cls._instance

    @classmethod
    def reset_singleton(cls) -> None:
        cls._instance = None
        cls._initialized = False


__all__ = ["ConfigManager"]
