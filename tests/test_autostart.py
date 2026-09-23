from asusfancontrol.autostart import _ps_literal


class TestPsLiteral:
    def test_wraps_plain_string_in_single_quotes(self):
        assert _ps_literal("hello") == "'hello'"

    def test_escapes_embedded_single_quote_by_doubling(self):
        assert _ps_literal("O'Brien") == "'O''Brien'"

    def test_escapes_multiple_single_quotes(self):
        assert _ps_literal("''") == "''''''"

    def test_empty_string_yields_empty_quoted_literal(self):
        assert _ps_literal("") == "''"

    def test_path_with_spaces_stays_intact_inside_quotes(self):
        assert _ps_literal(r"C:\Program Files\App.exe") == r"'C:\Program Files\App.exe'"

    def test_does_not_treat_dollar_sign_specially(self):
        # single-quoted PowerShell strings are literal: $ must not be expanded
        assert _ps_literal("$env:USERNAME") == "'$env:USERNAME'"
