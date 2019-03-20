from unittest import mock

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from freezegun import freeze_time

from signals.apps.email_integrations.integrations import handhaving_or_oost
from signals.apps.signals.models import STADSDEEL_NOORD, STADSDEEL_OOST
from tests.apps.signals.factories import SignalFactory


@override_settings(EMAIL_HANDHAVING_OR_OOST_INTEGRATION_ADDRESS='test@test.com')
class TestIntegrationHandhavingOROost(TestCase):

    @freeze_time('2018-09-05 23:00:00')  # Outside business hour
    def test_send_mail_integration_test(self):
        """Integration test for `send_mail` function."""
        signal = SignalFactory.create(
            category_assignment__category__parent__name='Overlast in de openbare ruimte',
            category_assignment__category__name='Parkeeroverlast',
            location__stadsdeel=STADSDEEL_OOST)

        number_of_messages = handhaving_or_oost.send_mail(signal)

        self.assertEqual(number_of_messages, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Nieuwe melding op meldingen.amsterdam.nl')

    @mock.patch('signals.apps.email_integrations.integrations.handhaving_or_oost.django_send_mail',
                return_value=1, autospec=True)
    @mock.patch('signals.apps.email_integrations.integrations.handhaving_or_oost.'
                'create_default_notification_message', autospec=True)
    @mock.patch('signals.apps.email_integrations.integrations.handhaving_or_oost.'
                'is_signal_applicable', return_value=True, autospec=True)
    def test_send_mail(
            self,
            mocked_is_signal_applicable,
            mocked_create_default_notification_message,
            mocked_django_send_mail):
        # Setting up mocked notification message.
        mocked_message = mock.Mock()
        mocked_create_default_notification_message.return_value = mocked_message

        signal = SignalFactory.create()
        number_of_messages = handhaving_or_oost.send_mail(signal)

        self.assertEqual(number_of_messages, 1)
        mocked_is_signal_applicable.assert_called_once_with(signal)
        mocked_django_send_mail.assert_called_once_with(
            subject='Nieuwe melding op meldingen.amsterdam.nl',
            message=mocked_message,
            from_email=settings.NOREPLY,
            recipient_list=(settings.EMAIL_HANDHAVING_OR_OOST_INTEGRATION_ADDRESS, ))

    @mock.patch('signals.apps.email_integrations.integrations.handhaving_or_oost.django_send_mail',
                autospec=True)
    @mock.patch('signals.apps.email_integrations.integrations.handhaving_or_oost.'
                'is_signal_applicable', return_value=False, autospec=True)
    def test_send_mail_not_applicable(self, mocked_is_signal_applicable, mocked_django_send_mail):
        signal = SignalFactory.create()

        number_of_messages = handhaving_or_oost.send_mail(signal)

        self.assertEqual(number_of_messages, 0)
        mocked_is_signal_applicable.assert_called_once_with(signal)
        mocked_django_send_mail.assert_not_called()

    @mock.patch('signals.apps.email_integrations.integrations.handhaving_or_oost.is_business_hour',
                return_value=False, autospec=True)
    def test_is_signal_applicable_true(self, mocked_is_business_hour):
        signal = SignalFactory.create(
            category_assignment__category__parent__name='Overlast in de openbare ruimte',
            category_assignment__category__name='Fietswrak',
            location__stadsdeel=STADSDEEL_OOST)

        result = handhaving_or_oost.is_signal_applicable(signal)

        self.assertEqual(result, True)

    @mock.patch('signals.apps.email_integrations.integrations.handhaving_or_oost.is_business_hour',
                return_value=True, autospec=True)
    def test_is_signal_applicable_is_business_hour(self, mocked_is_business_hour):
        signal = SignalFactory.create(
            category_assignment__category__parent__name='Overlast in de openbare ruimte',
            category_assignment__category__name='Fietswrak',
            location__stadsdeel=STADSDEEL_OOST)

        result = handhaving_or_oost.is_signal_applicable(signal)

        self.assertEqual(result, False)

    @mock.patch('signals.apps.email_integrations.integrations.handhaving_or_oost.is_business_hour',
                return_value=False, autospec=True)
    def test_is_signal_applicable_outside_category_in_stadsdeel_oost(self, mocked_is_business_hour):
        signal = SignalFactory.create(
            category_assignment__category__parent__name='Some other main category',
            category_assignment__category__name='Some other category',
            location__stadsdeel=STADSDEEL_OOST)

        result = handhaving_or_oost.is_signal_applicable(signal)

        self.assertEqual(result, False)

    @mock.patch('signals.apps.email_integrations.integrations.handhaving_or_oost.is_business_hour',
                return_value=False, autospec=True)
    def test_is_signal_applicable_in_category_outside_stadsdeel_oost(self, mocked_is_business_hour):
        signal = SignalFactory.create(
            category_assignment__category__parent__name='Overlast in de openbare ruimte',
            category_assignment__category__name='Fietswrak',
            location__stadsdeel=STADSDEEL_NOORD)

        result = handhaving_or_oost.is_signal_applicable(signal)

        self.assertEqual(result, False)
