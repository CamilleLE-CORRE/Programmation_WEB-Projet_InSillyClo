from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Team

User = get_user_model()


# =====================
# MODELE
# =====================
# Lorsqu’une équipe est créée, son propriétaire (owner) 
# doit automatiquement être membre de l’équipe.
class TeamModelTests(TestCase):
    def test_owner_is_added_as_member_on_creation(self):
        owner = User.objects.create_user(email="owner@example.com", password="pass")
        team = Team.objects.create(name="Test Team", owner=owner)

        self.assertEqual(team.owner, owner)
        self.assertTrue(team.members.filter(pk=owner.pk).exists())


# =====================
# LISTE DES TEAMS
# =====================
# Un utilisateur ne doit voir que les équipes dont il est membre.
class TeamListViewTests(TestCase):
    def setUp(self): # mise en place du scénario
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.other = User.objects.create_user(email="other@example.com", password="pass")
        self.team1 = Team.objects.create(name="Team 1", owner=self.user)
        self.team2 = Team.objects.create(name="Team 2", owner=self.other)

    def test_user_sees_only_his_teams(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("teams:teams"))

        teams = response.context["teams"]
        self.assertIn(self.team1, teams)
        self.assertNotIn(self.team2, teams)


# =====================
# CREATION
# =====================
# Lorsqu’une équipe est créée, le propriétaire doit être défini
class TeamCreateViewTests(TestCase):
    def test_create_team_sets_owner_and_membership(self):
        user = User.objects.create_user(email="user@example.com", password="pass")
        self.client.force_login(user)

        self.client.post(reverse("teams:create_team"), {"name": "New Team"})
        team = Team.objects.get(name="New Team")

        self.assertEqual(team.owner, user)
        self.assertTrue(team.members.filter(pk=user.pk).exists())


# =====================
# DETAIL + PERMISSIONS
# =====================
# Seuls les membres peuvent accéder à la vue détail.
# Le contexte doit indiquer si l’utilisateur est le propriétaire.
class TeamDetailViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass")
        self.member = User.objects.create_user(email="member@example.com", password="pass")
        self.outsider = User.objects.create_user(email="outsider@example.com", password="pass")

        self.team = Team.objects.create(name="Test Team", owner=self.owner)
        self.team.members.add(self.member)

    def test_only_members_can_access_detail(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("teams:team_detail", args=[self.team.pk]))
        self.assertEqual(response.status_code, 404)

    def test_owner_flag_is_correct(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("teams:team_detail", args=[self.team.pk]))
        self.assertTrue(response.context["is_owner"])

        self.client.force_login(self.member)
        response = self.client.get(reverse("teams:team_detail", args=[self.team.pk]))
        self.assertFalse(response.context["is_owner"])


# =====================
# AJOUT DE MEMBRE
# =====================
# Seul le propriétaire peut ajouter des membres.
# L’ajout avec un email invalide ne doit pas modifier l’équipe.
class TeamAddMemberTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass")
        self.new_user = User.objects.create_user(email="new@example.com", password="pass")
        self.team = Team.objects.create(name="Test Team", owner=self.owner)

    def test_owner_can_add_member(self):
        self.client.force_login(self.owner)
        self.client.post(
            reverse("teams:add_member", args=[self.team.pk]),
            {"email": "new@example.com"},
        )

        self.assertTrue(self.team.members.filter(pk=self.new_user.pk).exists())

    def test_invalid_email_does_not_modify_team(self):
        self.client.force_login(self.owner)
        self.client.post(
            reverse("teams:add_member", args=[self.team.pk]),
            {"email": "unknown@example.com"},
        )

        self.assertEqual(self.team.members.count(), 1)  # owner only


# =====================
# TRANSFERT OWNERSHIP
# =====================
# Seul le propriétaire peut transférer la propriété.
# Le nouveau propriétaire doit être un membre de l’équipe.
class TeamTransferOwnerTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass")
        self.member = User.objects.create_user(email="member@example.com", password="pass")

        self.team = Team.objects.create(name="Test Team", owner=self.owner)
        self.team.members.add(self.member)

    def test_owner_can_transfer_to_member(self):
        self.client.force_login(self.owner)
        self.client.post(
            reverse("teams:transfer_owner", args=[self.team.pk]),
            {"new_owner": self.member.pk},
        )

        self.team.refresh_from_db()
        self.assertEqual(self.team.owner, self.member)


# =====================
# ADMIN
# =====================
# Seuls les utilisateurs staff peuvent accéder à la liste admin des équipes.
# La liste doit contenir toutes les équipes.
class AdminTeamViewsTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            email="staff@example.com", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.team = Team.objects.create(name="Test Team", owner=self.user)

    def test_admin_team_list_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("teams:admin_team_list"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_admin_team_list(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("teams:admin_team_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.team, response.context["teams"])
