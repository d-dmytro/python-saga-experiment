from random import choice
from string import ascii_lowercase
from colorama import Fore

class ShutdownException(Exception):
    pass

def generate_id():
    return "".join(choice(ascii_lowercase) for i in range(4))

def get_random_color():
    return choice(list(vars(Fore)))

def colored(text: str, color: str):
    return f"{getattr(Fore, color)}{text}"
