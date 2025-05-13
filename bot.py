import os
import logging
import argparse
import sys
from binance.client import Client
from binance import exceptions

class BasicBot:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        # Initialize Binance Futures Testnet client
        self.client = Client(api_key, api_secret, testnet=True)
        
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

    def place_order(self, symbol: str, side: str, order_type: str,
                    quantity: float, price: float = None):
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity
        }
        if order_type.upper() == 'LIMIT':
            if price is None:
                raise ValueError('Price must be provided for LIMIT orders')
            params.update({
                'price': price,
                'timeInForce': 'GTC'
            })
        try:
            self.logger.info(f"Placing {order_type} order: {params}")
            result = self.client.futures_create_order(**params)
            self.logger.info(f"Order response: {result}")
            return result
        except exceptions.BinanceAPIException as e:
            self.logger.error(f"API error: {e.status_code} - {e.message}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise


def parse_args():
    parser = argparse.ArgumentParser(
        description='Basic Binance Futures Testnet Trading Bot'
    )
    # Allow env vars or CLI
    parser.add_argument('--api-key',
                        default=os.getenv('BINANCE_API_KEY'),
                        help='Binance API key (or set BINANCE_API_KEY)')
    parser.add_argument('--api-secret',
                        default=os.getenv('BINANCE_API_SECRET'),
                        help='Binance API secret (or set BINANCE_API_SECRET)')
    parser.add_argument('--symbol', required=True,
                        help='Trading symbol, e.g., BTCUSDT')
    parser.add_argument('--side', required=True,
                        choices=['BUY', 'SELL'], help='Order side')
    parser.add_argument('--type', dest='order_type', required=True,
                        choices=['MARKET', 'LIMIT'], help='Order type')
    parser.add_argument('--quantity', type=float, required=True,
                        help='Order quantity')
    parser.add_argument('--price', type=float,
                        help='Price for LIMIT orders')
    parser.add_argument('--testnet', action='store_true',
                        default=True,
                        help='Use Binance Futures Testnet (default)')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    # Validate API credentials
    if not args.api_key or not args.api_secret:
        print('Error: API key and secret must be provided via flags or environment variables')
        sys.exit(1)

    bot = BasicBot(args.api_key, args.api_secret, testnet=args.testnet)
    try:
        order = bot.place_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price
        )
        print("Order placed successfully:")
        print(order)
    except Exception as e:
        print(f"Failed to place order: {e}")
        sys.exit(1)
