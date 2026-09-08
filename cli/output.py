from __future__ import annotations
import cli.colorss as c


class ColorText:
    """Class for printing colored strings to the console"""

    def __init__(self, color: str = "", text: str = ""):
        if not color:
            self.text = text
        else:
            self.text = f"{color}{text}{c.RESET}"

    def __str__(self):
        return self.text
    
    def __repr__(self):
        return self.text

    def print(self):
        """Function prints the text to the console"""
        print(self.text)


class ColorAction:
    """Descriptor to support color methods both on class and instance level"""
    def __init__(self, color: str):
        self.color = color

    def __get__(self, instance, owner):
        if instance is None:
            return lambda text: owner()._append_text(ColorText(self.color, text))
        else:
            return lambda text: instance._append_text(ColorText(self.color, text))


class Outer:
    """Class for printing colored strings to the console"""

    def __init__(self, text: str | ColorText = ""):
        self.text = str(text) if text else ""
        
    def _append_text(self, text: str | ColorText) -> Outer:    
        self.text += str(text)
        return self

    def append(self, text: str | ColorText) -> Outer:
        return self._append_text(text)

    def new_line(self) -> Outer:
        self.text += "\n"
        return self

    def print(self):
        """Function prints the text to the console"""
        print(self.text)


    def __str__(self):
        return self.text

    append_red = ColorAction(c.RED)
    append_green = ColorAction(c.GREEN)
    append_yellow = ColorAction(c.YELLOW)
    append_orange = ColorAction(c.ORANGE)
    append_blue = ColorAction(c.BLUE)
    append_purple = ColorAction(c.PURPLE)