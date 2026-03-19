"""
Binance Futures Testnet - CLI Layer
Handles user input validation, order placement, and output formatting.
"""

import argparse
import json
import logging
import os
import sys
from typing import Optional

from client import (
    BinanceFuturesClient,
    BinanceFuturesClientError,
    BinanceFuturesAPIError,
)

# ─────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────

LOG_FILE = "binance_futures.log"

def setup_logging(log_file: str = LOG_FILE, level: int = logging.DEBUG):
    """Configure structured logging to both file and stdout."""
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)  # Only warnings+ to console (cleaner UX)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Input Validation
# ─────────────────────────────────────────────

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP"}


def validate_inputs(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float] = None,
) -> None:
    """Validate all CLI inputs before sending to the API."""
    if not symbol or not symbol.isalnum():
        raise ValueError(f"Invalid symbol '{symbol}'. Must be alphanumeric (e.g. BTCUSDT).")

    if side.upper() not in VALID_SIDES:
        raise ValueError(f"Invalid side '{side}'. Choose from: {', '.join(VALID_SIDES)}.")

    if order_type.upper() not in VALID_ORDER_TYPES:
        raise ValueError(f"Invalid order type '{order_type}'. Choose from: {', '.join(VALID_ORDER_TYPES)}.")

    if quantity <= 0:
        raise ValueError(f"Quantity must be greater than 0. Got: {quantity}.")

    if order_type.upper() == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders. Use --price.")
        if price <= 0:
            raise ValueError(f"Price must be greater than 0. Got: {price}.")

    if order_type.upper() == "STOP":
        if price is None:
            raise ValueError("Price (limit price) is required for STOP orders. Use --price.")
        if stop_price is None:
            raise ValueError("Stop price (trigger price) is required for STOP orders. Use --stop-price.")
        if price <= 0:
            raise ValueError(f"Price must be greater than 0. Got: {price}.")
        if stop_price <= 0:
            raise ValueError(f"Stop price must be greater than 0. Got: {stop_price}.")

    if order_type.upper() == "MARKET" and price is not None:
        logger.warning("Price was provided for a MARKET order and will be ignored.")


# ─────────────────────────────────────────────
# Output Formatting
# ─────────────────────────────────────────────

SEPARATOR = "─" * 55

def print_order_summary(symbol, side, order_type, quantity, price, stop_price=None):
    """Print the order request before submission."""
    print(f"\n{SEPARATOR}")
    print("  📋  ORDER REQUEST SUMMARY")
    print(SEPARATOR)
    print(f"  Symbol     : {symbol.upper()}")
    print(f"  Side       : {side.upper()}")
    print(f"  Type       : {order_type.upper()}")
    print(f"  Quantity   : {quantity}")
    if order_type.upper() in ("LIMIT", "STOP"):
        print(f"  Limit Price: {price}")
    if order_type.upper() == "STOP":
        print(f"  Stop Price : {stop_price}  ← triggers the order")
    print(SEPARATOR)


def print_order_response(response: dict):
    """Print the API response in a clean, readable format."""
    print(f"\n{SEPARATOR}")
    print("  ✅  ORDER RESPONSE")
    print(SEPARATOR)
    print(f"  Order ID    : {response.get('orderId', 'N/A')}")
    print(f"  Symbol      : {response.get('symbol', 'N/A')}")
    print(f"  Status      : {response.get('status', 'N/A')}")
    print(f"  Side        : {response.get('side', 'N/A')}")
    print(f"  Type        : {response.get('type', 'N/A')}")
    print(f"  Orig Qty    : {response.get('origQty', 'N/A')}")
    print(f"  Executed Qty: {response.get('executedQty', 'N/A')}")
    avg_price = response.get("avgPrice") or response.get("price") or "N/A"
    print(f"  Avg Price   : {avg_price}")
    if response.get("stopPrice") and response.get("stopPrice") != "0":
        print(f"  Stop Price  : {response.get('stopPrice')}")
    print(f"  Time in Frc : {response.get('timeInForce', 'N/A')}")
    print(SEPARATOR)
    print("  🎉  Order placed successfully on Binance Futures Testnet!")
    print(f"{SEPARATOR}\n")


def print_failure(message: str):
    """Print a clear failure message."""
    print(f"\n{SEPARATOR}")
    print("  ❌  ORDER FAILED")
    print(SEPARATOR)
    print(f"  Reason: {message}")
    print(f"{SEPARATOR}\n")


# ─────────────────────────────────────────────
# CLI Argument Parsing
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="binance_futures_order",
        description="Place Market/Limit orders on Binance Futures Testnet (USDT-M)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  Market BUY:
    python3 main.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

  Limit SELL:
    python3 main.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 2000

  Stop-Limit SELL (trigger at 65000, execute at 64800):
    python3 main.py --symbol BTCUSDT --side SELL --type STOP --quantity 0.01 --stop-price 65000 --price 64800

  Using env vars for credentials:
    export BINANCE_API_KEY=your_key
    export BINANCE_API_SECRET=your_secret
        """,
    )
    parser.add_argument("--symbol",   required=True,  help="Trading pair symbol (e.g. BTCUSDT)")
    parser.add_argument("--side",     required=True,  choices=["BUY", "SELL"], help="Order side")
    parser.add_argument("--type",     required=True,  dest="order_type", choices=["MARKET", "LIMIT", "STOP"], help="Order type")
    parser.add_argument("--quantity", required=True,  type=float, help="Order quantity")
    parser.add_argument("--price",    required=False, type=float, default=None, help="Limit price (required for LIMIT and STOP orders)")
    parser.add_argument("--stop-price", required=False, type=float, default=None, dest="stop_price", help="Trigger price (required for STOP orders)")
    parser.add_argument("--api-key",  required=False, default=None, help="Binance API key (or set BINANCE_API_KEY env var)")
    parser.add_argument("--api-secret", required=False, default=None, help="Binance API secret (or set BINANCE_API_SECRET env var)")
    parser.add_argument("--log-file", required=False, default=LOG_FILE, help=f"Path to log file (default: {LOG_FILE})")
    return parser


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()

    # Setup logging first
    setup_logging(log_file=args.log_file)
    logger.info("=== Binance Futures Order CLI started ===")

    # Resolve credentials: CLI args > environment variables
    api_key = args.api_key or os.environ.get("BINANCE_API_KEY", "")
    api_secret = args.api_secret or os.environ.get("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        print_failure("API key and secret are required. Use --api-key / --api-secret or set BINANCE_API_KEY / BINANCE_API_SECRET env vars.")
        logger.error("Missing API credentials. Exiting.")
        sys.exit(1)

    # Validate inputs
    try:
        validate_inputs(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as e:
        print_failure(str(e))
        logger.error("Input validation failed: %s", e)
        sys.exit(1)

    # Print order summary
    print_order_summary(args.symbol, args.side, args.order_type, args.quantity, args.price, args.stop_price)

    # Initialize client and place order
    try:
        client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
        response = client.place_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
        print_order_response(response)
        logger.info("Order completed successfully. orderId=%s", response.get("orderId"))

    except BinanceFuturesAPIError as e:
        print_failure(f"Binance API error (code {e.code}): {e.message}")
        logger.error("BinanceFuturesAPIError: code=%s msg=%s", e.code, e.message)
        sys.exit(1)

    except BinanceFuturesClientError as e:
        print_failure(str(e))
        logger.error("BinanceFuturesClientError: %s", e)
        sys.exit(1)

    except Exception as e:
        print_failure(f"Unexpected error: {e}")
        logger.exception("Unexpected exception during order placement.")
        sys.exit(1)


if __name__ == "__main__":
    main()
