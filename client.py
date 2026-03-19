"""
Binance Futures Testnet - API Client Layer
Handles all direct communication with the Binance Futures Testnet REST API.
"""

import hashlib
import hmac
import logging
import time
from typing import Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceFuturesClientError(Exception):
    """Raised for client-side errors (invalid input, config issues)."""
    pass


class BinanceFuturesAPIError(Exception):
    """Raised when the Binance API returns an error response."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"API Error {code}: {message}")


class BinanceFuturesClient:
    """
    Low-level client for Binance USDT-M Futures Testnet.
    Handles authentication, request signing, and HTTP communication.
    """

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10):
        if not api_key or not api_secret:
            raise BinanceFuturesClientError("API key and secret must not be empty.")
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        logger.info("BinanceFuturesClient initialized (testnet).")

    def _sign(self, params: dict) -> str:
        """Generate HMAC-SHA256 signature for the given params."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _request(self, method: str, endpoint: str, params: dict) -> dict:
        """
        Make a signed HTTP request to the Binance Futures Testnet.
        Adds timestamp and signature automatically.
        """
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._sign(params)

        url = f"{TESTNET_BASE_URL}{endpoint}"
        logger.debug("REQUEST %s %s | params: %s", method.upper(), url, {k: v for k, v in params.items() if k != "signature"})

        try:
            if method.upper() == "POST":
                response = self.session.post(url, data=params, timeout=self.timeout)
            elif method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=self.timeout)
            else:
                raise BinanceFuturesClientError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.ConnectionError as e:
            logger.error("Network connection error: %s", e)
            raise BinanceFuturesClientError(f"Network connection failed: {e}") from e
        except requests.exceptions.Timeout as e:
            logger.error("Request timed out: %s", e)
            raise BinanceFuturesClientError(f"Request timed out after {self.timeout}s.") from e
        except requests.exceptions.RequestException as e:
            logger.error("Unexpected request error: %s", e)
            raise BinanceFuturesClientError(f"Unexpected network error: {e}") from e

        logger.debug("RESPONSE %s | body: %s", response.status_code, response.text[:500])

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response received: %s", response.text[:200])
            raise BinanceFuturesClientError(f"Invalid JSON response (status {response.status_code}).")

        if isinstance(data, dict) and "code" in data and data["code"] != 200 and data["code"] < 0:
            logger.error("API error response: code=%s msg=%s", data.get("code"), data.get("msg"))
            raise BinanceFuturesAPIError(code=data["code"], message=data.get("msg", "Unknown error"))

        return data

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Place a MARKET, LIMIT, or STOP_LIMIT order on Binance Futures Testnet.

        Args:
            symbol:        Trading pair, e.g. 'BTCUSDT'
            side:          'BUY' or 'SELL'
            order_type:    'MARKET', 'LIMIT', or 'STOP'
            quantity:      Order quantity
            price:         Required for LIMIT and STOP orders (the limit price)
            stop_price:    Required for STOP orders (the trigger price)
            time_in_force: 'GTC', 'IOC', or 'FOK' (LIMIT/STOP only)

        Returns:
            dict with order response from Binance API
        """
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
        }

        if order_type.upper() == "LIMIT":
            if price is None:
                raise BinanceFuturesClientError("Price is required for LIMIT orders.")
            params["price"] = price
            params["timeInForce"] = time_in_force

        elif order_type.upper() == "STOP":
            if price is None:
                raise BinanceFuturesClientError("Price (limit price) is required for STOP orders.")
            if stop_price is None:
                raise BinanceFuturesClientError("Stop price (trigger price) is required for STOP orders.")
            if stop_price <= 0 or price <= 0:
                raise BinanceFuturesClientError("Both price and stop_price must be greater than 0.")
            params["price"] = price
            params["stopPrice"] = stop_price
            params["timeInForce"] = time_in_force

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s stop_price=%s",
            side.upper(), order_type.upper(), symbol.upper(), quantity,
            price or "MARKET", stop_price or "N/A"
        )

        result = self._request("POST", "/fapi/v1/order", params)
        logger.info("Order placed successfully | orderId=%s status=%s", result.get("orderId"), result.get("status"))
        return result
