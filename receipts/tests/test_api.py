from django import test
from django import urls

from receipts.tests import factories


class ReceiptApiTest(test.TestCase):
    url = urls.reverse_lazy('api:receipts')

    def setUp(self):
        self.user = factories.make_user()
        self.other = factories.make_user()
        self.mine = [factories.make_receipt(self.user) for _ in range(3)]
        self.foreign = factories.make_receipt(self.other)
        self.client.force_login(self.user)

    def ids(self, response):
        return {item['id'] for item in response.json()['results']}

    def test_anonymous_gets_401_json(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertIn('detail', response.json())

    def test_returns_only_own_receipts(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ids(response), {r.pk for r in self.mine})
        self.assertEqual(response.json()['count'], 3)

    def test_no_parameter_leaks_foreign_receipts(self):
        attempts = [
            {'user': self.other.pk},
            {'user_id': self.other.pk},
            {'ids': str(self.foreign.pk)},
            {'ids': f'{self.foreign.pk},{self.mine[0].pk}'},
            {'id': self.foreign.pk},
            {'sort': 'user'},
            {'page_size': 100},
        ]
        for params in attempts:
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                if response.status_code == 200:
                    self.assertNotIn(self.foreign.pk, self.ids(response))

    def test_ids_filter_returns_intersection_with_own(self):
        response = self.client.get(
            self.url, {'ids': f'{self.foreign.pk},{self.mine[0].pk}'}
        )
        self.assertEqual(self.ids(response), {self.mine[0].pk})

    def test_payload_shape(self):
        item = self.client.get(self.url).json()['results'][0]
        self.assertEqual(
            set(item),
            {
                'id',
                'fn',
                'fd',
                'fp',
                'purchased_at',
                'amount',
                'status',
                'status_display',
                'rejection_reason',
                'info',
                'has_photo',
                'photo_url',
                'registered_at',
                'updated_at',
            },
        )
        self.assertEqual(item['amount'], '1500.00')

    def test_status_filter_and_validation(self):
        self.mine[0].status = 'accepted'
        self.mine[0].save()
        response = self.client.get(self.url, {'status': 'accepted'})
        self.assertEqual(self.ids(response), {self.mine[0].pk})
        bad = [
            {'status': 'won'},
            {'page': 'x'},
            {'page': '0'},
            {'page_size': '101'},
            {'ids': '1,a'},
        ]
        for params in bad:
            with self.subTest(params=params):
                self.assertEqual(
                    self.client.get(self.url, params).status_code, 400
                )

    def test_pagination(self):
        response = self.client.get(self.url, {'page_size': 2, 'page': 2})
        body = response.json()
        self.assertEqual((body['num_pages'], len(body['results'])), (2, 1))
        response = self.client.get(self.url, {'page': 5})
        self.assertEqual(response.status_code, 404)

    def test_etag_not_modified_until_status_changes(self):
        first = self.client.get(self.url)
        etag = first['ETag']
        self.assertEqual(first['Cache-Control'], 'private, no-cache')
        cached = self.client.get(self.url, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(cached.status_code, 304)
        self.mine[0].status = 'accepted'
        self.mine[0].save()
        fresh = self.client.get(self.url, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(fresh.status_code, 200)
        self.assertNotEqual(fresh['ETag'], etag)

    def test_etag_differs_between_users(self):
        etag = self.client.get(self.url)['ETag']
        self.client.force_login(self.other)
        response = self.client.get(self.url, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(response.status_code, 200)

    def test_only_get(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)
