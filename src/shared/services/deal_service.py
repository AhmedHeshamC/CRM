"""
Deal Service Implementation
Following SOLID principles and enterprise best practices
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError

from .base_service import BaseService, ValidationError, NotFoundError, PermissionError, ConflictError
from ..repositories.deal_repository import DealRepository
from ..repositories.contact_repository import ContactRepository
from crm.apps.deals.models import Deal
from crm.apps.contacts.models import Contact

User = get_user_model()


class DealService(BaseService[Deal]):
    """
    Service for Deal business operations
    Following SOLID principles and clean architecture
    """

    def __init__(self,
                 deal_repository: Optional[DealRepository] = None,
                 contact_repository: Optional[ContactRepository] = None):
        """Initialize deal service with repositories"""
        super().__init__(deal_repository or DealRepository())
        self.contact_repository = contact_repository or ContactRepository()

    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate deal data for creation

        Args:
            data: Deal data

        Returns:
            Validated data

        Raises:
            ValidationError: If data is invalid
        """
        validated_data = {}

        # Validate required fields
        required_fields = ['title', 'value', 'stage', 'expected_close_date', 'contact', 'owner']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValidationError(f"{field} is required")

        # Validate title
        validated_data['title'] = data['title'].strip()
        if len(validated_data['title']) < 3:
            raise ValidationError("Title must be at least 3 characters long")

        # Validate value
        try:
            value = Decimal(str(data['value']))
            if value <= 0:
                raise ValidationError("Deal value must be positive")
            validated_data['value'] = value
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid deal value format")

        # Validate stage
        valid_stages = [choice[0] for choice in Deal.STAGE_CHOICES]
        if data['stage'] not in valid_stages:
            raise ValidationError(f"Invalid stage. Must be one of: {valid_stages}")
        validated_data['stage'] = data['stage']

        # Validate expected close date
        expected_date = data['expected_close_date']
        if isinstance(expected_date, str):
            try:
                expected_date = date.fromisoformat(expected_date.replace('Z', '+00:00').split('T')[0])
            except (ValueError, AttributeError):
                raise ValidationError("Invalid expected close date format")

        if expected_date <= date.today() and data['stage'] not in ['closed_won', 'closed_lost']:
            raise ValidationError("Expected close date cannot be in the past for open deals")
        validated_data['expected_close_date'] = expected_date

        # Validate contact
        contact = data['contact']
        if isinstance(contact, int):
            contact_obj = self.contact_repository.get_by_id(contact)
            if not contact_obj:
                raise ValidationError("Contact not found")
            validated_data['contact'] = contact_obj
        else:
            validated_data['contact'] = contact

        # Validate owner
        owner = data['owner']
        if isinstance(owner, int):
            owner_obj = User.objects.get(id=owner)
            validated_data['owner'] = owner_obj
        else:
            validated_data['owner'] = owner

        # Validate optional fields
        if 'description' in data and data['description']:
            validated_data['description'] = data['description'].strip()

        # Validate currency
        if 'currency' in data:
            valid_currencies = [choice[0] for choice in Deal.CURRENCY_CHOICES]
            if data['currency'] not in valid_currencies:
                raise ValidationError(f"Invalid currency. Must be one of: {valid_currencies}")
            validated_data['currency'] = data['currency']
        else:
            validated_data['currency'] = 'USD'

        # Validate probability
        if 'probability' in data:
            probability = data['probability']
            if not isinstance(probability, int) or probability < 0 or probability > 100:
                raise ValidationError("Probability must be an integer between 0 and 100")
            validated_data['probability'] = probability
        else:
            # Set default probability based on stage
            stage_probabilities = {
                'prospect': 10,
                'qualified': 25,
                'proposal': 50,
                'negotiation': 75,
                'closed_won': 100,
                'closed_lost': 0,
            }
            validated_data['probability'] = stage_probabilities.get(data['stage'], 0)

        return validated_data

    def validate_update_data(self, entity_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate deal data for update

        Args:
            entity_id: Deal ID
            data: Update data

        Returns:
            Validated data

        Raises:
            ValidationError: If data is invalid
            NotFoundError: If deal doesn't exist
        """
        # Check if deal exists
        deal = self.repository.get_by_id(entity_id)
        if not deal:
            raise NotFoundError(f"Deal with ID {entity_id} not found")

        validated_data = {}

        # Validate and clean fields
        if 'title' in data:
            if not data['title'].strip():
                raise ValidationError("Title cannot be empty")
            if len(data['title'].strip()) < 3:
                raise ValidationError("Title must be at least 3 characters long")
            validated_data['title'] = data['title'].strip()

        if 'value' in data:
            try:
                value = Decimal(str(data['value']))
                if value <= 0:
                    raise ValidationError("Deal value must be positive")
                validated_data['value'] = value
            except (InvalidOperation, ValueError):
                raise ValidationError("Invalid deal value format")

        if 'stage' in data:
            valid_stages = [choice[0] for choice in Deal.STAGE_CHOICES]
            if data['stage'] not in valid_stages:
                raise ValidationError(f"Invalid stage. Must be one of: {valid_stages}")

            # Validate stage transition
            if not deal.can_transition_to(data['stage']):
                current_stage_display = dict(Deal.STAGE_CHOICES).get(deal.stage, deal.stage)
                new_stage_display = dict(Deal.STAGE_CHOICES).get(data['stage'], data['stage'])
                raise ValidationError(f"Cannot transition from {current_stage_display} to {new_stage_display}")

            validated_data['stage'] = data['stage']

        if 'expected_close_date' in data:
            expected_date = data['expected_close_date']
            if isinstance(expected_date, str):
                try:
                    expected_date = date.fromisoformat(expected_date.replace('Z', '+00:00').split('T')[0])
                except (ValueError, AttributeError):
                    raise ValidationError("Invalid expected close date format")

            # Check if date is in the past for open deals
            current_stage = data.get('stage', deal.stage)
            if expected_date <= date.today() and current_stage not in ['closed_won', 'closed_lost']:
                raise ValidationError("Expected close date cannot be in the past for open deals")
            validated_data['expected_close_date'] = expected_date

        if 'probability' in data:
            probability = data['probability']
            if not isinstance(probability, int) or probability < 0 or probability > 100:
                raise ValidationError("Probability must be an integer between 0 and 100")
            validated_data['probability'] = probability

        if 'description' in data:
            validated_data['description'] = data['description'].strip() if data['description'] else None

        if 'currency' in data:
            valid_currencies = [choice[0] for choice in Deal.CURRENCY_CHOICES]
            if data['currency'] not in valid_currencies:
                raise ValidationError(f"Invalid currency. Must be one of: {valid_currencies}")
            validated_data['currency'] = data['currency']

        return validated_data

    def create_deal(self, data: Dict[str, Any], user_id: int) -> Deal:
        """
        Create a new deal with business logic

        Args:
            data: Deal data
            user_id: ID of user creating the deal

        Returns:
            Created deal

        Raises:
            ValidationError: If data is invalid
            PermissionError: If user doesn't have permission
            NotFoundError: If contact doesn't exist
        """
        # Validate owner permissions
        if 'owner' in data:
            owner_id = data['owner'].id if hasattr(data['owner'], 'id') else data['owner']
            if owner_id != user_id:
                user = User.objects.get(id=user_id)
                if not user.is_admin() and not user.is_manager():
                    raise PermissionError("You can only create deals for yourself")

        # Validate contact access
        contact_id = data['contact'].id if hasattr(data['contact'], 'id') else data['contact']
        contact = self.contact_repository.get_by_id(contact_id)
        if not contact:
            raise NotFoundError(f"Contact with ID {contact_id} not found")

        user = User.objects.get(id=user_id)
        if contact.owner_id != user_id and not user.is_admin():
            raise PermissionError("You can only create deals for your own contacts")

        return self.create(data)

    def update_deal(self, deal_id: int, data: Dict[str, Any], user_id: int) -> Deal:
        """
        Update a deal with business logic

        Args:
            deal_id: Deal ID
            data: Update data
            user_id: ID of user updating the deal

        Returns:
            Updated deal

        Raises:
            ValidationError: If data is invalid
            NotFoundError: If deal doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get deal to check permissions
        deal = self.repository.get_by_id(deal_id)
        if not deal:
            raise NotFoundError(f"Deal with ID {deal_id} not found")

        # Check permissions
        user = User.objects.get(id=user_id)
        if deal.owner_id != user_id and not user.is_admin():
            raise PermissionError("You can only update your own deals")

        return self.update(deal_id, data)

    def update_deal_stage(self, deal_id: int, new_stage: str, user_id: int) -> Deal:
        """
        Update deal stage with business logic

        Args:
            deal_id: Deal ID
            new_stage: New stage
            user_id: ID of user updating the deal

        Returns:
            Updated deal

        Raises:
            ValidationError: If stage transition is invalid
            NotFoundError: If deal doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get deal to check permissions
        deal = self.repository.get_by_id(deal_id)
        if not deal:
            raise NotFoundError(f"Deal with ID {deal_id} not found")

        # Check permissions
        user = User.objects.get(id=user_id)
        if deal.owner_id != user_id and not user.is_admin():
            raise PermissionError("You can only update your own deals")

        # Validate stage transition
        if not deal.can_transition_to(new_stage):
            current_stage_display = dict(Deal.STAGE_CHOICES).get(deal.stage, deal.stage)
            new_stage_display = dict(Deal.STAGE_CHOICES).get(new_stage, new_stage)
            raise ValidationError(f"Cannot transition from {current_stage_display} to {new_stage_display}")

        success = self.repository.update_deal_stage(deal_id, new_stage, user_id)
        if not success:
            raise ValidationError("Failed to update deal stage")

        return self.repository.get_by_id(deal_id)

    def close_deal_as_won(self, deal_id: int, final_value: Optional[Decimal] = None, user_id: int = None) -> Deal:
        """
        Close deal as won with business logic

        Args:
            deal_id: Deal ID
            final_value: Optional final value
            user_id: ID of user closing the deal

        Returns:
            Updated deal

        Raises:
            ValidationError: If deal cannot be closed as won
            NotFoundError: If deal doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get deal to check permissions
        deal = self.repository.get_by_id(deal_id)
        if not deal:
            raise NotFoundError(f"Deal with ID {deal_id} not found")

        # Check permissions
        if user_id:
            user = User.objects.get(id=user_id)
            if deal.owner_id != user_id and not user.is_admin():
                raise PermissionError("You can only close your own deals")

        # Validate that deal can be closed as won
        if deal.stage == 'closed_won':
            raise ValidationError("Deal is already marked as won")
        elif deal.stage == 'closed_lost':
            raise ValidationError("Cannot re-open a lost deal as won")

        success = self.repository.close_deal_as_won(deal_id, final_value)
        if not success:
            raise ValidationError("Failed to close deal as won")

        return self.repository.get_by_id(deal_id)

    def close_deal_as_lost(self, deal_id: int, loss_reason: str, user_id: int = None) -> Deal:
        """
        Close deal as lost with business logic

        Args:
            deal_id: Deal ID
            loss_reason: Reason for losing the deal
            user_id: ID of user closing the deal

        Returns:
            Updated deal

        Raises:
            ValidationError: If deal cannot be closed as lost
            NotFoundError: If deal doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get deal to check permissions
        deal = self.repository.get_by_id(deal_id)
        if not deal:
            raise NotFoundError(f"Deal with ID {deal_id} not found")

        # Check permissions
        if user_id:
            user = User.objects.get(id=user_id)
            if deal.owner_id != user_id and not user.is_admin():
                raise PermissionError("You can only close your own deals")

        # Validate loss reason
        if not loss_reason or not loss_reason.strip():
            raise ValidationError("Loss reason is required when closing a deal as lost")

        # Validate that deal can be closed as lost
        if deal.stage == 'closed_lost':
            raise ValidationError("Deal is already marked as lost")
        elif deal.stage == 'closed_won':
            raise ValidationError("Cannot mark a won deal as lost")

        success = self.repository.close_deal_as_lost(deal_id, loss_reason.strip())
        if not success:
            raise ValidationError("Failed to close deal as lost")

        return self.repository.get_by_id(deal_id)

    def get_user_deals(self, user_id: int, **filters) -> List[Deal]:
        """
        Get all deals for a user

        Args:
            user_id: User ID
            **filters: Additional filters

        Returns:
            List of deals
        """
        filters['owner_id'] = user_id
        return self.repository.filter(**filters)

    def get_deal_pipeline(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get deal pipeline statistics

        Args:
            user_id: Optional user ID to filter by

        Returns:
            Pipeline statistics
        """
        stats = self.repository.get_deal_statistics(user_id)
        pipeline_values = self.repository.get_pipeline_value_by_stage(user_id)

        return {
            'statistics': stats,
            'pipeline_by_stage': pipeline_values,
            'total_pipeline_value': sum(pipeline_values.values()),
        }

    def get_closing_soon_deals(self, user_id: int, days: int = 30) -> List[Deal]:
        """
        Get deals closing soon for a user

        Args:
            user_id: User ID
            days: Number of days ahead

        Returns:
            List of deals closing soon
        """
        return self.repository.get_closing_soon(days, user_id)

    def get_overdue_deals(self, user_id: int) -> List[Deal]:
        """
        Get overdue deals for a user

        Args:
            user_id: User ID

        Returns:
            List of overdue deals
        """
        return self.repository.get_overdue_deals(user_id)

    def search_user_deals(self, user_id: int, query: str) -> List[Deal]:
        """
        Search deals for a specific user

        Args:
            user_id: User ID
            query: Search query

        Returns:
            List of matching deals
        """
        return self.repository.search_deals(query, user_id)

    def get_deals_by_stage(self, user_id: int, stage: str) -> List[Deal]:
        """
        Get deals by stage for a user

        Args:
            user_id: User ID
            stage: Deal stage

        Returns:
            List of deals
        """
        return self.repository.get_by_stage(stage, user_id)

    def get_deals_by_value_range(self, user_id: int, min_value: float, max_value: float) -> List[Deal]:
        """
        Get deals by value range for a user

        Args:
            user_id: User ID
            min_value: Minimum deal value
            max_value: Maximum deal value

        Returns:
            List of deals
        """
        return self.repository.get_deals_by_value_range(min_value, max_value, user_id)

    def get_won_deals_this_month(self, user_id: int) -> List[Deal]:
        """
        Get deals won this month for a user

        Args:
            user_id: User ID

        Returns:
            List of won deals
        """
        # Calculate first day of current month
        today = date.today()
        first_day = today.replace(day=1)

        return self.repository.get_won_deals(user_id, (today - first_day).days + 1)