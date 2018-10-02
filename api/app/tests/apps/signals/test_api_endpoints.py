import json
import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from signals.apps.signals import workflow
from signals.apps.signals.models import (
    CategoryAssignment,
    Location,
    MainCategory,
    Priority,
    Reporter,
    Signal,
    Status
)
from tests.apps.signals import factories
from tests.apps.signals.factories import MainCategoryFactory, SubCategoryFactory
from tests.apps.users.factories import SuperUserFactory, UserFactory


class TestAPIEndpoints(APITestCase):

    def test_signals_index(self):
        response = self.client.get('/signals/')

        self.assertEqual(response.status_code, 200)


class TestAuthAPIEndpoints(APITestCase):
    endpoints = [
        '/signals/auth/signal/',
        '/signals/auth/status/',
        '/signals/auth/category/',
        '/signals/auth/location/',
        '/signals/auth/priority/',
    ]

    def setUp(self):
        self.signal = factories.SignalFactory(id=1,
                                              location__id=1,
                                              status__id=1,
                                              category_assignment__id=1,
                                              reporter__id=1,
                                              priority__id=1)

        # Forcing authentication
        user = UserFactory.create()  # Normal user without any extra permissions.
        self.client.force_authenticate(user=user)

    def test_get_lists(self):
        for url in self.endpoints:
            response = self.client.get(url)

            self.assertEqual(response.status_code, 200, 'Wrong response code for {}'.format(url))
            self.assertEqual(response['Content-Type'],
                             'application/json',
                             'Wrong Content-Type for {}'.format(url))
            self.assertIn('count', response.data, 'No count attribute in {}'.format(url))

    def test_get_lists_html(self):
        for url in self.endpoints:
            response = self.client.get('{}?format=api'.format(url))

            self.assertEqual(response.status_code, 200, 'Wrong response code for {}'.format(url))
            self.assertEqual(response['Content-Type'],
                             'text/html; charset=utf-8',
                             'Wrong Content-Type for {}'.format(url))
            self.assertIn('count', response.data, 'No count attribute in {}'.format(url))

    def test_get_detail(self):
        for endpoint in self.endpoints:
            url = f'{endpoint}1/'
            response = self.client.get(url)

            self.assertEqual(response.status_code, 200, 'Wrong response code for {}'.format(url))

    def test_delete_not_allowed(self):
        for endpoint in self.endpoints:
            url = f'{endpoint}1/'
            response = self.client.delete(url)

            self.assertEqual(response.status_code, 405, 'Wrong response code for {}'.format(url))

    def test_put_not_allowed(self):
        for endpoint in self.endpoints:
            url = f'{endpoint}1/'
            response = self.client.put(url)

            self.assertEqual(response.status_code, 405, 'Wrong response code for {}'.format(url))

    def test_patch_not_allowed(self):
        for endpoint in self.endpoints:
            url = f'{endpoint}1/'
            response = self.client.patch(url)

            self.assertEqual(response.status_code, 405, 'Wrong response code for {}'.format(url))


class TestAPIEnpointsBase(APITestCase):
    fixture_files = {
        "post_signal": "signal_post.json",
        "post_status": "status_auth_post.json",
        "post_category": "category_auth_post.json",
        "post_location": "location_auth_post.json",
    }

    def _get_fixture(self, name):
        filename = self.fixture_files[name]
        path = os.path.join(settings.BASE_DIR, 'apps', 'signals', 'fixtures', filename)

        with open(path) as fixture_file:
            postjson = json.loads(fixture_file.read())

        return postjson

    def setUp(self):
        self.signal = factories.SignalFactory.create()
        self.location = self.signal.location
        self.status = self.signal.status
        self.category_assignment = self.signal.category_assignment
        self.reporter = self.signal.reporter

        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )


