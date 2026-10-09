import cli.colorss as colors
from logger import get_logger 
log=get_logger(__name__)

def base_input(prompt: str, data_type: type):
    """Base function for input with type validation and 'q' exit condition."""
    user_input = input(prompt).strip()
    
    if user_input.lower() == 'q':
        raise StopIteration("Exiting procedure.")
    if not user_input:
        raise ValueError("Field cannot be empty.")
        
    if data_type == str:
        return user_input
    elif data_type == int:
        return int(user_input)
    elif data_type == float:
        return float(user_input)
        
    raise TypeError(f"Unsupported data type: {data_type}")


def input_value(prompt: str, data_type: type, error_msg: str = "") :
    """Universal wrapper for safe input of a single value of any type."""
    while True:
        try:
            return base_input(prompt, data_type)
        except StopIteration:
            return None
        except ValueError:
            msg = error_msg or f"Invalid input. Please enter a valid {data_type.__name__}."
            log.error(msg)
            print(colors.RED + msg + colors.RESET)


def input_category(categories: dict, prompt_label: str = "category"):
    """Lets the user pick a category by number from a predefined {category: budget} dict,
    instead of typing it freely."""
    options = list(categories.keys())
    print(f"{colors.BLUE}Select {prompt_label} (or 'q' to cancel):{colors.RESET}")
    for i, cat in enumerate(options, start=1):
        print(f"{colors.BLUE}{i}. {cat} (budget: {categories[cat]}){colors.RESET}")

    while True:
        choice = input_value(
            f"{colors.BLUE}Enter number (or 'q' to cancel): {colors.RESET}",
            int,
            "Invalid input. Please enter a valid number.",
        )
        if choice is None:
            return None  # User pressed 'q', cancel

        if 1 <= choice <= len(options):
            return options[choice - 1]

        msg = f"Invalid choice. Please enter a number between 1 and {len(options)}."
        log.error(msg)
        print(colors.RED + msg + colors.RESET)


def input_transaction1(transaction_dict: dict):
    """Function to input a transaction using a configuration dictionary.

    Each value in `transaction_dict` is either a plain type (str/int/float) for
    free-form input, or a {category: budget} dict to let the user pick a category
    from a numbered list instead of typing it.
    """
    transaction = {}
    for key, spec in transaction_dict.items():
        if isinstance(spec, dict):
            value = input_category(spec, prompt_label=key)
        else:
            prompt = f"{colors.BLUE}Input {key} (or 'q' to cancel): {colors.RESET}"
            error_msg = f"Invalid input for {key}. Please enter a valid {spec.__name__}."
            value = input_value(prompt, spec, error_msg)

        if value is None:
            return None  # User pressed 'q', cancel the entire transaction
        transaction[key] = value

    return transaction

def input_int(prompt: str):
    """Specialized wrapper for integer input."""
    return input_value(prompt, int, "Invalid input. Please enter a valid integer.")

def input_index_to_delete(prompt: str, error_msg: str = ""):
    """Function to input an index for deletion with range validation."""
    return input_value(prompt, int, error_msg)