from .formatter import Formatter
from .blocks import Text, Table, TableCell, TableRow, TableHeaderCell, TableCaption


class HtmlFormatter(Formatter):
    @staticmethod
    def _get_formatted_table_row(row: list, is_header: bool = False) -> str:
        cells = row.get("values")
        style = row.get("style")

        if cells is not None:
            block_cls = TableHeaderCell if is_header else TableCell

            return TableRow(
                "".join([block_cls(cell).get_html() for cell in cells]), style
            ).get_html()

        return []

    def get_text(self, content: str, style: str = None) -> str:
        """Get a text."""
        return Text(content, style).get_html()

    def get_table(self, content: dict, style: str = None) -> str:
        """Get a table."""
        caption = content.get("caption")
        header = content.get("header")
        rows = content.get("rows")

        formatted_table_rows = (
            [self._get_formatted_table_row(header, is_header=True)]
            if header is not None
            else []
        )

        for row in rows:
            formatted_table_rows.append(self._get_formatted_table_row(row))

        formatted_caption = (
            [TableCaption(caption).get_html()] if caption is not None else []
        )
        formatted_table_content = formatted_caption + formatted_table_rows

        return (
            Table("".join(formatted_table_content)).get_html()
            if formatted_table_content
            else None
        )
