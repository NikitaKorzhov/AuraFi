import json
import os
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
                return []
    else:
      return []
#--------------------------------------------------------------


RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
ORANGE = "\033[38;2;255;165;0m"
BLUE = "\033[34m"
PURPLE = "\033[38;2;155;81;224m"
RESET = "\033[0m"


def transaction_cancel(cancelation_char:str):
    if cancelation_char == 'q':
        print(f"{ORANGE}Your action canceled{RESET}")
        return True
    else:
        return False


def get_input_with_cancel(prompt: str, data_type=str):
    """
    Function to cancel action by key 'q'
    and converting to required type (str by default).
    """
    while True:
        value = input(f"{BLUE}{prompt}{RESET}")
        if transaction_cancel(value):
            return None

        try:
            return data_type(value)
        except ValueError:
            if data_type is float:
                print(f"{RED}Error: Please enter a valid number (e.g., 100.50).{RESET}")
            elif data_type is int:
                print(f"{RED}Error: Please enter a valid whole number (e.g., 10).{RESET}")
            else:
                print(f"{RED}Error: Invalid input format.{RESET}")

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
        transactions.append(transaction)
        print(f"{GREEN}{transaction_type} added successfully!{RESET}\n{YELLOW}{transaction}{RESET}\n\nSee transaction list below")
        show_all_transactions()
        write_transactions(transactions)


def show_all_transactions():
    if not transactions:
        print(f"{ORANGE}No transactions found.{RESET}")
    else:
        for i, t in enumerate(transactions):
            print(f"{PURPLE}[{i}] {t}{RESET}")

def delete_transaction():
    if not transactions:
        print(f"{ORANGE}No transactions to delete.{RESET}")
    else:
        for i, t in enumerate(transactions):
            print(f"{PURPLE}[{i}] {t}{RESET}")

        idx = get_input_with_cancel("Enter index to delete (or 'q'): ", int)

        if idx is not None:
            if 0 <= idx < len(transactions):
                removed = transactions.pop(idx)
                print(f"{ORANGE}Transaction {removed} deleted.{RESET}\n\nSee transaction list below")
                show_all_transactions()
                write_transactions(transactions)
            else:
                print(f"{RED}Error: Index out of range.{RESET}")


command_dict={1:"input income", 2:"input expense",3:"show all transactions",4:"delete transaction",5:"exit"}



#While loop executing program
transactions=read_transactions()
while True:
    print(f"\n{ORANGE}Command list: {command_dict}{RESET}")
    command = input(f"{BLUE}Input your command number:{RESET} ").strip()

    if command == "5":
        print("Thank you for using this program")
        break
    elif command == "1":
        add_transaction("income")
    elif command == "2":
        add_transaction("expense")
    elif command == "3":
        show_all_transactions()
    elif command == "4":
        delete_transaction()
    else:
        print(f"{RED}Unknown command. Please try again.{RESET}")