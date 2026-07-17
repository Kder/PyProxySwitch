"""Persistent application settings and upstream proxy-list management."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .paths import CONFIG_FILE, PROXY_LIST_FILE, initialize_user_config
from .proxy_list import ProxyEntry, load_proxy_list, save_proxy_list

logger = logging.getLogger("PyProxySwitch")
SequenceLike = list[Any] | tuple[Any, ...]


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
                self._config = defaults | loaded
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
        old_value = self._config.get(key)
        self._config[key] = value
        if key == "LOG_PATH" and old_value != value:
            try:
                from .logger_config import update_log_path

                update_log_path()
            except Exception as exc:
                logger.warning("Failed to update log path: %s", exc)

    def update(self, values: dict[str, Any]) -> None:
        self._config.update(values)

    def reload(self) -> None:
        self.load()

    def save(self) -> None:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with self.config_path.open("w", encoding="utf-8") as config_file:
                json.dump(
                    self._config,
                    config_file,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                config_file.write("\n")
        except (OSError, TypeError) as exc:
            logger.error("Failed to save configuration: %s", exc)

    def get_proxies(self) -> list[ProxyEntry]:
        return list(self._proxies)

    def get_proxy_names(self) -> list[str]:
        return list(self._proxy_names)

    def set_proxies(self, proxies: list[SequenceLike]) -> None:
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

    def save_proxies(self) -> None:
        try:
            save_proxy_list(self._proxies, self.proxy_list_path)
        except (OSError, ValueError) as exc:
            logger.error("Failed to save proxy list: %s", exc)

    def reset_to_default(self) -> None:
        self._config = self._get_default_config()

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

    def keys(self):
        return self._config.keys()

    def values(self):
        return self._config.values()

    def items(self):
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
