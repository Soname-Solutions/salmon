import mimetypes

DEFAULT_MIME_TYPE = 'application/octet-stream'


class File:

    def __init__(self, name: str, content: str):
        """Ititiate file class.

        Args
            name (str): File name with the extension.
            content (str): File content.
        """
        self.name = name
        self.content = content

    @property
    def mime_type(self) -> str:
        return mimetypes.guess_type(self.name, strict=False)[0] or DEFAULT_MIME_TYPE


class Message:

    def __init__(self, body: str, header: str = None, file: File = None):
        """Ititiate message class.

        Args
            body (str): Message body to send.
            header (str): Message header.
            file (File): File to attach.
        """
        self.body = body
        self.header = header
        self.file = file
