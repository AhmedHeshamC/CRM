"""
Unit Tests for Django Models - TDD Approach
These tests are written BEFORE implementation to drive development
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta

User = get_user_model()


class TestUserModel(TestCase):
    """Test cases for custom User model - Following TDD methodology"""

    def test_user_creation_with_email(self):
        """Test that user can be created with email instead of username"""
        # This test will FAIL initially - driving User model implementation
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        assert user.email == 'test@example.com'
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'
        assert user.check_password('testpass123')
        assert str(user) == 'John Doe'

    def test_user_email_normalization(self):
        """Test that email is normalized during creation"""
        # This test will FAIL initially - driving email normalization
        user = User.objects.create_user(
            email='Test@EXAMPLE.COM',
            password='testpass123'
        )
        assert user.email == 'Test@example.com'

    def test_user_email_required(self):
        """Test that email is required field"""
        # This test will FAIL initially - driving validation implementation
        with pytest.raises(ValueError):
            User.objects.create_user(
                email='',
                password='testpass123'
            )

    def test_user_create_superuser(self):
        """Test superuser creation with proper attributes"""
        # This test will FAIL initially - driving superuser implementation
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        assert admin_user.is_superuser
        assert admin_user.is_staff
        assert admin_user.is_active

    def test_user_role_field(self):
        """Test that user has role field with default values"""
        # This test will FAIL initially - driving role field implementation
        user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        assert user.role == 'sales'  # Default role
        assert hasattr(user, 'get_role_display')

    def test_user_profile_relationship(self):
        """Test user profile one-to-one relationship"""
        # This test will FAIL initially - driving profile model
        user = User.objects.create_user(
            email='profile@example.com',
            password='testpass123'
        )
        assert hasattr(user, 'profile')
        assert user.profile.user == user


class TestContactModel(TestCase):
    """Test cases for Contact model - Following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def test_contact_creation(self):
        """Test contact creation with all required fields"""
        # This test will FAIL initially - driving Contact model implementation
        from crm.apps.contacts.models import Contact

        contact = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@example.com',
            phone='+1234567890',
            company='Tech Corp',
            title='Software Engineer',
            owner=self.user
        )

        assert contact.first_name == 'Jane'
        assert contact.last_name == 'Smith'
        assert contact.email == 'jane.smith@example.com'
        assert contact.owner == self.user
        assert str(contact) == 'Jane Smith - Tech Corp'
        assert contact.created_at is not None
        assert contact.updated_at is not None

    def test_contact_email_unique(self):
        """Test that contact email must be unique per owner"""
        # This test will FAIL initially - driving unique constraint
        from crm.apps.contacts.models import Contact

        Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            owner=self.user
        )

        with pytest.raises(Exception):  # IntegrityError or ValidationError
            Contact.objects.create(
                first_name='Jane',
                last_name='Doe',
                email='jane@example.com',
                owner=self.user
            )

    def test_contact_phone_validation(self):
        """Test phone number format validation"""
        # This test will FAIL initially - driving phone validation
        from crm.apps.contacts.models import Contact

        # Valid phone numbers
        valid_phones = ['+1234567890', '+1-234-567-8900', '(234) 567-8900']

        for i, phone in enumerate(valid_phones):
            contact = Contact.objects.create(
                first_name='Test',
                last_name=f'User{i}',
                email=f'test{i}@example.com',
                phone=phone,
                owner=self.user
            )
            assert contact.phone == phone

    def test_contact_soft_delete(self):
        """Test that contacts are soft deleted"""
        # This test will FAIL initially - driving soft delete implementation
        from crm.apps.contacts.models import Contact

        contact = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            owner=self.user
        )

        contact_id = contact.id
        contact.delete()  # Soft delete

        assert not Contact.objects.filter(id=contact_id).exists()
        assert Contact.all_objects.filter(id=contact_id, is_deleted=True).exists()
        assert Contact.all_objects.filter(id=contact_id).exists()  # Include deleted

    def test_contact_tags_field(self):
        """Test contact tags functionality"""
        # This test will FAIL initially - driving tags implementation
        from crm.apps.contacts.models import Contact

        contact = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            owner=self.user,
            tags=['vip', 'prospect', 'enterprise']
        )

        assert 'vip' in contact.tags
        assert 'prospect' in contact.tags
        assert 'enterprise' in contact.tags
        assert len(contact.tags) == 3