class TestSignalEndpoint(TestAPIEnpointsBase):
    """Test for public endpoint `/signals/signal/`."""

    endpoint = '/signals/signal/'

    def test_get_detail(self):
        """Signal detail endpoint should only return the `Status` of the given `Signal`."""
        response = self.client.get(f'{self.endpoint}{self.signal.signal_id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('signal_id'), str(self.signal.signal_id))
        self.assertEqual(response.data.get('status').get('id'), self.signal.status.id)
        self.assertEqual(response.data.get('status').get('state'), str(self.signal.status.state))
        self.assertEqual(response.data.get('text'), None)
        self.assertEqual(response.data.get('category'), None)
        self.assertEqual(response.data.get('location'), None)
        self.assertEqual(response.data.get('reporter'), None)
        self.assertEqual(response.data.get('priority'), None)
        self.assertEqual(response.data.get('id'), None)

    def test_get_list(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 405)

    def test_delete_not_allowed(self):
        response = self.client.delete(f'{self.endpoint}1/')

        self.assertEqual(response.status_code, 405)

    def test_put_not_allowed(self):
        response = self.client.put(f'{self.endpoint}1/')

        self.assertEqual(response.status_code, 405)

    def test_patch_not_allowed(self):
        response = self.client.patch(f'{self.endpoint}1/')

        self.assertEqual(response.status_code, 405)

    def test_post_signal_with_json(self):
        postjson = self._get_fixture('post_signal')
        response = self.client.post(self.endpoint, postjson, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Signal.objects.count(), 2)
        id = response.data['id']
        s = Signal.objects.get(id=id)

        self.assertEqual(Reporter.objects.count(), 2)
        lr = Reporter.objects.filter(signal=s.id)
        self.assertEqual(lr.count(), 1)
        r = lr[0]

        self.assertEqual(r.id, s.reporter.id)

        self.assertEqual(
            Location.objects.filter(signal=s.id).count(), 1)

        self.assertEqual(
            CategoryAssignment.objects.filter(signal=s.id).count(), 1)

        self.assertEqual(
            Status.objects.filter(signal=s.id).count(), 1)

        self.assertEqual(
            CategoryAssignment.objects.filter(signal=s.id).first()._signal.id, s.id,
            "Category is missing _signal field?"
        )

        self.assertEqual(
            Status.objects.filter(signal=s.id).first()._signal.id, s.id,
            "State is missing _signal field?"
        )

        self.assertEqual(
            Reporter.objects.filter(signal=s.id).first()._signal.id, s.id,
            "Reporter is missing _signal field?"
        )

    def test_post_signal_with_multipart_and_image(self):
        data = self._get_fixture('post_signal')

        # Adding a testing image to the posting data.
        image = SimpleUploadedFile(
            'image.gif', self.small_gif, content_type='image/gif')
        data['image'] = image

        # Changing data dict structure (loaded from json file) to work with
        # multipart structure.
        for key, value in data['status'].items():
            data['status.{}'.format(key)] = value
        for key, value in data['location'].items():
            data['location.{}'.format(key)] = value
        data['location.geometrie'] = 'POINT (4.893697 52.372840)'
        for key, value in data['category'].items():
            data['category.{}'.format(key)] = value
        for key, value in data['reporter'].items():
            data['reporter.{}'.format(key)] = value

        del data['status']
        del data['status.extra_properties']
        del data['location']
        del data['location.address']
        del data['location.extra_properties']
        del data['category']
        del data['reporter']
        del data['reporter.extra_properties']
        del data['reporter.remove_at']
        del data['incident_date_end']
        del data['operational_date']

        response = self.client.post(self.endpoint, data)

        self.assertEqual(response.status_code, 201)

        signal = Signal.objects.get(id=response.json()['id'])
        self.assertTrue(signal.image)

    def test_post_signal_image(self):
        url = f'{self.endpoint}image/'
        image = SimpleUploadedFile(
            'image.gif', self.small_gif, content_type='image/gif')
        response = self.client.post(
            url, {'signal_id': self.signal.signal_id, 'image': image})

        self.assertEqual(response.status_code, 202)
        self.signal.refresh_from_db()
        self.assertTrue(self.signal.image)

    def test_post_signal_image_already_exists(self):
        self.signal.image = 'already_exists'
        self.signal.save()

        url = f'{self.endpoint}image/'
        image = SimpleUploadedFile(
            'image.gif', self.small_gif, content_type='image/gif')
        response = self.client.post(
            url, {'signal_id': self.signal.signal_id, 'image': image})

        self.assertEqual(response.status_code, 403)


class TestAuthAPIEndpointsPOST(TestAPIEnpointsBase):

    def setUp(self):
        super().setUp()

        # Forcing authentication
        superuser = SuperUserFactory.create()  # Superuser has all permissions by default.
        self.client.force_authenticate(user=superuser)

    def test_signal_post_not_allowed(self):
        endpoint = '/signals/auth/signal/'
        response = self.client.post(endpoint, {}, format='json')

        self.assertEqual(response.status_code, 405)

    def test_endpoints_forbidden(self):
        user = UserFactory.create()  # Normal user without any extra permissions.
        self.client.force_authenticate(user=user)

        # These endpoints are protected with object-level permissions. Check if we can't POST to
        # these endpoints with a normal `User` instance.
        endpoints = [
            '/signals/auth/status/',
            '/signals/auth/category/',
            '/signals/auth/location/',
            '/signals/auth/priority/',
        ]
        for endpoint in endpoints:
            response = self.client.post(endpoint, {}, format='json')
            self.assertEqual(response.status_code,
                             403,
                             'Wrong response code for {}'.format(endpoint))

    def test_post_status_all_fields(self):
        # Asserting initial state.
        self.assertEqual(self.signal.status.state, workflow.GEMELD)

        # Posting a new status change.
        url = '/signals/auth/status/'
        data = {
            '_signal': self.signal.id,
            'text': 'Changing status to "afwachting"',
            'user': 'user@example.com',
            'target_api': None,
            'state': workflow.AFWACHTING,
            'extra_properties': {},
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)

        result = response.json()
        self.signal.refresh_from_db()
        self.assertEqual(self.signal.status.text, result['text'])
        self.assertEqual(self.signal.status.user, result['user'])
        self.assertEqual(self.signal.status.state, result['state'])

    def test_post_status_minimal_fiels(self):
        # Asserting initial state.
        self.assertEqual(self.signal.status.state, workflow.GEMELD)

        # Posting a new status change.
        url = '/signals/auth/status/'
        data = {
            '_signal': self.signal.id,
            'state': workflow.AFWACHTING,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)

        self.signal.refresh_from_db()
        result = response.json()
        self.assertEqual(self.signal.status.state, result['state'])

    def test_post_status_invalid(self):
        # Prepare current state.
        self.signal.status.state = workflow.VERZONDEN
        self.signal.status.save()

        # Post an unallowed status change from the API.
        url = '/signals/auth/status/'
        data = {
            '_signal': self.signal.id,
            'state': workflow.TE_VERZENDEN,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 400)

        result = response.json()
        self.assertIn('state', result)
        self.assertIn('target_api', result)

    def test_post_location(self):
        """We only create new location items"""
        url = "/signals/auth/location/"
        postjson = self._get_fixture('post_location')
        postjson['_signal'] = self.signal.id
        response = self.client.post(url, postjson, format='json')
        result = response.json()
        self.assertEqual(response.status_code, 201)
        self.signal.refresh_from_db()
        # check that current location of signal is now this one
        self.assertEqual(self.signal.location.id, result['id'])

    def test_post_category(self):
        sub_category_name = 'Overlast op het water - snel varen'
        sub_category = SubCategoryFactory.create(name=sub_category_name,
                                                 main_category__name='Overlast op het water')

        # Asserting that we don't change the sub category to the same value the signal object
        # already has.
        self.assertNotEqual(self.signal.category_assignment.sub_category.name, sub_category_name)

        url = '/signals/auth/category/'
        postjson = {
            '_signal': self.signal.id,
            'sub_category': '/signals/v1/public/terms/categories/{}/sub_categories/{}'.format(
                sub_category.main_category.slug, sub_category.slug),
        }
        response = self.client.post(url, postjson, format='json')
        self.assertEqual(response.status_code, 201)

        result = response.json()
        self.assertEqual(result['sub'], sub_category_name)

        self.signal.refresh_from_db()
        self.assertEqual(self.signal.category_assignment.sub_category, sub_category)

    def test_post_category_backwards_compatibility_style(self):
        """
        Note, this is a backwards compatibility test for changing the category "old-style" posting.
        Implementation and test should be removed after the FE is updated to "new-style" of changing
        categories.
        """
        sub_category_name = 'Overlast op het water - snel varen'
        SubCategoryFactory.create(name=sub_category_name,
                                  main_category__name='Overlast op het water')

        # Asserting that we don't change the sub category to the same value the signal object
        # already has.
        self.assertNotEqual(self.signal.category_assignment.sub_category.name, sub_category_name)

        url = '/signals/auth/category/'
        postjson = {
            '_signal': self.signal.id,
            'main': 'Overlast op het water',
            'sub': sub_category_name,
        }
        response = self.client.post(url, postjson, format='json')
        self.assertEqual(response.status_code, 201)

        result = response.json()
        self.assertEqual(result['sub'], sub_category_name)

        self.signal.refresh_from_db()
        self.assertEqual(self.signal.category_assignment.sub_category.name, sub_category_name)

    def test_post_priority(self):
        url = '/signals/auth/priority/'
        data = {
            '_signal': self.signal.id,
            'priority': Priority.PRIORITY_HIGH,
        }
        response = self.client.post(url, data, format='json')
        result = response.json()

        self.assertEqual(response.status_code, 201)

        self.signal.refresh_from_db()
        self.assertEqual(self.signal.priority.id, result['id'])
        self.assertEqual(self.signal.priority.priority, Priority.PRIORITY_HIGH)


class TestCategoryTermsEndpoints(APITestCase):
    fixtures = ['categories.json', ]

    def test_category_list(self):
        # Asserting that we've 9 `MainCategory` objects loaded from the json fixture.
        self.assertEqual(MainCategory.objects.count(), 9)

        url = '/signals/v1/public/terms/categories'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data['results']), 9)

    def test_category_detail(self):
        # Asserting that we've 13 sub categories for our main category "Afval".
        main_category = MainCategoryFactory.create(name='Afval')
        self.assertEqual(main_category.sub_categories.count(), 13)

        url = '/signals/v1/public/terms/categories/{slug}'.format(slug=main_category.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['name'], 'Afval')
        self.assertEqual(len(data['sub_categories']), 13)

    def test_sub_category_detail(self):
        sub_category = SubCategoryFactory.create(name='Grofvuil', main_category__name='Afval')

        url = '/signals/v1/public/terms/categories/{slug}/sub_categories/{sub_slug}'.format(
            slug=sub_category.main_category.slug,
            sub_slug=sub_category.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['name'], 'Grofvuil')
