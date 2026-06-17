import base64
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Generate VAPID keypair for Web Push. Run once per environment.'

    def handle(self, *args, **options):
        try:
            from py_vapid import Vapid01
            from cryptography.hazmat.primitives import serialization
        except ImportError:
            self.stderr.write('pywebpush is not installed.')
            return

        pem_path = os.path.join(settings.BASE_DIR, 'vapid_private.pem')
        v = Vapid01()
        v.generate_keys()
        v.save_key(pem_path)

        public_key_bytes = v.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint)
        public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode().rstrip('=')

        self.stdout.write(self.style.SUCCESS('Generated {}'.format(pem_path)))
        self.stdout.write('\nAdd to your .env / .env.local:\n')
        self.stdout.write('VAPID_PRIVATE_KEY={}'.format(pem_path))
        self.stdout.write('VAPID_PUBLIC_KEY={}'.format(public_key_b64))
        self.stdout.write('VAPID_CONTACT_EMAIL=dangerous@duck.com')
