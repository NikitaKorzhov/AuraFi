import cli.colorss as c
from cli.output import ColorText, Outer


class TestColorText:
    def test_without_color_keeps_text_unchanged(self):
        assert str(ColorText(text="hello")) == "hello"

    def test_with_color_wraps_text_with_color_and_reset_codes(self):
        colored = ColorText(c.RED, "hello")
        assert str(colored) == f"{c.RED}hello{c.RESET}"

    def test_repr_matches_str(self):
        colored = ColorText(c.GREEN, "ok")
        assert repr(colored) == str(colored)

    def test_print_writes_text_to_stdout(self, capsys):
        ColorText(c.BLUE, "hi").print()
        assert capsys.readouterr().out == f"{c.BLUE}hi{c.RESET}\n"


class TestOuter:
    def test_starts_empty_by_default(self):
        assert str(Outer()) == ""

    def test_can_be_seeded_with_initial_text(self):
        assert str(Outer("start")) == "start"

    def test_append_adds_text_and_returns_self_for_chaining(self):
        outer = Outer("a")
        result = outer.append("b")
        assert result is outer
        assert str(outer) == "ab"

    def test_new_line_appends_a_newline(self):
        outer = Outer("a").new_line().append("b")
        assert str(outer) == "a\nb"

    def test_print_writes_text_to_stdout(self, capsys):
        Outer("hello").print()
        assert capsys.readouterr().out == "hello\n"


class TestColorActionDescriptor:
    def test_class_level_access_creates_a_brand_new_outer_each_time(self):
        first = Outer.append_red("a")
        second = Outer.append_red("b")
        assert first is not second
        assert str(first) == f"{c.RED}a{c.RESET}"
        assert str(second) == f"{c.RED}b{c.RESET}"

    def test_instance_level_access_appends_to_the_existing_outer(self):
        outer = Outer("prefix-")
        result = outer.append_green("ok")
        assert result is outer
        assert str(outer) == f"prefix-{c.GREEN}ok{c.RESET}"

    def test_chaining_multiple_colors_on_one_instance(self):
        outer = Outer().append_yellow("warn").append_blue("info")
        assert str(outer) == f"{c.YELLOW}warn{c.RESET}{c.BLUE}info{c.RESET}"

    def test_every_exposed_color_action_uses_its_own_color_constant(self):
        pairs = [
            (Outer.append_red, c.RED),
            (Outer.append_green, c.GREEN),
            (Outer.append_yellow, c.YELLOW),
            (Outer.append_orange, c.ORANGE),
            (Outer.append_blue, c.BLUE),
            (Outer.append_purple, c.PURPLE),
        ]
        for action, color in pairs:
            assert str(action("x")) == f"{color}x{c.RESET}"
