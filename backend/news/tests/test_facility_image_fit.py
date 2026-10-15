import io
from copy import deepcopy

from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image, ImageDraw

from news.models import ContentImage, FacilityImage
from news.tests import test_branches as helpers


class FacilityImageFitTests(TestCase):
    setUp = helpers.BranchTests.setUp
    branch = helpers.BranchTests.branch
    publish = helpers.BranchTests.publish

    def marked_image(self, size, name):
        image = Image.new("RGB", size, "#ecf1f4")
        draw = ImageDraw.Draw(image)
        w, h = size
        for box, color in [
            ((0, 0, w - 1, 60), "#e34234"),
            ((0, h - 61, w - 1, h - 1), "#3478e3"),
            ((0, 61, 60, h - 62), "#22a667"),
            ((w - 61, 61, w - 1, h - 62), "#f4b942"),
        ]:
            draw.rectangle(box, fill=color)
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        return ContentImage.objects.create(
            title=name,
            file=SimpleUploadedFile(name + ".png", buffer.getvalue(), "image/png"),
        )

    def test_public_renditions_keep_full_edges_ratio_and_saved_positions(self):
        sizes = [(900, 1800), (1800, 900), (1800, 1800)]
        images = [self.marked_image(size, str(i)) for i, size in enumerate(sizes)]
        branch = self.branch()
        branch.facilities = [
            FacilityImage(image=image, sort_order=i, position_x=10, position_y=90)
            for i, image in enumerate(images)
        ]
        self.publish(branch)
        original_revision = deepcopy(branch.live_revision.content)
        for route in ["/", "/branches/"]:
            soup = BeautifulSoup(self.client.get(route).content, "html.parser")
            photos = soup.select("#branch-main [data-gallery-slide] img")
            self.assertEqual(len(photos), 3)
            for photo, source, size in zip(photos, images, sizes, strict=True):
                self.assertNotIn("style", photo.attrs)
                rendition = source.renditions.get(filter_spec="max-1536x1536")
                self.assertEqual(int(photo["width"]), rendition.width)
                self.assertEqual(int(photo["height"]), rendition.height)
                self.assertEqual(rendition.width * size[1], rendition.height * size[0])
                response = self.client.get(photo["src"])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "image/png")
                with Image.open(
                    io.BytesIO(b"".join(response.streaming_content))
                ) as rendered:
                    rendered = rendered.convert("RGB")
                    w, h = rendered.size
                    self.assertEqual(
                        [
                            rendered.getpixel(point)
                            for point in [
                                (w // 2, 3),
                                (w // 2, h - 4),
                                (3, h // 2),
                                (w - 4, h // 2),
                            ]
                        ],
                        [
                            (227, 66, 52),
                            (52, 120, 227),
                            (34, 166, 103),
                            (244, 185, 66),
                        ],
                    )
                self.assertEqual(self.client.get(source.file.url).status_code, 404)
        branch.refresh_from_db()
        self.assertEqual(branch.live_revision.content, original_revision)
        self.assertEqual(
            list(branch.facilities.values_list("position_x", "position_y")),
            [(10, 90)] * 3,
        )