class TestDealModel(TestCase):
    """Test cases for Deal model - Following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        from crm.apps.contacts.models import Contact
        self.contact = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            owner=self.user
        )

    def test_deal_creation(self):
        """Test deal creation with all required fields"""
        # This test will FAIL initially - driving Deal model implementation
        from crm.apps.deals.models import Deal

        deal = Deal.objects.create(
            title='Enterprise Software License',
            description='Large enterprise software licensing deal',
            value=100000.00,
            currency='USD',
            stage='qualified',
            probability=75,
            expected_close_date=timezone.now() + timedelta(days=90),
            contact=self.contact,
            owner=self.user
        )

        assert deal.title == 'Enterprise Software License'
        assert deal.value == 100000.00
        assert deal.currency == 'USD'
        assert deal.stage == 'qualified'
        assert deal.probability == 75
        assert deal.contact == self.contact
        assert deal.owner == self.user
        assert str(deal) == 'Enterprise Software License - USD 100,000.00'

    def test_deal_stage_transitions(self):
        """Test deal stage transition validation"""
        # This test will FAIL initially - driving stage transition logic
        from crm.apps.deals.models import Deal

        deal = Deal.objects.create(
            title='Test Deal',
            value=50000.00,
            stage='prospect',
            expected_close_date=timezone.now() + timedelta(days=60),
            contact=self.contact,
            owner=self.user
        )

        # Valid transitions
        deal.stage = 'qualified'
        deal.save()
        assert deal.stage == 'qualified'

        deal.stage = 'proposal'
        deal.save()
        assert deal.stage == 'proposal'

    def test_deal_value_validation(self):
        """Test deal value must be positive"""
        # This test will FAIL initially - driving value validation
        from crm.apps.deals.models import Deal

        with pytest.raises(ValidationError):
            Deal.objects.create(
                title='Invalid Deal',
                value=-1000.00,
                stage='prospect',
                expected_close_date=timezone.now() + timedelta(days=30),
                contact=self.contact,
                owner=self.user
            )

    def test_deal_probability_range(self):
        """Test deal probability must be between 0 and 100"""
        # This test will FAIL initially - driving probability validation
        from crm.apps.deals.models import Deal

        with pytest.raises(ValidationError):
            Deal.objects.create(
                title='Invalid Probability Deal',
                value=50000.00,
                probability=150,
                stage='prospect',
                expected_close_date=timezone.now() + timedelta(days=30),
                contact=self.contact,
                owner=self.user
            )

    def test_deal_pipeline_tracking(self):
        """Test deal pipeline movement tracking"""
        # This test will FAIL initially - driving pipeline history
        from crm.apps.deals.models import Deal

        deal = Deal.objects.create(
            title='Pipeline Test Deal',
            value=75000.00,
            stage='prospect',
            expected_close_date=timezone.now() + timedelta(days=45),
            contact=self.contact,
            owner=self.user
        )

        initial_stage = deal.stage
        deal.stage = 'qualified'
        deal.save()

        # Should track stage changes
        assert hasattr(deal, 'stage_history')
        assert deal.stage_history.count() >= 1

    def test_deal_win_loss_tracking(self):
        """Test deal won/lost status tracking"""
        # This test will FAIL initially - driving win/loss tracking
        from crm.apps.deals.models import Deal

        deal = Deal.objects.create(
            title='Win/Loss Test Deal',
            value=50000.00,
            stage='proposal',
            expected_close_date=timezone.now() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )

        # Mark as won
        deal.stage = 'closed_won'
        deal.save()

        assert deal.is_won
        assert not deal.is_lost
        assert deal.closed_date is not None

        # Mark as lost
        deal.stage = 'closed_lost'
        deal.deal_loss_reason = 'Competitor pricing'
        deal.save()

        assert not deal.is_won
        assert deal.is_lost
        assert deal.deal_loss_reason == 'Competitor pricing'


class TestActivityModel(TestCase):
    """Test cases for Activity model - Following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        from crm.apps.contacts.models import Contact
        from crm.apps.deals.models import Deal

        self.contact = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            owner=self.user
        )

        self.deal = Deal.objects.create(
            title='Test Deal',
            value=50000.00,
            stage='qualified',
            expected_close_date=timezone.now() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )

    def test_activity_creation(self):
        """Test activity creation with different types"""
        # This test will FAIL initially - driving Activity model implementation
        from crm.apps.activities.models import Activity

        activity = Activity.objects.create(
            type='call',
            title='Initial Discovery Call',
            description='Discussed client requirements and budget',
            contact=self.contact,
            deal=self.deal,
            owner=self.user,
            scheduled_at=timezone.now() + timedelta(hours=2),
            duration_minutes=60
        )

        assert activity.type == 'call'
        assert activity.title == 'Initial Discovery Call'
        assert activity.contact == self.contact
        assert activity.deal == self.deal
        assert activity.owner == self.user
        assert str(activity) == 'Phone Call - Initial Discovery Call'

    def test_activity_scheduling_validation(self):
        """Test activity scheduling validation"""
        # This test will FAIL initially - driving scheduling validation
        from crm.apps.activities.models import Activity

        # Past activity should not be allowed for future activities
        past_time = timezone.now() - timedelta(hours=1)

        with pytest.raises(ValidationError):
            Activity.objects.create(
                type='meeting',
                title='Future Meeting',
                contact=self.contact,
                owner=self.user,
                scheduled_at=past_time,
                duration_minutes=30
            )

    def test_activity_completion_tracking(self):
        """Test activity completion status tracking"""
        # This test will FAIL initially - driving completion tracking
        from crm.apps.activities.models import Activity

        activity = Activity.objects.create(
            type='email',
            title='Follow-up Email',
            contact=self.contact,
            owner=self.user,
            scheduled_at=timezone.now()
        )

        assert not activity.is_completed
        assert activity.completed_at is None

        # Mark as completed
        activity.mark_completed()
        activity.save()

        assert activity.is_completed
        assert activity.completed_at is not None

    def test_activity_reminders(self):
        """Test activity reminder functionality"""
        # This test will FAIL initially - driving reminder system
        from crm.apps.activities.models import Activity

        activity = Activity.objects.create(
            type='meeting',
            title='Client Meeting',
            contact=self.contact,
            owner=self.user,
            scheduled_at=timezone.now() + timedelta(hours=24),
            reminder_minutes=60
        )

        assert activity.reminder_minutes == 60
        assert activity.reminder_at is not None
        assert activity.reminder_at < activity.scheduled_at