from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate VAPID keys for web push notifications"

    def handle(self, *args: list, **options: dict) -> None:
        from webpush import VAPID

        keys = VAPID.generate_keys()
        private_key = keys[0].decode()
        public_key = keys[1].decode()
        public_key_b64 = keys[2]

        self.stdout.write(
            self.style.SUCCESS(
                f"\nVAPID Keys generated successfully!\n\n"
                f"Add these to your settings.py or environment variables:\n\n"
                f"VAPID_PUBLIC_KEY = '''{public_key}'''\n"
                f"VAPID_PRIVATE_KEY = '''{private_key}'''\n\n"
                f"Or add to .env file:\n"
                f"VAPID_PUBLIC_KEY={public_key_b64}\n"
                f"VAPID_PRIVATE_KEY=<PEM format key - see above>\n",
            ),
        )
