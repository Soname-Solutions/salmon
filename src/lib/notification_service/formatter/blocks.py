class Block:
    def __init__(self, text: str, style: str = None) -> None:
        self._text = text
        self._style = style

    @property
    def css_class(self) -> str:
        """Css class for a HTML block."""
        return "" if self._style is None else f' class="{self._style}"'


class Text(Block):
    def get_html(self) -> str:
        """Get HTML for the text."""
        return f"<div{self.css_class}>{self._text}</div><br/>"


class TableHeaderCell(Block):
    def get_html(self) -> str:
        """Get HTML for the table header cell."""
        return f"<th{self.css_class}>{self._text}</th>"


class TableCell(Block):
    def get_html(self) -> str:
        """Get HTML for the table cell."""
        return f"<td{self.css_class}>{self._text}</td>"


class TableRow(Block):
    def get_html(self) -> str:
        """Get HTML for the table row."""
        return f"<tr{self.css_class}>{self._text}</tr>"


class Table(Block):
    def get_html(self) -> str:
        """Get HTML for the table."""
        return f"<table{self.css_class}>{self._text}</table><br/>"


class TableCaption(Block):
    def get_html(self) -> str:
        """Get HTML for the caption."""
        return f"<caption{self.css_class}>{self._text}</caption>"
