from coinbase.wallet.client import Client
key = 'YOUR_COINBASE_API_KEY'
scrt = 'YOUR_COINBASE_API_SECRET'

print("1. Connecting to Coinbase...")
client = Client(key, scrt)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Connect to coinbase and pull down all account info
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
list_of_accounts = client.get_accounts()['data']

my_coinbase = {'current_value': 0,
               'current_unrealized_gain': 0,
               'current_performance': 0,
               'currencies': []}

print("2. Gathering Coinbase account information...")
# Iterate over each account that isn't a USD account
for account in list_of_accounts:
    try:
        if (account['currency'] == 'USD')\
        | (float(account['balance']['amount']) == 0):
            pass
        else:
            # Get current amount of currency and your totals
            currency_name = account['balance']['currency']
            current_quantity = float(account['balance']['amount'])
            current_total = float(account['native_balance']['amount'])
            current_price = float(client.get_spot_price(currency_pair
                                                  = currency_name +
                                                  '-USD')['amount'])

            currency_dict = {
                'symbol': currency_name,
                'quantity': current_quantity,
                'current_price': current_price,
                'current_total': current_total,
                'average_price': 0,
                'original_worth': 0,
                'sell_original_worth': 0,
                'realized_gain_loss': 0,
                'unrealized_gain_loss': 0,
                'current_performance': 0,
                'realized_gain_performance': 0,
                'all_time_invested': 0,
                'all_time_costs': 0,
                'all_time_fees': 0,
                'orders': []
            }

            my_coinbase['currencies'].append(currency_dict)

            # Get list of transactions
            for transaction in account.get_transactions()['data']:
                # For buys
                if transaction['type'] == 'buy':
                    # Get currency name, currency amount, date transacted
                    symbol = transaction['amount']['currency']
                    amount = float(transaction['amount']['amount'])
                    datetime = transaction['created_at']

                    # Get buy price and fee
                    buy = account.get_buy(transaction['buy']['id'])
                    buy_cost = float(buy['total']['amount'])
                    buy_subtotal = float(buy['subtotal']['amount'])
                    total_fee = 0
                    for fee in buy['fees']:
                        total_fee += float(fee['amount']['amount'])

                    order_dict = {
                        'type': 'buy',
                        'datetime': datetime,
                        'symbol': symbol,
                        'amount': amount,
                        'cost': buy_cost,
                        'invested': buy_subtotal,
                        'spot_price': buy_subtotal/amount,
                        'total_fee': total_fee
                    }

                    currency_dict['all_time_invested'] += buy_subtotal
                    currency_dict['all_time_costs'] += buy_cost
                    currency_dict['all_time_fees'] += total_fee
                    currency_dict['orders'].append(order_dict)

                elif transaction['type'] == 'sell':
                    # Get currency name, currency amount, date transacted
                    symbol = transaction['amount']['currency']
                    amount = float(transaction['amount']['amount'])
                    datetime = transaction['created_at']

                    # Get buy price and fee
                    sell = account.get_sell(transaction['sell']['id'])
                    sell_earned = float(sell['total']['amount'])
                    sell_total = float(sell['subtotal']['amount'])
                    total_fee = 0
                    for fee in sell['fees']:
                        total_fee += float(fee['amount']['amount'])
                    order_dict = {
                        'type': 'sell',
                        'datetime': datetime,
                        'symbol': symbol,
                        'amount': amount,
                        'earned': sell_earned,
                        'sell_total': sell_total,
                        'spot_price': -sell_total/amount,
                        'total_fee': total_fee
                    }

                    currency_dict['all_time_fees'] += total_fee
                    currency_dict['orders'].append(order_dict)

            # sort all orders by date
            currency_dict['orders'] = sorted(currency_dict['orders'],
                                             key = lambda k:k['datetime'],
                                             reverse=False)

            # Store running quantity of currency
            total_currency_quantity = 0
            # Store weighted average price of currency
            weighted_currency_price = 0

            # Store total invested
            total_invested = 0

            for order in currency_dict['orders']:
                if order['type'] == 'buy':
                    # calculate current quantity and weighted avg price of each
                    num = ((total_currency_quantity * weighted_currency_price)
                           + (order['amount'] * order['spot_price']))
                    den = (total_currency_quantity + order['amount'])
                    weighted_currency_price = float(num/den)
                    total_currency_quantity += order['amount']

                    order['original_worth'] = 'N/A'

                elif order['type'] == 'sell':
                    # calculate realized gain/loss on sale
                    # use average buy price to calculate sale return
                    investment_value = ((-order['amount'])
                                        *weighted_currency_price)

                    # save original worth of the sale quantity
                    # i.e. amount * avg buy price up until now
                    order['original_worth'] = (-(order['amount']
                                                 *weighted_currency_price))
                    currency_dict['sell_original_worth'] += order['original_worth']
                    currency_dict['realized_gain_loss'] += ((order['sell_total'])
                                                            - (investment_value))

                    # subtract quantity sold from existing amount
                    total_currency_quantity += order['amount']
                    if total_currency_quantity == 0:
                        weighted_currency_price = 0
                    else:
                        pass

                else:
                    pass
            currency_dict['average_price'] = weighted_currency_price
            currency_dict['original_worth'] = (currency_dict['quantity']
                                               *weighted_currency_price)
            currency_dict['unrealized_gain_loss'] = (currency_dict['current_total']
                                                     - currency_dict['original_worth'])
            currency_dict['current_performance'] = (currency_dict['unrealized_gain_loss']
                                                    /currency_dict['original_worth'])
            # Calculate realized gain performance if something has been sold
            if currency_dict['realized_gain_loss'] != 0:
                currency_dict['realized_gain_performance'] = (currency_dict['realized_gain_loss']
                                                              /currency_dict['sell_original_worth'])

            # Add in currency totals to full account dictionary
            my_coinbase['current_value'] += currency_dict['current_total']
            my_coinbase['current_unrealized_gain'] += currency_dict['unrealized_gain_loss']

    except:
        pass

