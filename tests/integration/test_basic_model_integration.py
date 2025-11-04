"""
Basic Model Integration Tests
Following TDD, SOLID, and KISS principles

Red-Green-Refactor approach:
1. RED: Write failing tests for model interactions
2. GREEN: Make tests pass with simple implementation
3. REFACTOR: Improve code while maintaining functionality
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class TestUserContactIntegration(TransactionTestCase):
    """
    Test integration between User and Contact models
    Following KISS principle - simple, focused tests
    """

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )

    def test_user_can_create_multiple_contacts(self):
        """
        RED: Test that user can create and manage multiple contacts
        This should drive the relationship implementation
        """
        from crm.apps.contacts.models import Contact

        # Create multiple contacts for the same user
        contact1 = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            owner=self.user
        )

        contact2 = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            owner=self.user
        )

        # Verify relationships work correctly
        user_contacts = Contact.objects.filter(owner=self.user)
        self.assertEqual(user_contacts.count(), 2)
        self.assertIn(contact1, user_contacts)
        self.assertIn(contact2, user_contacts)

        # Test user relationship back to contacts
        self.assertEqual(self.user.contacts.count(), 2)
        self.assertIn(contact1, self.user.contacts.all())
        self.assertIn(contact2, self.user.contacts.all())

    def test_contact_soft_delete_with_user_relationship(self):
        """
        RED: Test that soft delete doesn't break user relationships
        This should drive the soft delete manager implementation
        """
        from crm.apps.contacts.models import Contact

        contact = Contact.objects.create(
            first_name='Sarah',
            last_name='Wilson',
            email='sarah@example.com',
            owner=self.user
        )

        # Verify initial state
        self.assertEqual(Contact.objects.filter(owner=self.user).count(), 1)
        self.assertEqual(self.user.contacts.count(), 1)

        # Soft delete the contact
        contact.delete()

        # Verify soft delete behavior
        self.assertEqual(Contact.objects.filter(owner=self.user).count(), 0)
        self.assertEqual(self.user.contacts.count(), 0)
        self.assertEqual(Contact.all_objects.filter(owner=self.user).count(), 1)

        # Restore contact
        contact.restore()
        self.assertEqual(Contact.objects.filter(owner=self.user).count(), 1)


class TestContactDealIntegration(TransactionTestCase):
    """
    Test integration between Contact and Deal models
    Following SOLID Single Responsibility principle
    """

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='sales@example.com',
            first_name='Sales',
            last_name='User',
            password='testpass123'
        )

        from crm.apps.contacts.models import Contact
        self.contact = Contact.objects.create(
            first_name='Big',
            last_name='Client',
            email='client@example.com',
            owner=self.user
        )

    def test_contact_can_have_multiple_deals(self):
        """
        RED: Test that contact can be associated with multiple deals
        This should drive the deal-contact relationship
        """
        from crm.apps.deals.models import Deal

        # Create multiple deals for the same contact
        deal1 = Deal.objects.create(
            title='First Deal',
            value=50000.00,
            stage='qualified',
            expected_close_date=timezone.now() + timedelta(days=60),
            contact=self.contact,
            owner=self.user
        )

        deal2 = Deal.objects.create(
            title='Second Deal',
            value=75000.00,
            stage='prospect',
            expected_close_date=timezone.now() + timedelta(days=90),
            contact=self.contact,
            owner=self.user
        )

        # Verify relationships
        contact_deals = Deal.objects.filter(contact=self.contact)
        self.assertEqual(contact_deals.count(), 2)

        # Test contact relationship back to deals
        self.assertEqual(self.contact.deals.count(), 2)
        self.assertIn(deal1, self.contact.deals.all())
        self.assertIn(deal2, self.contact.deals.all())

    def test_deal_value_calculation_through_contact(self):
        """
        RED: Test that we can calculate total deal value for a contact
        This should drive the deal aggregation methods
        """
        from crm.apps.deals.models import Deal

        # Create deals with different values
        Deal.objects.create(
            title='Small Deal',
            value=25000.00,
            stage='closed_won',
            expected_close_date=timezone.now() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )

        Deal.objects.create(
            title='Large Deal',
            value=100000.00,
            stage='proposal',
            expected_close_date=timezone.now() + timedelta(days=45),
            contact=self.contact,
            owner=self.user
        )

        # Test total deal value calculation
        total_value = self.contact.get_total_deal_value()
        self.assertEqual(total_value, 125000.00)

        # Test deals count
        self.assertEqual(self.contact.get_deals_count(), 2)


class TestDealActivityIntegration(TransactionTestCase):
    """
    Test integration between Deal and Activity models
    Following KISS principle - focused, simple tests
    """

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='activity@example.com',
            first_name='Activity',
            last_name='User',
            password='testpass123'
        )

        from crm.apps.contacts.models import Contact
        self.contact = Contact.objects.create(
            first_name='Active',
            last_name='Client',
            email='active@example.com',
            owner=self.user
        )

        from crm.apps.deals.models import Deal
        self.deal = Deal.objects.create(
            title='Test Deal',
            value=50000.00,
            stage='qualified',
            expected_close_date=timezone.now() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )

    def test_deal_can_have_multiple_activities(self):
        """
        RED: Test that deal can have multiple related activities
        This should drive the deal-activity relationship
        """
        from crm.apps.activities.models import Activity

        # Create multiple activities for the deal
        activity1 = Activity.objects.create(
            type='call',
            title='Initial Call',
            contact=self.contact,
            deal=self.deal,
            owner=self.user,
            scheduled_at=timezone.now() + timedelta(hours=1),
            duration_minutes=30
        )

        activity2 = Activity.objects.create(
            type='meeting',
            title='Follow-up Meeting',
            contact=self.contact,
            deal=self.deal,
            owner=self.user,
            scheduled_at=timezone.now() + timedelta(days=1),
            duration_minutes=60
        )

        # Verify relationships
        deal_activities = Activity.objects.filter(deal=self.deal)
        self.assertEqual(deal_activities.count(), 2)

        # Test deal relationship back to activities
        self.assertEqual(self.deal.activities.count(), 2)
        self.assertIn(activity1, self.deal.activities.all())
        self.assertIn(activity2, self.deal.activities.all())

    def test_activity_creation_with_deal_stage_changes(self):
        """
        RED: Test that activities can be created when deal stages change
        This should drive the deal workflow logic
        """
        from crm.apps.activities.models import Activity

        # Initial activity
        initial_activity = Activity.objects.create(
            type='call',
            title='Discovery Call',
            contact=self.contact,
            deal=self.deal,
            owner=self.user,
            scheduled_at=timezone.now() + timedelta(hours=2),
            duration_minutes=45
        )

        # Change deal stage
        self.deal.stage = 'proposal'
        self.deal.save()

        # Create follow-up activity
        followup_activity = Activity.objects.create(
            type='meeting',
            title='Proposal Meeting',
            contact=self.contact,
            deal=self.deal,
            owner=self.user,
            scheduled_at=timezone.now() + timedelta(days=2),
            duration_minutes=90
        )

        # Verify both activities exist and are related correctly
        activities = Activity.objects.filter(deal=self.deal)
        self.assertEqual(activities.count(), 2)

        # Verify deal stage change was tracked
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.stage, 'proposal')


class TestFullWorkflowIntegration(TransactionTestCase):
    """
    Test complete CRM workflow from user creation to deal management
    Following SOLID principles - each test has single responsibility
    """

    def test_complete_sales_workflow(self):
        """
        RED: Test complete sales workflow
        User -> Contact -> Deal -> Activities -> Deal Closed
        This should drive the complete integration
        """
        from crm.apps.contacts.models import Contact
        from crm.apps.deals.models import Deal
        from crm.apps.activities.models import Activity

        # Step 1: Create sales user
        sales_user = User.objects.create_user(
            email='sales@company.com',
            first_name='Sales',
            last_name='Rep',
            password='salespass123'
        )

        # Step 2: Create new contact
        contact = Contact.objects.create(
            first_name='Enterprise',
            last_name='Client',
            email='enterprise@client.com',
            company='Enterprise Corp',
            phone='+1-555-555-0123',
            owner=sales_user
        )

        # Step 3: Create initial deal
        deal = Deal.objects.create(
            title='Enterprise Software License',
            value=250000.00,
            stage='prospect',
            expected_close_date=timezone.now() + timedelta(days=90),
            contact=contact,
            owner=sales_user
        )

        # Step 4: Create discovery activity
        discovery_activity = Activity.objects.create(
            type='call',
            title='Discovery Call',
            description='Initial requirements gathering',
            contact=contact,
            deal=deal,
            owner=sales_user,
            scheduled_at=timezone.now() + timedelta(hours=3),
            duration_minutes=60
        )

        # Step 5: Progress deal through pipeline
        deal.stage = 'qualified'
        deal.save()

        # Step 6: Create proposal activity
        proposal_activity = Activity.objects.create(
            type='meeting',
            title='Demo and Proposal',
            description='Product demonstration and proposal review',
            contact=contact,
            deal=deal,
            owner=sales_user,
            scheduled_at=timezone.now() + timedelta(days=7),
            duration_minutes=120
        )

        # Step 7: Close deal as won
        deal.close_as_won()

        # Verify complete workflow
        self.assertEqual(sales_user.contacts.count(), 1)
        self.assertEqual(contact.deals.count(), 1)
        self.assertEqual(deal.activities.count(), 2)
        self.assertTrue(deal.is_won)
        self.assertEqual(contact.get_total_deal_value(), 250000.00)
        self.assertEqual(contact.get_deals_count(), 1)