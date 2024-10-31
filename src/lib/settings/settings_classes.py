from typing import Optional
from pydantic import BaseModel


class DeliveryMethod(BaseModel):
    name: str
    delivery_method_type: str

    # applicable for AWS_SES & SMTP
    sender_email: Optional[str] = None
    # True -> <div style="color: red">; False -> <div class="example_class">
    use_inline_css_styles: Optional[bool] = False

    # applicable for SMTP
    credentials_secret_name: Optional[str] = None
    use_ssl: Optional[bool] = True
    timeout: Optional[float] = 10.0
