from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .models import Correspondence, CorrespondenceEntry


class CorrespondenceUploadConflictTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            password="password",
            email="test@example.com",
        )
        self.client.login(username="testuser", password="password")

        self.corr = Correspondence.objects.create(
            name="Test correspondence",
            owner=self.user,   
            is_public=False,
        )

    def test_conflict_same_name_multiple_identifiers(self):
        """
        même nom -> identifiants différents
        """
        csv_content = (
            "pYTK045,Venus,plasmid\n"
            "pYTK046,Venus,plasmid\n"
        )

        file = SimpleUploadedFile(
            "conflict.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        url = reverse("correspondences:upload", kwargs={"pk": self.corr.pk})
        response = self.client.post(
            url,
            {
                "file": file,
                "replace_existing": False,
            },
            follow=True,
        )

        # 1) Page can't change (status 200)
        self.assertEqual(response.status_code, 200)

        # 2) No entry created
        self.assertEqual(
            CorrespondenceEntry.objects.filter(correspondence=self.corr).count(),
            0,
        )

        # 3) Conflict message shown
        self.assertContains(response, "Conflict:")
