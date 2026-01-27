from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.teams.models import Team
from apps.campaigns.models import CampaignTemplate

User = get_user_model()

class LoadDemoTests(TestCase):
    def test_command_runs(self):
        call_command("loaddemo", "--skip-genbank")

    def test_creates_expected_users(self):
        call_command("loaddemo", "--skip-genbank")

        self.assertTrue(User.objects.filter(email="admin@insillyclo.com").exists())
        self.assertTrue(User.objects.filter(email="researcher1@insillyclo.com").exists())
        self.assertTrue(User.objects.filter(email="researcher2@insillyclo.com").exists())
        self.assertTrue(User.objects.filter(email="user1@example.com").exists())
        self.assertTrue(User.objects.filter(email="user2@example.com").exists())
        self.assertTrue(User.objects.filter(email="user3@example.com").exists())

    def test_idempotent(self):
        call_command("loaddemo", "--skip-genbank")
        call_command("loaddemo", "--skip-genbank")

        self.assertEqual(User.objects.filter(email="admin@insillyclo.com").count(), 1)
        self.assertEqual(User.objects.filter(email="researcher1@insillyclo.com").count(), 1)
        self.assertEqual(User.objects.filter(email="user1@example.com").count(), 1)

    def test_passwords_are_hashed(self):
        call_command("loaddemo", "--skip-genbank")
        admin = User.objects.get(email="admin@insillyclo.com")
        self.assertNotEqual(admin.password, "admin123")
        self.assertTrue(admin.check_password("admin123"))


class LoadDemoTeamsTemplatesTests(TestCase):
    def test_teams_created(self):
        call_command("loaddemo", "--skip-genbank")
        self.assertTrue(Team.objects.filter(name="Équipe Plasmides").exists())

    def test_templates_created(self):
        call_command("loaddemo", "--skip-genbank")
        self.assertTrue(CampaignTemplate.objects.filter(name="Template YTK Standard").exists())