my_coinbase['current_performance'] = (my_coinbase['current_unrealized_gain']
                                      /(my_coinbase['current_value']
                                        -my_coinbase['current_unrealized_gain'])
                                     )
my_coinbase['currencies'] = sorted(my_coinbase['currencies'],
                                   key = lambda k:float(k['current_total']),
                                   reverse=True)
print("Coinbase information gathered.\n")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Connect to google spreadsheets and fill info
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
print("3. Connecting to Google Sheets...")
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = (ServiceAccountCredentials
               .from_json_keyfile_name("YOUR_GOOGLE_CREDENTIALS_FILENAME.json",
                                       scope)
              )

gc = gspread.authorize(credentials)
spreadsheet = gc.open("Coinbase Portfolio")

# open portfolio overview worksheet from file
wks1 = spreadsheet.get_worksheet(0)

# ADD PORTFOLIO OVERVIEW DETAILS INTO SPREADSHEET
currency_count = len(my_coinbase['currencies'])

currency_cell_list = wks1.range('B3:G' + str(2 + currency_count))
# Iterate over each currency
for idx, currency in enumerate(my_coinbase['currencies']):
    cell = 0 + (idx*6)
    wks_row_num = str(3 + idx)
    # Symbols
    currency_cell_list[cell].value = currency['symbol']
    cell += 1
    # Current Price
    currency_cell_list[cell].value = currency['current_price']
    cell += 1
    # Current Quantity
    currency_cell_list[cell].value = currency['quantity']
    cell += 1
    # Current Total
    currency_cell_list[cell].value = currency['current_total']
    cell += 1
    # Unrealized Gain/Loss
    currency_cell_list[cell].value = currency['unrealized_gain_loss']
    cell += 1
    # Portfolio performance
    currency_cell_list[cell].value = currency['current_performance']
    cell += 1

print("4. Writing information to sheet 1...")
# Update spreadsheet with currency overview
wks1.update_cells(currency_cell_list)

# Include Totals
# final_row = currency_count + 3
totals_cell_list = wks1.range('I3:K3')
# Set cell values with totals
# totals_cell_list[0].value = 'Total'
totals_cell_list[0].value = my_coinbase['current_value']
totals_cell_list[1].value = my_coinbase['current_unrealized_gain']
totals_cell_list[2].value = my_coinbase['current_performance']

