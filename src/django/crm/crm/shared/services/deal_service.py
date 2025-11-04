"""
Deal Service - KISS Implementation
Simple business logic following SOLID principles
"""

from ..repositories.deal_repository import DealRepository
from django.core.exceptions import ValidationError


class DealService:
    """
    Simple Deal Service - Following KISS principle
    Focused only on deal business logic
    """

    def __init__(self, repository=None):
        """Initialize with repository"""
        self.repository = repository or DealRepository()

    def create_deal(self, data, user_id):
        """Create new deal with simple validation"""
        # Set owner
        data['owner_id'] = user_id
        return self.repository.create(**data)

    def update_deal(self, deal_id, data, user_id):
        """Update deal with permission check"""
        deal = self.repository.get_by_id(deal_id)
        if not deal:
            raise ValidationError('Deal not found.')

        # Check permission
        if deal.owner_id != user_id:
            raise ValidationError('Permission denied.')

        return self.repository.update(deal, **data)

    def advance_stage(self, deal_id, user_id):
        """Advance deal to next stage"""
        deal = self.repository.get_by_id(deal_id)
        if not deal:
            raise ValidationError('Deal not found.')

        if deal.owner_id != user_id:
            raise ValidationError('Permission denied.')

        # Simple stage progression
        stages = ['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won']
        current_stage_index = stages.index(deal.stage) if deal.stage in stages else -1

        if current_stage_index < len(stages) - 1:
            new_stage = stages[current_stage_index + 1]
            return self.repository.update(deal, stage=new_stage)

        raise ValidationError('Deal is already in final stage.')

    def lose_deal(self, deal_id, user_id, reason=None):
        """Mark deal as lost"""
        deal = self.repository.get_by_id(deal_id)
        if not deal:
            raise ValidationError('Deal not found.')

        if deal.owner_id != user_id:
            raise ValidationError('Permission denied.')

        data = {'is_lost': True, 'stage': 'closed_lost'}
        if reason:
            data['loss_reason'] = reason

        return self.repository.update(deal, **data)

    def win_deal(self, deal_id, user_id):
        """Mark deal as won"""
        deal = self.repository.get_by_id(deal_id)
        if not deal:
            raise ValidationError('Deal not found.')

        if deal.owner_id != user_id:
            raise ValidationError('Permission denied.')

        return self.repository.update(deal, is_won=True, stage='closed_won')

    def get_user_deals(self, user_id, include_closed=False):
        """Get deals for user"""
        return self.repository.get_user_deals(user_id, include_closed)

    def get_pipeline_value(self, user_id=None):
        """Get total value of open deals"""
        return self.repository.get_pipeline_value(user_id)

    def get_deal_statistics(self, user_id=None):
        """Get deal statistics"""
        return self.repository.get_statistics(user_id)

    def search_user_deals(self, user_id, query):
        """Search deals for user"""
        return self.repository.search_deals(user_id, query)