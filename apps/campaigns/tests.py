from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import CampaignTemplate


class TemplateCreationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')

    def test_create_template_minimal(self):
        self.client.login(username='tester', password='pass')
        data = {
            'name': 'my_template',
            'template_type': 'simple',
            'restriction_enzyme': 'BsaI',
            'separator': '.',
            # download_format is not sent by the form; should not be required
        }
        resp = self.client.post(reverse('campaigns:create_template'), data)
        # should redirect to template list
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CampaignTemplate.objects.filter(name='my_template').exists())

    def test_duplicate_name_fails(self):
        # create an existing template
        CampaignTemplate.objects.create(name='existing', template_type='simple', restriction_enzyme='BsaI', separator='.', owner=self.user)
        self.client.login(username='tester', password='pass')
        data = {
            'name': 'existing',
            'template_type': 'simple',
            'restriction_enzyme': 'BsaI',
            'separator': '.',
        }
        resp = self.client.post(reverse('campaigns:create_template'), data)
        # Should render the form again (status 200) with the validation error
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'A template with this name already exists.')
        self.assertEqual(CampaignTemplate.objects.filter(name='existing').count(), 1)

