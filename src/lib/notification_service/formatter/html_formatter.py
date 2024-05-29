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

    def _get_text(self, content: str, style: str = None) -> str:
        """Get a text."""
        return Text(content, style).get_html()

    def _get_table(self, content: dict, style: str = None) -> str:
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
            Table("".join(formatted_table_content), style).get_html()
            if formatted_table_content
            else None
        )

    @staticmethod
    def get_complete_html(body_content: str) -> str:
        _css_style = """
            body {}
            table, th, td { border: 1px solid black; margin: 2px; }       
            table { border-collapse: collapse; }
            th { background-color: lightgray; }
            tr:nth-child(odd) {background: #EEE}
            tr:nth-child(even) {background: #FFF}
            th:last-child, td:last-child, th:nth-last-child(2), td:nth-last-child(2), th:nth-last-child(3), 
            td:nth-last-child(3) { text-align: left; }       
            td {  padding-right: 10px; padding-left: 10px; }  
            .ok { background-color: lightgreen; }
            .error { background-color: #FFCCCB; }
            .warning { background-color: lightblue; }          
            .header {font-size: 19px; font-weight: bold; padding: 20px 10px;}
            """
        return f"<html><head><style>{_css_style}</style></head><body>{body_content}</body></html>"

    def get_formatted_message(self, message_body: list) -> str:
        """Get a final formatted message."""
        formatted_message_objects = []

        for message_object in message_body:
            try:
                object_type = [key for key in message_object.keys() if key != "style"][0]
            except IndexError:
                raise KeyError(f"Message object type is not set")

            content = message_object.get(object_type)
            style = message_object.get("style")

            formatted_object = self._format(object_type, content=content, style=style)

            if formatted_object is not None:
                formatted_message_objects.append(formatted_object)

        formatted_message_body = "".join(formatted_message_objects)
        formatted_message = self.get_complete_html(formatted_message_body)

        return formatted_message