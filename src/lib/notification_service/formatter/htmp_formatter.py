from .formatter import Formatter
from .blocks import Header, Table, TableCell, TableRow, TableHeaderCell


class HtmlFormatter(Formatter):
    @staticmethod
    def _get_formatted_table_row(
        table_cells: list, status: str = None, is_header: bool = False
    ) -> str:
        if table_cells:
            block_cls = TableHeaderCell if is_header else TableCell

            return TableRow(
                "".join([block_cls(cell).get_html() for cell in table_cells]), status
            ).get_html()

        return []

    def get_header(self, text: str) -> str:
        """Get a header."""
        return Header(text).get_html()

    def get_table(self, table_items: list, table_header: list = None) -> str:
        """Get a table."""
        formatted_table_rows = (
            [self._get_formatted_table_row(table_header, is_header=True)]
            if table_header is not None
            else []
        )

        for table_item in table_items:
            table_cells = table_item.get("cells")
            status = table_item.get("status")

            formatted_table_rows.append(
                self._get_formatted_table_row(table_cells, status=status)
            )

        return Table("".join(formatted_table_rows)).get_html()