# Update spreadsheet with totals
wks1.update_cells(totals_cell_list)


# open currency details worksheet from file
wks2 = spreadsheet.get_worksheet(1)

# ADD CURRENCY OVERVIEW DETAILS INTO SPREADSHEET
currency_count = len(my_coinbase['currencies'])
currency_cell_list = wks2.range('B3:M' + str(2 + currency_count))
# Iterate over each currency
for idx, currency in enumerate(my_coinbase['currencies']):
    cell = 0 + (idx*12)
    wks_row_num = str(3 + idx)
    # Symbols
    currency_cell_list[cell].value = currency['symbol']
    cell += 1
    # Current Price
    currency_cell_list[cell].value = currency['current_price']
    cell += 1
    # Current Quantity
    currency_cell_list[cell].value = currency['quantity']
    cell += 1
    # Average Buy Price
    currency_cell_list[cell].value = currency['average_price']
    cell += 1
    # Original worth of current quantity
    currency_cell_list[cell].value = currency['original_worth']
    cell += 1
    # Current Total
    currency_cell_list[cell].value = currency['current_total']
    cell += 1
    # Unrealized Gain/Loss
    currency_cell_list[cell].value = currency['unrealized_gain_loss']
    cell += 1
    # Portfolio performance
    currency_cell_list[cell].value = currency['current_performance']
    cell += 1
    # Realized Gain
    currency_cell_list[cell].value = currency['realized_gain_loss']
    cell += 1
    # Historical Cost
    currency_cell_list[cell].value = currency['all_time_costs']
    cell += 1
    # Historical Fees
    currency_cell_list[cell].value = currency['all_time_fees']
    cell += 1
    # Historical Investment
    currency_cell_list[cell].value = currency['all_time_invested']

print("5. Writing information to sheet 2...")
# Update spreadsheet with currency overview
wks2.update_cells(currency_cell_list)

# ADD ORDERS INTO SPREADSHEET
# Get all orders sorted by date
all_orders = []

for currency in my_coinbase['currencies']:
    all_orders.extend(currency['orders'])

all_orders = sorted(all_orders, key = lambda k:k['datetime'])

# open orders worksheet from file
wks3 = spreadsheet.get_worksheet(2)

order_count = len(all_orders)
order_cell_list = wks3.range('B3:K' + str(2 + order_count))
for idx, order in enumerate(all_orders):
    cell = 0 + (idx*10)
    wks_row_num = str(3 + idx)
    # Date
    order_cell_list[cell].value = order['datetime'].split('T')[0]
    cell += 1
    # Order Type
    order_cell_list[cell].value = order['type']
    cell += 1
    # Symbol
    order_cell_list[cell].value = order['symbol']
    cell += 1
    # Price
    order_cell_list[cell].value = order['spot_price']
    cell += 1
    # Amount
    order_cell_list[cell].value = order['amount']
    cell += 1
    # Cost
    if order['type'] == 'buy':
        order_cell_list[cell].value = order['cost']
    else:
        order_cell_list[cell].value = order['sell_total']
    cell += 1
    # Fee
    order_cell_list[cell].value = order['total_fee']
    cell += 1
    # Price & for sales: original worth, net profit
    if order['type'] == 'buy':
        order_cell_list[cell].value = order['invested']
        cell += 1
        order_cell_list[cell].value = 'N/A'
        cell += 1
        order_cell_list[cell].value = 'N/A'
        cell += 1
    else:
        order_cell_list[cell].value = order['earned']
        cell += 1
        # Original Worth
        order_cell_list[cell].value = order['original_worth']
        cell += 1
        # Net Profit
        order_cell_list[cell].value = (order['earned']
                                       - order['original_worth'])

print("6. Writing information to sheet 3...")
# Update spreadsheet with orders
wks3.update_cells(order_cell_list)

spreadsheet_url = "https://docs.google.com/spreadsheets/d/%s" % spreadsheet.id

print("Process completed.\n\nTo see results please visit:", spreadsheet_url)
