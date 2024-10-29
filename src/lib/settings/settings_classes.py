from typing import Optional
from pydantic import BaseModel


class DeliveryMethod(BaseModel):
    name: str
    delivery_method_type: str
    sender_email: Optional[str] = None
    credentials_secret_name: Optional[str] = None
    use_inline_css_styles: Optional[
        bool
    ] = False  # True -> <div style="color: red">; False -> <div class="example_class">
    use_ssl: Optional[bool] = None
    timeout: Optional[int] = None
