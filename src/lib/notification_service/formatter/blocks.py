class Block:
    def __init__(self, text: str, css_class: str = None) -> None:
        self._text = text
        self._css_class = css_class

    @property
    def css_class(self):
        return "" if self._css_class is None else f' class="{self._css_class}"'


class Header(Block):
    def get_html(self) -> str:
        """Get HTML for the header."""
        return f"<h1>{self._text}</h1>"


class TableHeaderCell(Block):
    def get_html(self) -> str:
        """Get HTML for the table header cell."""
        return f"<th>{self._text}</th>"


class TableCell(Block):
    def get_html(self) -> str:
        """Get HTML for the table cell."""
        return f"<td>{self._text}</td>"


class TableRow(Block):
    def get_html(self) -> str:
        """Get HTML for the table row."""
        return f"<tr{self.css_class}>{self._text}</tr>"


class Table(Block):
    def get_html(self) -> str:
        """Get HTML for the table."""
        return f"<table>{self._text}</table>"
