from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from django.conf import settings
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate PWA icons from the logo.png source image"

    PWA_SIZES = [16, 32, 64, 72, 96, 128, 144, 152, 180, 192, 384, 512]

    @staticmethod
    def generate_image(source: Image.Image, size: int, output_dir: Path, image_type: str = "png"):
        resized = source.resize((size, size), Image.Resampling.LANCZOS)
        output_path = output_dir / f"{size}.{image_type}"
        resized.save(output_path)
        return output_path

    def handle(self, *args, **options):
        static_root = settings.STATICFILES_DIRS[0]
        source_path = static_root / "img" / "logo.png"
        output_dir = static_root / "favicon"

        if not source_path.exists():
            logger.error(f"Source image not found: {source_path}")
            return

        source = Image.open(source_path)
        generated = [self.generate_image(source=source, size=16, output_dir=static_root, image_type="ico")]
        for size in self.PWA_SIZES:
            generated.append(self.generate_image(source=source, size=size, output_dir=output_dir))

        logger.info(f"Generated {len(generated)} icons in {output_dir}:")
        for icon in generated:
            self.stdout.write(f"  {icon.name}")
