import re

class PiiRedactionService:
    """
    A service to redact Personally Identifiable Information (PII) from text.
    """

    def __init__(self):
        # A simple regex to find email addresses.
        self.email_regex = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    def sanitize(self, text: str) -> str:
        """
        Sanitizes the given text by redacting PII.
        """
        sanitized_text = self.email_regex.sub("[REDACTED EMAIL]", text)
        return sanitized_text
