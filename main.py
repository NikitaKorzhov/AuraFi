import json
import os
from datetime import datetime

from tracker import ExpenseTracker
from Transaction import Transaction




#Logger
loggerFilePath="log.txt"
def log(message):
    log_record = f"{datetime.utcnow().isoformat()}Z - {message}\n"
    try:
        with open(loggerFilePath, "a", encoding="utf-8") as file:
            file.write(log_record)
    except:
        pass
#File storage
file_path = "transactions.json" #File name to save transactions list
def write_transactions(transactions:list):
    """Function to write entire transactions into file

    :param transactions: list of transactions
    :type transactions: list"""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(transactions, file, indent=4, ensure_ascii=False)

def read_transactions():
    """Function to read entire transactions from file into list"""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                log("Error while reading transactions file")
                return []
    else:
      return []
#--------------------------------------------------------------

#Color string before output
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
ORANGE = "\033[38;2;255;165;0m"
BLUE = "\033[34m"
PURPLE = "\033[38;2;155;81;224m"
RESET = "\033[0m"

def color_string(color,text):
    """Function returns colored string with given color

    :param color: color
    :type color: str
    :param text: text
    :type text: str"""
    return f"{color}{text}{RESET}"
#------------------------------------------------------------------------

def transaction_cancel(cancelation_char:str):
    if cancelation_char == 'q':
        print(f"{color_string(ORANGE,'Your action canceled')}")
        return True
    else:
        return False


def get_input_with_cancel(prompt: str, data_type=str):
    """
    Function to cancel action by key 'q'
    and converting to required type (str by default).
    """
    while True:
        value = input(f"{color_string(BLUE,prompt)}")
        if transaction_cancel(value):
            return None

        try:
            return data_type(value)
        except ValueError:
            if data_type is float:
                log("Invalid amount")
                print(f"{color_string(RED,'Error: Please enter a valid number (e.g., 100.50).')}")
            elif data_type is int:
                log("Invalid amount")
                print(f"{color_string(RED,'Error: Please enter a valid whole number (e.g., 10).')}")
            else:
                log('Invalid input for transaction_cancel')
                print(f"{color_string(RED,'Error: Invalid input format.')}")

def input_transaction(transaction_type=""):
    fields = [
        ("amount", float),
        ("category", str)
    ]

    transaction = {}

    if transaction_type in ["income", "expense"]:
        transaction["type"] = transaction_type
    else:
        fields.insert(1, ("type", str))

    for key, data_type in fields:
        prompt = f"Input {key} (or 'q' to cancel): "

        value = get_input_with_cancel(prompt, data_type)
        if value is None:
            return None

        transaction[key] = value

    return transaction


#Transaction list and functions to operate with it from console
transactions=[]

def add_transaction(transaction_type:str):
    transaction = input_transaction(transaction_type)
    if transaction is not None:
        transactions.addTransaction(Transaction.from_data(transaction))
        print(f"{color_string(GREEN,f'{transaction_type} added successfully!')}\n{color_string(YELLOW,f'{transaction}')}\n\nSee transaction list below")
        show_all_transactions()
        write_transactions(transactions.to_list())


def show_all_transactions():
    if not transactions:
        print(f"{color_string(ORANGE,'No transactions found.')}")
    else:
         print(f"{color_string(PURPLE,transactions)}")

def show_all_transactions_with_info():
     if not transactions:
        print(f"{color_string(ORANGE,'No transactions found.')}")
     else:
        transactions_Info=color_string(YELLOW,f"Income sum: {transactions.calc_income()}, Expense sum: {transactions.calc_expense()}, total: {transactions.budget_count()}")
        print(f"{color_string(PURPLE,transactions)},\n{transactions_Info}")

def delete_transaction():
    if not transactions:
        print(f"{color_string(ORANGE,'No transactions to delete.')}")
    else:
        show_all_transactions()

        idx = get_input_with_cancel("Enter index to delete (or 'q'): ", int)

        if idx is not None:
            if 0 < idx <= len(transactions.transactions):
                removed = transactions.remove_transaction(idx)
                print(f"{color_string(ORANGE,f'Transaction {removed} deleted.')}\n\nSee transaction list below")
                show_all_transactions()
                write_transactions(transactions.to_list())
            else:
                print(f"{color_string(RED,'Error: Index out of range.')}")


command_dict={1:"input income", 2:"input expense",3:"show all transactions",4:"delete transaction",5:"exit"}



#While loop executing program
transactions=ExpenseTracker.from_data(read_transactions())
while True:
    print(f"\n{color_string(ORANGE,f'Command list: {command_dict}')}")
    command = input(f"{color_string(BLUE,'Input your command number:')} ").strip()

    if command == "5":
        log("Program ended")
        print("Thank you for using this program")
        break
    elif command == "1":
        add_transaction("income")
    elif command == "2":
        add_transaction("expense")
    elif command == "3":
        show_all_transactions_with_info()
    elif command == "4":
        delete_transaction()
    else:
        log(f"Command with number {command} not exists")
        print(f"{color_string(RED,'Unknown command. Please try again.')}")