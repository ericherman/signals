from django.contrib.auth.models import Permission
from rest_framework import status

from tests.apps.signals.factories import CategoryFactory, DepartmentFactory, ParentCategoryFactory
from tests.test import SIAReadWriteUserMixin, SignalsBaseApiTestCase


class TestPrivateDepartmentEndpoint(SIAReadWriteUserMixin, SignalsBaseApiTestCase):
    list_endpoint = '/signals/v1/private/departments/'
    detail_endpoint = '/signals/v1/private/departments/{pk}'

    def setUp(self):
        self.department_read = Permission.objects.get(
            codename='sia_department_read'
        )
        self.department_write = Permission.objects.get(
            codename='sia_department_write'
        )
        self.sia_read_write_user.user_permissions.add(self.department_read)
        self.sia_read_write_user.user_permissions.add(self.department_write)

        self.department = DepartmentFactory.create()

        self.category = ParentCategoryFactory.create()
        self.subcategory = CategoryFactory.create(parent=self.category)

    def test_get_list(self):
        self.client.force_authenticate(user=self.sia_read_write_user)

        response = self.client.get(self.list_endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['count'], 20)
        self.assertEqual(len(data['results']), 20)

    def test_get_detail(self):
        self.client.force_authenticate(user=self.sia_read_write_user)

        response = self.client.get(self.detail_endpoint.format(pk=self.department.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['name'], self.department.name)
        self.assertEqual(data['code'], self.department.code)
        self.assertEqual(data['is_intern'], self.department.is_intern)

        self.assertEqual(len(data['categories']), 0)

    def test_post(self):
        self.client.force_authenticate(user=self.sia_read_write_user)

        data = {
            'name': 'The department',
            'code': 'TDP',
            'is_intern': True,
            'categories': [
                {
                    'category_id': self.subcategory.pk,
                    'is_responsible': True
                }
            ]
        }

        response = self.client.post(
            self.list_endpoint, data=data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['name'], 'The department')
        self.assertEqual(data['code'], 'TDP')
        self.assertEqual(data['is_intern'], True)
        self.assertEqual(len(data['categories']), 1)

        self.assertTrue(data['categories'][0]['is_responsible'])
        self.assertTrue(data['categories'][0]['can_view'])
        self.assertEqual(data['categories'][0]['category']['departments'][0]['code'], 'TDP')

    def test_post_no_categories(self):
        self.client.force_authenticate(user=self.sia_read_write_user)

        data = {
            'name': 'The department',
            'code': 'TDP',
            'is_intern': True
        }

        response = self.client.post(
            self.list_endpoint, data=data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['name'], 'The department')
        self.assertEqual(data['code'], 'TDP')
        self.assertEqual(data['is_intern'], True)
        self.assertEqual(len(data['categories']), 0)

    def test_post_invalid_data(self):
        self.client.force_authenticate(user=self.sia_read_write_user)

        data = {
            'name': 'The department',
            'code': 'TDP-too-long-code',
        }

        response = self.client.post(
            self.list_endpoint, data=data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertEqual(data['code'][0],
                         'Zorg ervoor dat dit veld niet meer dan 3 karakters bevat.')

    def test_patch(self):
        self.client.force_authenticate(user=self.sia_read_write_user)

        data = {
            'name': 'A way better name than generated by the factory',
            'categories': [
                {
                    'category_id': self.subcategory.pk,
                    'is_responsible': True
                }
            ]
        }

        response = self.client.patch(
            self.detail_endpoint.format(pk=self.department.pk), data=data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['name'], 'A way better name than generated by the factory')
        self.assertEqual(data['code'], self.department.code)
        self.assertEqual(data['is_intern'], self.department.is_intern)
        self.assertTrue(data['categories'][0]['is_responsible'])
        self.assertTrue(data['categories'][0]['can_view'])
        self.assertEqual(data['categories'][0]['category']['departments'][0]['code'],
                         self.department.code)

    def test_patch_invalid_data(self):
        self.client.force_authenticate(user=self.sia_read_write_user)

        data = {
            'code': 'way too long to get accepted'  # can only be 3 characters long
        }

        response = self.client.patch(
            self.detail_endpoint.format(pk=self.department.pk), data=data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertEqual(data['code'][0],
                         'Zorg ervoor dat dit veld niet meer dan 3 karakters bevat.')

    def test_delete_method_not_allowed(self):
        self.client.force_authenticate(user=self.sia_read_write_user)

        response = self.client.delete(self.detail_endpoint.format(pk=1))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
