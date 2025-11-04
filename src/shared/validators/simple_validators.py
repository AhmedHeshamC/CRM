"""
Simple Validators - KISS Principle
Focused, single-purpose validation functions
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from typing import Any, Dict, List


class ValidationError(Exception):
    """Simple validation error"""
    pass


class EmailValidator:
    """Simple email validation"""

    @staticmethod
    def validate(email: str) -> str:
        """Validate and clean email"""
        email = email.strip().lower()
        try:
            validate_email(email)
            return email
        except DjangoValidationError:
            raise ValidationError("Invalid email format")


class PhoneValidator:
    """Simple phone validation"""

    @staticmethod
    def validate(phone: str) -> str:
        """Validate and clean phone number"""
        phone = phone.strip()
        if len(phone) < 10:
            raise ValidationError("Phone number must be at least 10 digits")
        return phone


class RequiredFieldsValidator:
    """Simple required fields validation"""

    @staticmethod
    def validate(data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate required fields are present and not empty"""
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                raise ValidationError(f"{field} is required")


class ListValidator:
    """Simple list validation"""

    @staticmethod
    def validate_list(value: Any) -> List[str]:
        """Validate value is a list and clean it"""
        if not isinstance(value, list):
            raise ValidationError("Value must be a list")

        return [item.strip() for item in value if item.strip()]


class ContactValidator:
    """Composite validator for contacts - KISS approach"""

    def __init__(self):
        self.email_validator = EmailValidator()
        self.phone_validator = PhoneValidator()
        self.required_validator = RequiredFieldsValidator()
        self.list_validator = ListValidator()

    def validate_create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contact creation data"""
        # Required fields
        self.required_validator.validate(
            data, ['first_name', 'last_name', 'email', 'owner']
        )

        validated = {}
        validated['first_name'] = data['first_name'].strip()
        validated['last_name'] = data['last_name'].strip()
        validated['email'] = self.email_validator.validate(data['email'])
        validated['owner'] = data['owner']

        # Optional fields
        if 'phone' in data and data['phone']:
            validated['phone'] = self.phone_validator.validate(data['phone'])

        if 'tags' in data:
            validated['tags'] = self.list_validator.validate_list(data['tags'])

        return validated