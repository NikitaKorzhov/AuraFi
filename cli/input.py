import cli.colorss as colors
from logger import get_logger 
log=get_logger(__name__)

def base_input(prompt: str, data_type: type):
    """Базова функція для введення з перевіркою типу та умовою виходу через 'q'."""
    user_input = input(prompt).strip()
    
    if user_input.lower() == 'q':
        raise StopIteration("Вихід із процедури.")
    if not user_input:
        raise ValueError("Поле не може бути порожнім.")
        
    if data_type == str:
        return user_input
    elif data_type == int:
        return int(user_input)
    elif data_type == float:
        return float(user_input)
        
    raise TypeError(f"Unsupported data type: {data_type}")


def input_value(prompt: str, data_type: type, error_msg: str = "") :
    """Універсальна обгортка для безпечного введення одного значення будь-якого типу."""
    while True:
        try:
            return base_input(prompt, data_type)
        except StopIteration:
            return None
        except ValueError:
            msg = error_msg or f"Invalid input. Please enter a valid {data_type.__name__}."
            log.error(msg)
            print(colors.RED + msg + colors.RESET)


def input_transaction1(transaction_dict: dict):
    """Функція для введення транзакції за словником конфігурації."""
    transaction = {}
    for key, data_type in transaction_dict.items():
        prompt = f"{colors.BLUE}Input {key} (or 'q' to cancel): {colors.RESET}"
        error_msg = f"Invalid input for {key}. Please enter a valid {data_type.__name__}."
        
        value = input_value(prompt, data_type, error_msg)
        if value is None:
            return None  # Користувач натиснув 'q', скасовуємо всю транзакцію
        transaction[key] = value
        
    return transaction

def input_int(prompt: str):
    """Спеціалізована обгортка для введення цілого числа."""
    return input_value(prompt, int, "Invalid input. Please enter a valid integer.")

def input_index_to_delete(prompt: str, error_msg: str = ""):
    """Функція для введення індексу для видалення з перевіркою діапазону."""
    return input_value(prompt, int, error_msg)