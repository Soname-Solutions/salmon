from .base_formatter import BaseFormatter


class PlainTextFormatter(BaseFormatter):
    # def get_formatted_message(self, message_body: list) -> str:
    #     """Get a final formatted message."""
    #     return message_body

    def _get_text(self, content: str, style: str = None) -> str:
        """Get a text."""
        return f"{content}\n"

    def _get_table(self, content: dict, style: str = None) -> str:
        """Get a table."""
        caption = content.get("caption")
        header = content.get("header")
        rows = content.get("rows")

        table_data = [row["values"] for row in rows]

        # Calculate the maximum width for each column
        max_widths = [max(len(str(item)) for item in col) for col in zip(*table_data)]

        # Function to create a row string with proper padding
        def format_row(row, max_widths):
            return (
                "| "
                + " | ".join(
                    str(item).ljust(max_width)
                    for item, max_width in zip(row, max_widths)
                )
                + " |"
            )

        # Creating the ASCII table
        header_line = "+-" + "-+-".join("-" * width for width in max_widths) + "-+"
        rows_lines = [format_row(row, max_widths) for row in table_data]

        # Combine all parts into the final table string
        ascii_table = (
            header_line
            + "\n"
            + ("\n" + header_line + "\n").join(rows_lines)
            + "\n"
            + header_line
        )

        return ascii_table

    def get_formatted_message(self, message_body: list) -> str:
        """Get a final formatted message."""
        formatted_message_objects = []

        for message_object in message_body:
            try:
                object_type = [key for key in message_object.keys() if key != "style"][
                    0
                ]
            except IndexError:
                raise KeyError(f"Message object type is not set")

            content = message_object.get(object_type)
            style = message_object.get(
                "style"
            )  # for backward compatibility. For plain text, "style" is not applicable

            formatted_object = self._format(object_type, content=content, style=style)

            if formatted_object is not None:
                formatted_message_objects.append(formatted_object)

        formatted_message_body = "\n".join(formatted_message_objects)
        formatted_message = formatted_message_body

        return formatted_message
