"""Create a hosting administrator without an interactive console."""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
    UserAttributeSimilarityValidator,
    validate_password,
)
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create an admin from DJANGO_SUPERUSER_* secrets; never modify existing users.'

    def handle(self, *args, **options):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip().lower()
        name = os.environ.get('DJANGO_SUPERUSER_NAME', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
        if not any((email, name, password)):
            return
        if not all((email, name, password)):
            self.stderr.write('Admin bootstrap skipped: set EMAIL, NAME and PASSWORD secrets together.')
            return

        User = get_user_model()
        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            self.report_existing(existing)
            return

        user = User(email=email, name=name, role='admin')
        try:
            validate_password(password, user, password_validators=[
                MinimumLengthValidator(12), CommonPasswordValidator(),
                NumericPasswordValidator(),
                UserAttributeSimilarityValidator(user_attributes=('name', 'email')),
            ])
            user.set_password(password)
            user.full_clean(validate_unique=False)
        except ValidationError:
            # Never log input values or validator messages that may include them.
            self.stderr.write(
                'Admin bootstrap skipped: check email, name (max 100 characters), '
                'and password (at least 12 characters, not common, numeric or similar to user details).'
            )
            return

        # The unique email constraint also protects concurrent starts.
        existing, created = User.objects.get_or_create(
            email=email, defaults={'name': name, 'role': 'admin', 'password': user.password},
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Admin created. Remove DJANGO_SUPERUSER_* secrets after login.'))
        else:
            self.report_existing(existing)

    def report_existing(self, user):
        if user.is_staff:
            self.stdout.write('Admin already exists; account and password unchanged.')
        else:
            self.stderr.write('Admin bootstrap skipped: email belongs to a regular user. Use a new email.')
