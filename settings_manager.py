"""
Settings Manager for persistent configuration with per-exchange settings.
Provides thread-safe access to settings and handles JSON persistence.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from config import DEFAULT_SETTINGS, DEFAULT_EXCHANGE_SETTINGS

logger = logging.getLogger(__name__)


class SettingsManager:
    """Thread-safe settings manager with JSON persistence and hierarchical resolution."""
    
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = Path(settings_file)
        self._lock = threading.Lock()
        self._settings = {}
        self._load_settings()
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        Deep merge two dictionaries.
        Values from override take precedence, but nested dicts are merged recursively.
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _load_settings(self):
        """Load settings from JSON file, merge with defaults."""
        with self._lock:
            if self.settings_file.exists():
                try:
                    with open(self.settings_file, 'r') as f:
                        loaded = json.load(f)
                    # Deep merge loaded settings with defaults to preserve nested structure
                    self._settings = self._deep_merge(DEFAULT_SETTINGS, loaded)
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Error loading settings: {e}, using defaults")
                    self._settings = DEFAULT_SETTINGS.copy()
            else:
                # Create file with empty dict (will use defaults)
                self._settings = DEFAULT_SETTINGS.copy()
                self._save_settings()
    
    def _save_settings(self):
        """Persist current settings to JSON file."""
        # Called within lock context by callers
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving settings: {e}")
    
    # Global Settings Properties
    
    @property
    def alerts_enabled(self) -> bool:
        with self._lock:
            return self._settings.get("alerts_enabled", False)
    
    @alerts_enabled.setter
    def alerts_enabled(self, value: bool):
        with self._lock:
            self._settings["alerts_enabled"] = value
            self._save_settings()
    
    @property
    def chat_id(self) -> str:
        with self._lock:
            return self._settings.get("chat_id", DEFAULT_SETTINGS["chat_id"])
    
    @chat_id.setter
    def chat_id(self, value: str):
        with self._lock:
            self._settings["chat_id"] = value
            self._save_settings()
    
    @property
    def global_distance(self) -> float:
        with self._lock:
            return self._settings.get("global_distance_pct", DEFAULT_SETTINGS["global_distance_pct"])
    
    @global_distance.setter
    def global_distance(self, value: float):
        with self._lock:
            self._settings["global_distance_pct"] = value
            self._save_settings()
    
    @property
    def scan_interval(self) -> int:
        with self._lock:
            return self._settings.get("scan_interval", DEFAULT_SETTINGS["scan_interval"])
    
    @scan_interval.setter
    def scan_interval(self, value: int):
        with self._lock:
            self._settings["scan_interval"] = value
            self._save_settings()
    
    @property
    def orderbook_depth(self) -> int:
        with self._lock:
            return self._settings.get("orderbook_depth", DEFAULT_SETTINGS["orderbook_depth"])
    
    @orderbook_depth.setter
    def orderbook_depth(self, value: int):
        with self._lock:
            self._settings["orderbook_depth"] = value
            self._save_settings()
    
    @property
    def global_blacklist(self) -> List[str]:
        """Get the global blacklist."""
        with self._lock:
            return self._settings.get("global_blacklist", []).copy()
    
    @property
    def global_ticker_overrides(self) -> Dict[str, int]:
        """Get the global ticker overrides."""
        with self._lock:
            return self._settings.get("global_ticker_overrides", {}).copy()
    
    @property
    def authorized_users(self) -> List[int]:
        with self._lock:
            return self._settings.get("authorized_users", []).copy()
    
    @property
    def quote_currencies(self) -> List[str]:
        with self._lock:
            return self._settings.get("quote_currencies", DEFAULT_SETTINGS["quote_currencies"]).copy()
    
    # Global Blacklist Management
    
    def add_global_blacklist(self, ticker: str):
        """Add a ticker to the global blacklist."""
        ticker = ticker.upper()
        with self._lock:
            if "global_blacklist" not in self._settings:
                self._settings["global_blacklist"] = []
            if ticker not in self._settings["global_blacklist"]:
                self._settings["global_blacklist"].append(ticker)
                self._save_settings()
    
    def remove_global_blacklist(self, ticker: str):
        """Remove a ticker from the global blacklist."""
        ticker = ticker.upper()
        with self._lock:
            if "global_blacklist" in self._settings and ticker in self._settings["global_blacklist"]:
                self._settings["global_blacklist"].remove(ticker)
                self._save_settings()
    
    def clear_global_blacklist(self):
        """Clear the entire global blacklist."""
        with self._lock:
            self._settings["global_blacklist"] = []
            self._save_settings()
    
    # Global Ticker Overrides Management
    
    def set_global_ticker_override(self, ticker: str, min_size: int):
        """Set global ticker override."""
        ticker = ticker.upper()
        with self._lock:
            if "global_ticker_overrides" not in self._settings:
                self._settings["global_ticker_overrides"] = {}
            self._settings["global_ticker_overrides"][ticker] = min_size
            self._save_settings()
    
    def remove_global_ticker_override(self, ticker: str):
        """Remove global ticker override."""
        ticker = ticker.upper()
        with self._lock:
            if "global_ticker_overrides" in self._settings:
                if ticker in self._settings["global_ticker_overrides"]:
                    del self._settings["global_ticker_overrides"][ticker]
                    self._save_settings()
    
    # Exchange Settings Management
    
    def get_exchange_min_size(self, exchange: str) -> int:
        """Get min_size for a specific exchange."""
        exchange = exchange.lower()
        with self._lock:
            exchanges = self._settings.get("exchanges", {})
            exch_settings = exchanges.get(exchange, {})
            return exch_settings.get("min_size", DEFAULT_EXCHANGE_SETTINGS["min_size"])
    
    def set_exchange_min_size(self, exchange: str, value: int):
        """Set min_size for a specific exchange."""
        exchange = exchange.lower()
        with self._lock:
            if "exchanges" not in self._settings:
                self._settings["exchanges"] = {}
            if exchange not in self._settings["exchanges"]:
                self._settings["exchanges"][exchange] = DEFAULT_EXCHANGE_SETTINGS.copy()
            self._settings["exchanges"][exchange]["min_size"] = value
            self._save_settings()
    
    def get_exchange_min_lifetime(self, exchange: str) -> int:
        """Get min_lifetime for a specific exchange."""
        exchange = exchange.lower()
        with self._lock:
            exchanges = self._settings.get("exchanges", {})
            exch_settings = exchanges.get(exchange, {})
            return exch_settings.get("min_lifetime", DEFAULT_EXCHANGE_SETTINGS["min_lifetime"])
    
    def set_exchange_min_lifetime(self, exchange: str, value: int):
        """Set min_lifetime for a specific exchange."""
        exchange = exchange.lower()
        with self._lock:
            if "exchanges" not in self._settings:
                self._settings["exchanges"] = {}
            if exchange not in self._settings["exchanges"]:
                self._settings["exchanges"][exchange] = DEFAULT_EXCHANGE_SETTINGS.copy()
            self._settings["exchanges"][exchange]["min_lifetime"] = value
            self._save_settings()
    
    def get_exchange_ticker_overrides(self, exchange: str) -> Dict[str, int]:
        """Get ticker overrides for a specific exchange."""
        exchange = exchange.lower()
        with self._lock:
            exchanges = self._settings.get("exchanges", {})
            exch_settings = exchanges.get(exchange, {})
            return exch_settings.get("ticker_overrides", {}).copy()
    
    def set_exchange_ticker_override(self, exchange: str, ticker: str, min_size: int):
        """Set ticker-specific min_size override for an exchange."""
        exchange = exchange.lower()
        ticker = ticker.upper()
        with self._lock:
            if "exchanges" not in self._settings:
                self._settings["exchanges"] = {}
            if exchange not in self._settings["exchanges"]:
                self._settings["exchanges"][exchange] = DEFAULT_EXCHANGE_SETTINGS.copy()
            if "ticker_overrides" not in self._settings["exchanges"][exchange]:
                self._settings["exchanges"][exchange]["ticker_overrides"] = {}
            self._settings["exchanges"][exchange]["ticker_overrides"][ticker] = min_size
            self._save_settings()
    
    def remove_exchange_ticker_override(self, exchange: str, ticker: str):
        """Remove ticker-specific override for an exchange."""
        exchange = exchange.lower()
        ticker = ticker.upper()
        with self._lock:
            if "exchanges" in self._settings:
                if exchange in self._settings["exchanges"]:
                    if "ticker_overrides" in self._settings["exchanges"][exchange]:
                        if ticker in self._settings["exchanges"][exchange]["ticker_overrides"]:
                            del self._settings["exchanges"][exchange]["ticker_overrides"][ticker]
                            self._save_settings()
    
    def get_exchange_blacklist(self, exchange: str) -> List[str]:
        """Get blacklist for a specific exchange."""
        exchange = exchange.lower()
        with self._lock:
            exchanges = self._settings.get("exchanges", {})
            exch_settings = exchanges.get(exchange, {})
            return exch_settings.get("blacklist", []).copy()
    
    def add_exchange_blacklist(self, exchange: str, ticker: str):
        """Add ticker to exchange-specific blacklist."""
        exchange = exchange.lower()
        ticker = ticker.upper()
        with self._lock:
            if "exchanges" not in self._settings:
                self._settings["exchanges"] = {}
            if exchange not in self._settings["exchanges"]:
                self._settings["exchanges"][exchange] = DEFAULT_EXCHANGE_SETTINGS.copy()
            if "blacklist" not in self._settings["exchanges"][exchange]:
                self._settings["exchanges"][exchange]["blacklist"] = []
            if ticker not in self._settings["exchanges"][exchange]["blacklist"]:
                self._settings["exchanges"][exchange]["blacklist"].append(ticker)
                self._save_settings()
    
    def remove_exchange_blacklist(self, exchange: str, ticker: str):
        """Remove ticker from exchange-specific blacklist."""
        exchange = exchange.lower()
        ticker = ticker.upper()
        with self._lock:
            if "exchanges" in self._settings:
                if exchange in self._settings["exchanges"]:
                    if "blacklist" in self._settings["exchanges"][exchange]:
                        if ticker in self._settings["exchanges"][exchange]["blacklist"]:
                            self._settings["exchanges"][exchange]["blacklist"].remove(ticker)
                            self._save_settings()
    
    def clear_exchange_blacklist(self, exchange: str):
        """Clear the entire blacklist for an exchange."""
        exchange = exchange.lower()
        with self._lock:
            if "exchanges" in self._settings:
                if exchange in self._settings["exchanges"]:
                    self._settings["exchanges"][exchange]["blacklist"] = []
                    self._save_settings()

    
    # Hierarchical Resolution
    
    def resolve_min_size(self, exchange: str, base_symbol: str) -> int:
        """
        Resolve min_size with hierarchy:
        1. Exchange ticker override (highest priority)
        2. Global ticker override
        3. Exchange min_size (lowest priority)
        """
        base_symbol = base_symbol.upper()
        exchange = exchange.lower()
        
        with self._lock:
            exchanges = self._settings.get("exchanges", {})
            exch_settings = exchanges.get(exchange, {})
            
            # Check exchange ticker override (highest priority)
            ticker_overrides = exch_settings.get("ticker_overrides", {})
            if base_symbol in ticker_overrides:
                return ticker_overrides[base_symbol]
            
            # Check global ticker override
            global_overrides = self._settings.get("global_ticker_overrides", {})
            if base_symbol in global_overrides:
                return global_overrides[base_symbol]
            
            # Return exchange min_size (lowest priority)
            return exch_settings.get("min_size", DEFAULT_EXCHANGE_SETTINGS["min_size"])
    
    def is_blacklisted(self, exchange: str, base_symbol: str) -> bool:
        """
        Check if a ticker is blacklisted.
        Checks both global blacklist AND exchange-specific blacklist.
        """
        base_symbol = base_symbol.upper()
        exchange = exchange.lower()
        
        with self._lock:
            # Check global blacklist
            global_blacklist = self._settings.get("global_blacklist", [])
            if base_symbol in global_blacklist:
                return True
            
            # Check exchange blacklist
            exchanges = self._settings.get("exchanges", {})
            exch_settings = exchanges.get(exchange, {})
            exch_blacklist = exch_settings.get("blacklist", [])
            return base_symbol in exch_blacklist
    
    # Authorization
    
    def add_authorized_user(self, user_id: int):
        """Add a user to the authorized users list."""
        with self._lock:
            if "authorized_users" not in self._settings:
                self._settings["authorized_users"] = []
            if user_id not in self._settings["authorized_users"]:
                self._settings["authorized_users"].append(user_id)
                self._save_settings()
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if a user is authorized. If no users are set, allow everyone."""
        with self._lock:
            authorized = self._settings.get("authorized_users", [])
            if not authorized:  # Empty list = allow all
                return True
            return user_id in authorized
    
    # Settings Display
    
    def format_current_settings(self) -> str:
        """Return formatted string of all settings in Russian for the bot menu."""
        with self._lock:
            settings = self._settings.copy()
        
        # Get global settings
        alerts_status = "✅ Включены" if settings.get("alerts_enabled", False) else "❌ Выключены"
        global_dist = settings.get("global_distance_pct", DEFAULT_SETTINGS["global_distance_pct"])
        
        text = "📊 Текущие настройки\n\n"
        text += f"🔔 Алерты: {alerts_status}\n\n"
        
        # Global settings
        text += "🌐 Глобальные:\n"
        text += f"• Расстояние: {global_dist:.2f}%\n"
        
        # Global blacklist
        global_blacklist = settings.get("global_blacklist", [])
        text += f"• Чёрный список: "
        if global_blacklist:
            text += ", ".join(global_blacklist)
        else:
            text += "Пусто"
        text += "\n\n"
        
        # Exchange settings
        text += "📊 По биржам:\n"
        exchanges_settings = settings.get("exchanges", {})
        
        # Show all supported exchanges
        from config import SUPPORTED_EXCHANGES
        for exch_key, exch_info in SUPPORTED_EXCHANGES.items():
            exch_label = exch_info["label"]
            exch_settings_dict = exchanges_settings.get(exch_key, {})
            
            min_val = exch_settings_dict.get("min_size", DEFAULT_EXCHANGE_SETTINGS["min_size"])
            ticker_overrides = exch_settings_dict.get("ticker_overrides", {})
            blacklist = exch_settings_dict.get("blacklist", [])
            
            text += f"• {exch_label}:\n"
            text += f"  - Min: {min_val:,.0f} USDT\n"
            
            if ticker_overrides:
                text += f"  - Тикеры: "
                ticker_strs = [f"{t}={v:,.0f}" for t, v in ticker_overrides.items()]
                text += ", ".join(ticker_strs[:3])  # Show max 3
                if len(ticker_overrides) > 3:
                    text += f" (+{len(ticker_overrides) - 3})"
                text += "\n"
            
            if blacklist:
                text += f"  - ЧС: {', '.join(blacklist[:3])}"
                if len(blacklist) > 3:
                    text += f" (+{len(blacklist) - 3})"
                text += "\n"
        
        return text
    
    def format_settings(self) -> str:
        """Return formatted HTML string of all settings."""
        with self._lock:
            settings = self._settings.copy()
        
        html = "<b>📋 Current Settings</b>\n\n"
        
        # Global Settings
        html += "<b>Global Settings:</b>\n"
        html += f"• Alerts Enabled: {'✅' if settings.get('alerts_enabled') else '❌'}\n"
        html += f"• Chat ID: <code>{settings.get('chat_id')}</code>\n"
        html += f"• Distance: {settings.get('global_distance_pct', DEFAULT_SETTINGS['global_distance_pct']):.2f}%\n"
        html += f"• Scan Interval: {settings.get('scan_interval', DEFAULT_SETTINGS['scan_interval'])}s\n"
        html += f"• Orderbook Depth: {settings.get('orderbook_depth', DEFAULT_SETTINGS['orderbook_depth'])}\n"
        html += f"• Quote Currencies: {', '.join(settings.get('quote_currencies', []))}\n"
        html += "\n"
        
        # Global Blacklist
        blacklist = settings.get('global_blacklist', [])
        html += f"<b>Global Blacklist ({len(blacklist)}):</b>\n"
        if blacklist:
            html += f"• {', '.join(blacklist)}\n"
        else:
            html += "• None\n"
        html += "\n"
        
        # Global Ticker Overrides
        ticker_overrides = settings.get('global_ticker_overrides', {})
        html += f"<b>Global Ticker Overrides ({len(ticker_overrides)}):</b>\n"
        if ticker_overrides:
            for ticker, min_size in ticker_overrides.items():
                html += f"• {ticker}: min_size=${min_size:,.0f}\n"
        else:
            html += "• None\n"
        html += "\n"
        
        # Exchange Settings
        exchange_settings = settings.get('exchanges', {})
        html += f"<b>Exchange Settings ({len(exchange_settings)}):</b>\n"
        if exchange_settings:
            for exchange, exch_settings in exchange_settings.items():
                html += f"• <b>{exchange.upper()}</b>:\n"
                html += f"  - min_size: ${exch_settings.get('min_size', DEFAULT_EXCHANGE_SETTINGS['min_size']):,.0f}\n"
                html += f"  - min_lifetime: {exch_settings.get('min_lifetime', DEFAULT_EXCHANGE_SETTINGS['min_lifetime'])}s\n"
                
                # Exchange ticker overrides
                exch_ticker_overrides = exch_settings.get('ticker_overrides', {})
                if exch_ticker_overrides:
                    html += f"  - ticker_overrides: {len(exch_ticker_overrides)} tickers\n"
                
                # Exchange blacklist
                exch_blacklist = exch_settings.get('blacklist', [])
                if exch_blacklist:
                    html += f"  - blacklist: {len(exch_blacklist)} tickers\n"
        else:
            html += "• None\n"
        html += "\n"
        
        # Authorized Users
        authorized = settings.get('authorized_users', [])
        html += f"<b>Authorized Users ({len(authorized)}):</b>\n"
        if authorized:
            html += f"• {', '.join(map(str, authorized))}\n"
        else:
            html += "• All users (no restrictions)\n"
        
        return html
