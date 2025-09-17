from django.contrib.auth import get_user_model
from django.test import TestCase
from django.db import IntegrityError


class UserModelTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def test_username_field_is_email(self):
        self.assertEqual(self.User.USERNAME_FIELD, "email")
        self.assertEqual(self.User.REQUIRED_FIELDS, [])

    def test_create_user_with_email_successful(self):
        email = "user@example.com"
        password = "strong-pass-123"
        user = self.User.objects.create_user(email=email, password=password)

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_email_is_normalized(self):
        email = "TEST@EXAMPLE.COM"
        user = self.User.objects.create_user(email=email, password="pass123")

        # BaseUserManager.normalize_email lowercases the domain part
        self.assertEqual(user.email, "TEST@example.com")

    def test_email_required(self):
        with self.assertRaisesMessage(ValueError, "The given email must be set"):
            self.User.objects.create_user(email=None, password="pass123")

    def test_email_unique(self):
        email = "unique@example.com"
        self.User.objects.create_user(email=email, password="pass123")
        with self.assertRaises(IntegrityError):
            self.User.objects.create_user(email=email, password="another-pass")

    def test_create_superuser_flags(self):
        email = "admin@example.com"
        user = self.User.objects.create_superuser(email=email, password="admin-pass")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_with_is_staff_false_raises(self):
        with self.assertRaisesMessage(ValueError, "Superuser must have is_staff=True."):
            self.User.objects.create_superuser(
                email="admin2@example.com", password="pass123", is_staff=False
            )

    def test_create_superuser_with_is_superuser_false_raises(self):
        with self.assertRaisesMessage(
            ValueError, "Superuser must have is_superuser=True."
        ):
            self.User.objects.create_superuser(
                email="admin3@example.com", password="pass123", is_superuser=False
            )

    def test_user_str_returns_email(self):
        email = "whoami@example.com"
        user = self.User.objects.create_user(email=email, password="pass123")
        self.assertEqual(str(user), email)
