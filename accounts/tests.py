"""Rollar va boshqaruv buyruqlari testlari."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import Profile
from accounts.permissions import has_role, user_role
from accounts.roles import GROUP_ADMIN, GROUP_MANAGER, GROUP_SUPPORT, ensure_roles

User = get_user_model()


class SetupRolesCommandTests(TestCase):
    """`setup_roles` buyrug'i — serverda har joylashtirishda ishlaydi.

    Ilgari bu buyruq sinalmagan edi va Support roli qo'shilganda
    `manager, admin_group = ensure_roles()` qatori ishlamay qoldi:
    `ValueError: too many values to unpack`. Railway'da butun joylashtirish
    shu sababdan yiqilgandi.
    """

    def test_buyruq_ishlaydi(self):
        out = StringIO()
        call_command('setup_roles', stdout=out)
        self.assertIn('tayyor', out.getvalue())

    def test_uchala_guruh_yaratiladi(self):
        call_command('setup_roles', stdout=StringIO())
        for name in (GROUP_SUPPORT, GROUP_MANAGER, GROUP_ADMIN):
            with self.subTest(group=name):
                self.assertTrue(Group.objects.filter(name=name).exists())

    def test_qayta_ishga_tushirsa_takrorlanmaydi(self):
        for _ in range(3):
            call_command('setup_roles', stdout=StringIO())
        for name in (GROUP_SUPPORT, GROUP_MANAGER, GROUP_ADMIN):
            with self.subTest(group=name):
                self.assertEqual(Group.objects.filter(name=name).count(), 1)

    def test_har_bir_rol_uchun_guruh_bor(self):
        """Yangi rol qo'shilsa, unga guruh ham qo'shilganini tekshiradi."""
        from accounts.signals import GROUP_BY_ROLE
        for role, _label in Profile.ROLES:
            with self.subTest(role=role):
                self.assertIn(role, GROUP_BY_ROLE, 'rolga guruh biriktirilmagan')

    def test_ensure_roles_har_bir_guruhni_qaytaradi(self):
        groups = ensure_roles()
        self.assertEqual(len(groups), len(Profile.ROLES))
        names = {group.name for group in groups}
        self.assertEqual(names, {GROUP_SUPPORT, GROUP_MANAGER, GROUP_ADMIN})


@override_settings(AUTO_TRANSLATE=False)
class RoleAssignmentTests(TestCase):
    """Profil yaratilganda foydalanuvchi mos guruhga tushishi kerak."""

    def make(self, username, role):
        user = User.objects.create_user(username, password='Parol12345!')
        Profile.objects.create(user=user, role=role)
        user.refresh_from_db()
        return user

    def test_rol_guruhga_biriktiriladi(self):
        cases = {
            Profile.ROLE_SUPPORT: GROUP_SUPPORT,
            Profile.ROLE_MANAGER: GROUP_MANAGER,
            Profile.ROLE_ADMIN: GROUP_ADMIN,
        }
        for role, group_name in cases.items():
            with self.subTest(role=role):
                user = self.make('u_%s' % role, role)
                self.assertTrue(user.groups.filter(name=group_name).exists())

    def test_profil_yaratilganda_xodim_boladi(self):
        user = self.make('xodim', Profile.ROLE_SUPPORT)
        self.assertTrue(user.is_staff)

    def test_rol_ozgarsa_guruh_ham_ozgaradi(self):
        user = self.make('almashadi', Profile.ROLE_SUPPORT)
        user.profile.role = Profile.ROLE_ADMIN
        user.profile.save()
        user.refresh_from_db()
        self.assertTrue(user.groups.filter(name=GROUP_ADMIN).exists())
        self.assertFalse(user.groups.filter(name=GROUP_SUPPORT).exists())

    def test_profil_ochirilsa_ruxsat_qaytariladi(self):
        user = self.make('ochiriladi', Profile.ROLE_MANAGER)
        user.profile.delete()
        user.refresh_from_db()
        self.assertFalse(user.is_staff)

    def test_superuser_doim_admin(self):
        boss = User.objects.create_superuser('boss', 'boss@example.com', 'Parol12345!')
        self.assertEqual(user_role(boss), 'admin')
        self.assertTrue(has_role(boss, 'admin'))

    def test_profilsiz_foydalanuvchida_rol_yoq(self):
        outsider = User.objects.create_user('begona', password='Parol12345!')
        self.assertIsNone(user_role(outsider))


class ManagementCommandsSmokeTests(TestCase):
    """Har bir boshqaruv buyrug'i hech bo'lmasa ishga tusha olishi kerak.

    Buyruqlar server tomonida ishlaydi va sinalmasa xatosi faqat
    joylashtirishda bilinadi.
    """

    def test_setup_roles_xatosiz(self):
        call_command('setup_roles', stdout=StringIO())

    def test_translate_content_missing_rejimi(self):
        """Tarmoqqa chiqmasin — `AUTO_TRANSLATE=False` bilan."""
        with override_settings(AUTO_TRANSLATE=False):
            call_command('translate_content', '--missing', stdout=StringIO(), stderr=StringIO())


class EnsureAdminCommandTests(TestCase):
    """`ensure_admin` — serverda administrator hisobini yaratadi."""

    def run_cmd(self, **env):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, env, clear=False):
            out = StringIO()
            call_command('ensure_admin', stdout=out)
            return out.getvalue()

    def test_ozgaruvchilarsiz_hech_narsa_qilmaydi(self):
        """Pre-deploy'da doim qolgani uchun bo'sh holatda xato bermasligi shart."""
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ADMIN_USERNAME', None)
            os.environ.pop('ADMIN_PASSWORD', None)
            out = StringIO()
            call_command('ensure_admin', stdout=out)
        self.assertIn('o‘tkazib yuborildi', out.getvalue())
        self.assertEqual(User.objects.count(), 0)

    def test_hisob_yaratiladi(self):
        self.run_cmd(ADMIN_USERNAME='Sevara', ADMIN_PASSWORD='juda-kuchli-parol-123')
        user = User.objects.get(username='Sevara')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password('juda-kuchli-parol-123'))

    def test_admin_roli_beriladi(self):
        self.run_cmd(ADMIN_USERNAME='Sevara', ADMIN_PASSWORD='juda-kuchli-parol-123')
        user = User.objects.get(username='Sevara')
        self.assertEqual(user.profile.role, Profile.ROLE_ADMIN)
        self.assertTrue(has_role(user, 'admin'))

    def test_qayta_ishga_tushirsa_parol_yangilanadi(self):
        self.run_cmd(ADMIN_USERNAME='Sevara', ADMIN_PASSWORD='birinchi-parol-123')
        self.run_cmd(ADMIN_USERNAME='Sevara', ADMIN_PASSWORD='ikkinchi-parol-456')
        self.assertEqual(User.objects.filter(username='Sevara').count(), 1)
        self.assertTrue(User.objects.get(username='Sevara').check_password('ikkinchi-parol-456'))

    def test_qisqa_parolda_ogohlantiradi(self):
        out = self.run_cmd(ADMIN_USERNAME='Sevara', ADMIN_PASSWORD='qisqa123')
        self.assertIn('parol qisqa', out)

    def test_panelga_kira_oladi(self):
        self.run_cmd(ADMIN_USERNAME='Sevara', ADMIN_PASSWORD='juda-kuchli-parol-123')
        ok = self.client.login(username='Sevara', password='juda-kuchli-parol-123')
        self.assertTrue(ok, 'yaratilgan hisob bilan kirib bo‘lmadi')
