import os
import logging
import argparse
import sys
import time
import numpy as np
from decimal import Decimal, ROUND_DOWN
from binance.client import Client
from binance import exceptions

class BasicBot:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        # Initialize Binance Futures Testnet client
        self.client = Client(api_key, api_secret, testnet=testnet)
        # Fetch exchange info for precision rules
        info = self.client.futures_exchange_info()
        self.filters = {f['symbol']: f['filters'] for f in info['symbols']}

        # Configure logger (file + console)
        self.logger = logging.getLogger('BasicBot')
        self.logger.setLevel(logging.INFO)
        fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh = logging.FileHandler('bot.log')
        fh.setFormatter(fmt)
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        self.logger.info('Initialized BasicBot')

    def _adjust_precision(self, symbol: str, value: float, filter_type: str) -> float:
        # filter_type: 'LOT_SIZE' for quantity, 'PRICE_FILTER' for price
        sym_filters = self.filters.get(symbol.upper(), [])
        for f in sym_filters:
            if f['filterType'] == filter_type:
                step = Decimal(f['stepSize'] if filter_type == 'LOT_SIZE' else f['tickSize'])
                val = Decimal(value)
                # round down to allowed precision
                quantized = (val // step) * step
                return float(quantized)
        return value

    def place_order(self, symbol: str, side: str, order_type: str,
                    quantity: float, price: float = None, stop_price: float = None):
        """
        Place various orders:
        - MARKET, LIMIT, STOP_LIMIT on Futures
        """
        s = symbol.upper()
        qty = self._adjust_precision(s, quantity, 'LOT_SIZE')
        # MARKET
        if order_type == 'MARKET':
            params = {
                'symbol': s,
                'side': side.upper(),
                'type': 'MARKET',
                'quantity': qty
            }
            endpoint = self.client.futures_create_order
        # LIMIT
        elif order_type == 'LIMIT':
            if price is None:
                raise ValueError('Price required for LIMIT orders')
            pr = self._adjust_precision(s, price, 'PRICE_FILTER')
            params = {
                'symbol': s,
                'side': side.upper(),
                'type': 'LIMIT',
                'price': pr,
                'quantity': qty,
                'timeInForce': 'GTC'
            }
            endpoint = self.client.futures_create_order
        # STOP_LIMIT
        elif order_type == 'STOP_LIMIT':
            if price is None or stop_price is None:
                raise ValueError('Both stop_price and price required for STOP_LIMIT')
            pr = self._adjust_precision(s, price, 'PRICE_FILTER')
            sp = self._adjust_precision(s, stop_price, 'PRICE_FILTER')
            params = {
                'symbol': s,
                'side': side.upper(),
                'type': 'STOP',
                'price': pr,
                'stopPrice': sp,
                'quantity': qty,
                'timeInForce': 'GTC'
            }
            endpoint = self.client.futures_create_order
        else:
            raise ValueError(f'Unsupported order type: {order_type}')

        try:
            self.logger.info(f"Placing {order_type} order with params: {params}")
            result = endpoint(**params)
            self.logger.info(f"Order response: {result}")
            return result
        except exceptions.BinanceAPIException as e:
            self.logger.error(f"API error: {e.status_code} - {e.message}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    def execute_twap(self, symbol: str, side: str, total_qty: float,
                     duration: int, intervals: int):
        slice_qty = total_qty / intervals
        delay = duration / intervals
        results = []
        self.logger.info(f"Starting TWAP: {intervals} slices, {slice_qty} qty each, every {delay}s")
        for i in range(intervals):
            res = self.place_order(symbol, side, 'MARKET', slice_qty)
            results.append(res)
            if i < intervals - 1:
                time.sleep(delay)
        return results

    def execute_grid(self, symbol: str, side: str, total_qty: float,
                     lower_price: float, upper_price: float, grids: int):
        prices = np.linspace(lower_price, upper_price, grids)
        qty_per_order = total_qty / grids
        results = []
        self.logger.info(f"Starting Grid: {grids} levels from {lower_price} to {upper_price}, {qty_per_order} each")
        for price in prices:
            res = self.place_order(symbol, side, 'LIMIT', qty_per_order, price=price)
            results.append(res)
        return results


def parse_args():
    parser = argparse.ArgumentParser(
        description='Advanced Binance Bot: Market, Limit, Stop-Limit, TWAP, Grid with precision handling'
    )
    parser.add_argument('--api-key', default=os.getenv('BINANCE_API_KEY'),
                        help='API key (or set BINANCE_API_KEY)')
    parser.add_argument('--api-secret', default=os.getenv('BINANCE_API_SECRET'),
                        help='API secret (or set BINANCE_API_SECRET)')
    parser.add_argument('--symbol', required=True,
                        help='Trading symbol, e.g., BTCUSDT')
    parser.add_argument('--side', required=True, choices=['BUY', 'SELL'],
                        help='Order side')
    parser.add_argument('--type', dest='order_type', required=True,
                        choices=['MARKET', 'LIMIT', 'STOP_LIMIT', 'TWAP', 'GRID'],
                        help='Order type')
    parser.add_argument('--quantity', type=float, required=True,
                        help='Order quantity or total quantity for TWAP/Grid')
    parser.add_argument('--price', type=float,
                        help='Price for LIMIT or STOP_LIMIT orders')
    parser.add_argument('--stop-price', type=float,
                        help='Stop price for STOP_LIMIT orders')
    parser.add_argument('--duration', type=int,
                        help='Total duration in seconds for TWAP')
    parser.add_argument('--intervals', type=int,
                        help='Number of slices for TWAP')
    parser.add_argument('--lower-price', type=float,
                        help='Lower bound price for Grid')
    parser.add_argument('--upper-price', type=float,
                        help='Upper bound price for Grid')
    parser.add_argument('--grids', type=int,
                        help='Number of grid levels')
    parser.add_argument('--testnet', action='store_true', default=True,
                        help='Use Binance Futures Testnet')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if not args.api_key or not args.api_secret:
        print('Error: API key/secret required via flags or env vars')
        sys.exit(1)

    bot = BasicBot(args.api_key, args.api_secret, testnet=args.testnet)
    try:
        if args.order_type in ['MARKET', 'LIMIT', 'STOP_LIMIT']:
            result = bot.place_order(
                symbol=args.symbol,
                side=args.side,
                order_type=args.order_type,
                quantity=args.quantity,
                price=args.price,
                stop_price=args.stop_price
            )
        elif args.order_type == 'TWAP':
            if args.duration is None or args.intervals is None:
                raise ValueError('TWAP requires --duration and --intervals')
            result = bot.execute_twap(
                symbol=args.symbol,
                side=args.side,
                total_qty=args.quantity,
                duration=args.duration,
                intervals=args.intervals
            )
        elif args.order_type == 'GRID':
            if args.lower_price is None or args.upper_price is None or args.grids is None:
                raise ValueError('GRID requires --lower-price, --upper-price, and --grids')
            result = bot.execute_grid(
                symbol=args.symbol,
                side=args.side,
                total_qty=args.quantity,
                lower_price=args.lower_price,
                upper_price=args.upper_price,
                grids=args.grids
            )
        print("Order response:")
        print(result)
    except Exception as e:
        print(f"Failed to place order: {e}")
        sys.exit(1)
