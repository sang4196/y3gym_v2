import re
import uuid

import bleach
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.images.models import AbstractImage, AbstractRendition
from wagtail.models import (
    DraftStateMixin,
    LockableMixin,
    Orderable,
    PreviewableMixin,
    RevisionMixin,
)

from .panels import PopupSettingsPanel


class ContentImage(AbstractImage):
    admin_form_fields = (
        "title",
        "file",
        "focal_point_x",
        "focal_point_y",
        "focal_point_width",
        "focal_point_height",
    )

    def validate_immutable_file(self):
        if not self.pk:
            return
        old = (
            type(self).objects.filter(pk=self.pk).values_list("file", flat=True).first()
        )
        if old and (old != self.file.name or not self.file._committed):
            raise ValidationError(
                {
                    "file": "기존 사진 파일은 교체할 수 없습니다. 새 사진을 등록한 뒤 글에서 선택해 주세요."
                }
            )

    def clean(self):
        super().clean()
        self.validate_immutable_file()

    def save(self, *args, **kwargs):
        self.validate_immutable_file()
        return super().save(*args, **kwargs)


class Rendition(AbstractRendition):
    image = models.ForeignKey(
        ContentImage, on_delete=models.CASCADE, related_name="renditions"
    )

    class Meta:
        unique_together = [("image", "filter_spec", "focal_point_key")]


class Post(
    PreviewableMixin, DraftStateMixin, LockableMixin, RevisionMixin, models.Model
):
    title = models.CharField("제목", max_length=200)
    category = models.CharField(
        "분류",
        max_length=10,
        choices=[("notices", "공지"), ("events", "이벤트")],
        default="notices",
    )
    summary = models.CharField("짧은 설명", max_length=300, blank=True)
    cover_image = models.ForeignKey(
        ContentImage,
        verbose_name="대표 사진",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    body = RichTextField(
        "본문",
        blank=True,
        features=["h2", "h3", "bold", "italic", "ol", "ul", "link", "image"],
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("category"),
        FieldPanel("summary"),
        FieldPanel(
            "cover_image", help_text="선택 항목입니다. 본문에 넣는 사진과 구분합니다."
        ),
        FieldPanel(
            "body",
            help_text="임시 콘텐츠 검토용입니다. 초안 저장은 공개 화면을 바꾸지 않습니다.",
        ),
        PopupSettingsPanel(heading="팝업 설정"),
    ]

    class Meta:
        verbose_name = "소식"
        verbose_name_plural = "소식"

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        self.body = bleach.clean(
            self.body.source if hasattr(self.body, "source") else self.body or "",
            tags=[
                "p",
                "br",
                "h2",
                "h3",
                "strong",
                "b",
                "em",
                "i",
                "ul",
                "ol",
                "li",
                "a",
                "embed",
            ],
            attributes={
                "a": ["href", "linktype", "id"],
                "embed": ["embedtype", "id", "format", "alt"],
            },
            protocols=["http", "https", "mailto", "tel"],
            strip=True,
        )
        # Wagtail database rich text uses self-closing embed tags; HTML5
        # sanitization otherwise serializes them without the closing slash.
        self.body = re.sub(r"<embed(\s[^>]*?)(?<!/)>", r"<embed\1/>", self.body)
        self.body = self.body.replace("<br>", "<br/>")

    def get_absolute_url(self):
        return reverse("news:detail", args=[self.pk])

    def get_preview_template(self, request, mode_name):
        return "news/detail.html"

    def serve_preview(self, request, mode_name):
        # Wagtail's preview endpoint also checks model permissions; keep the
        # rendering method safe if called outside that endpoint later.
        if not request.user.has_perm("news.change_post"):
            raise PermissionDenied
        response = TemplateResponse(
            request,
            self.get_preview_template(request, mode_name),
            {
                "post": self,
                "is_preview": True,
                "page_kind": "news-post",
            },
        )
        response["Cache-Control"] = "private, no-store"
        return response


class PopupSetting(models.Model):
    # Separate from Post/revisions: publishing an older body draft must never
    # restore older popup settings or publish a draft as a side effect.
    post = models.OneToOneField(
        Post, on_delete=models.CASCADE, related_name="popup_setting"
    )
    enabled = models.BooleanField("팝업 사용", default=False)
    starts_at = models.DateTimeField("시작 일시 (한국 시간)", null=True, blank=True)
    ends_at = models.DateTimeField("종료 일시 (한국 시간)", null=True, blank=True)
    version = models.PositiveIntegerField(default=0, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.enabled:
            errors = {}
            if not self.starts_at:
                errors["starts_at"] = "팝업을 사용하려면 시작 일시가 필요합니다."
            if not self.ends_at:
                errors["ends_at"] = "팝업을 사용하려면 종료 일시가 필요합니다."
            if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
                errors["ends_at"] = "종료 일시는 시작 일시보다 늦어야 합니다."
            if errors:
                raise ValidationError(errors)

    def display_state(self, now=None):
        now = now or timezone.now()
        if not self.enabled:
            return "사용 안 함", "팝업 사용 설정이 꺼져 있습니다."
        if not self.post.live or not self.post.live_revision_id:
            return (
                "게시글 비공개",
                "연결 글을 공개해야 팝업 노출 대상이 됩니다. 설정 적용은 글을 게시하지 않습니다.",
            )
        if not self.starts_at or not self.ends_at:
            return "기간 설정 필요", "시작·종료 일시를 확인해 주세요."
        if now < self.starts_at:
            return "시작 전", "설정된 시작 일시 전입니다."
        if now >= self.ends_at:
            return (
                "기간 종료",
                "팝업 노출 기간이 끝났습니다. 게시글 공개 상태는 유지됩니다.",
            )
        return (
            "노출 대상",
            "공개 글이며 서버 시각이 노출 기간 안에 있습니다. 오늘 숨김·브라우저 차단 여부는 방문자마다 다릅니다.",
        )


class BrandContent(
    PreviewableMixin, DraftStateMixin, LockableMixin, RevisionMixin, models.Model
):
    # One site-wide editing unit, including when two create requests race.
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    live = models.BooleanField(default=False, editable=False)
    name = models.CharField("브랜드명", max_length=80, blank=True)
    logo_image = models.ForeignKey(
        ContentImage,
        verbose_name="로고",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    intro_title = models.TextField("첫 소개 제목", max_length=160, blank=True)
    intro_text = models.TextField("소개 설명", max_length=500, blank=True)
    hero_image = models.ForeignKey(
        ContentImage,
        verbose_name="대표 사진",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    hero_alt = models.CharField("대표 사진 대체 설명", max_length=200, blank=True)
    hero_position_x = models.PositiveSmallIntegerField(
        "사진 가로 중심 (%)", default=50, validators=[MaxValueValidator(100)]
    )
    hero_position_y = models.PositiveSmallIntegerField(
        "사진 세로 중심 (%)", default=50, validators=[MaxValueValidator(100)]
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel(
                    "name",
                    help_text="공개할 때 필수입니다. 미완성 초안은 저장할 수 있습니다.",
                ),
                FieldPanel(
                    "logo_image",
                    help_text="선택 항목입니다. 없으면 브랜드명을 텍스트로 표시합니다.",
                ),
            ],
            heading="브랜드",
        ),
        MultiFieldPanel(
            [
                FieldPanel(
                    "intro_title",
                    help_text="공개할 때 필수입니다. 줄바꿈을 사용할 수 있으며 초안 저장은 공개 홈을 바꾸지 않습니다.",
                ),
                FieldPanel("intro_text"),
            ],
            heading="홈 소개",
        ),
        MultiFieldPanel(
            [
                FieldPanel(
                    "hero_image",
                    help_text="없으면 대표 사진 영역을 숨깁니다. 기존 시설 사진 목록과는 별개입니다.",
                ),
                FieldPanel(
                    "hero_alt", help_text="사진에서 보이는 내용을 설명해 주세요."
                ),
                FieldPanel("hero_position_x"),
                FieldPanel("hero_position_y"),
            ],
            heading="대표 사진",
        ),
    ]

    class Meta:
        verbose_name = "브랜드·홈"
        verbose_name_plural = "브랜드·홈"
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name="one_brand_content")
        ]

    def __str__(self):
        return self.name or "브랜드·홈 (준비 초안)"

    def validate_for_publication(self):
        errors = {}
        for field in ["name", "intro_title"]:
            if not getattr(self, field).strip():
                errors[field] = (
                    "공개하려면 입력해 주세요. 미완성 상태는 초안 저장할 수 있습니다."
                )
        if errors:
            raise ValidationError(errors)

    def publish(self, revision, **kwargs):
        # Validate the requested revision, not the mutable latest draft. This
        # also guards revision history publication outside the current form.
        revision.as_object().validate_for_publication()
        return super().publish(revision, **kwargs)

    def serve_preview(self, request, mode_name):
        if not request.user.has_perm("news.change_brandcontent"):
            raise PermissionDenied
        from .home import render_home

        response = render_home(request, branding=self, is_preview=True)
        response["Cache-Control"] = "private, no-store"
        return response


def branch_key():
    return "branch-" + uuid.uuid4().hex


class Branch(
    PreviewableMixin, DraftStateMixin, LockableMixin, RevisionMixin, ClusterableModel
):
    key = models.SlugField(
        unique=True, default=branch_key, editable=False, max_length=48
    )
    live = models.BooleanField(default=False, editable=False)
    name = models.CharField("지점명", max_length=100, blank=True)
    intro = models.TextField("지점 소개", max_length=500, blank=True)
    address = models.CharField("주소", max_length=200, blank=True)
    opening_hours = models.TextField("운영시간", max_length=500, blank=True)
    phone = models.CharField("전화 안내 (모의 문의)", max_length=80, blank=True)
    channel = models.CharField("카카오톡 안내 (모의 문의)", max_length=200, blank=True)
    display_order = models.PositiveIntegerField("표시 순서", default=0)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel(
                    "name",
                    help_text="공개할 때 필수입니다. 미완성 초안은 저장할 수 있습니다.",
                ),
                FieldPanel("intro"),
                FieldPanel(
                    "display_order",
                    help_text="작은 숫자부터 표시합니다. 공개 본점은 항상 첫 번째입니다. 본점 지정과 지점 식별자는 이 화면에서 변경하지 않습니다.",
                ),
            ],
            heading="지점 정보",
        ),
        MultiFieldPanel(
            [
                FieldPanel(
                    "address",
                    help_text="공개할 때 필수입니다. 현재는 실제 지도가 연결되지 않습니다.",
                ),
                FieldPanel(
                    "opening_hours",
                    help_text="공개할 때 필수입니다. 줄바꿈할 수 있습니다.",
                ),
                FieldPanel(
                    "phone",
                    help_text="선택 항목입니다. 없으면 전화 버튼을 숨깁니다. 이번 단계는 실제 전화 연결 없이 안내만 표시합니다.",
                ),
                FieldPanel(
                    "channel",
                    help_text="선택 항목입니다. 없으면 카카오톡 버튼을 숨깁니다. 실제 외부 서비스로 연결하지 않습니다.",
                ),
            ],
            heading="위치·운영시간·문의",
        ),
        InlinePanel(
            "facilities",
            label="시설 사진",
            heading="시설 사진",
            help_text="지점과 함께 초안 저장·미리보기·공개합니다. 순서는 위/아래 이동으로 바꿀 수 있습니다. 이미지 없는 항목은 초안에 보관하고 공개 사진에서는 제외합니다.",
        ),
    ]

    class Meta:
        verbose_name = "지점"
        verbose_name_plural = "지점"

    def __str__(self):
        return self.name or "지점 (준비 초안)"

    def headquarters(self):
        return "본점" if self.key == "main" else "일반 지점"

    headquarters.short_description = "본점 구분"

    def save(self, *args, **kwargs):
        if self.pk:
            old_key = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("key", flat=True)
                .first()
            )
            if old_key and self.key != old_key:
                raise ValidationError("지점 식별자와 본점 지정은 변경할 수 없습니다.")
        return super().save(*args, **kwargs)

    def with_content_json(self, content):
        obj = super().with_content_json(content)
        obj.key = self.key
        return obj

    def validate_for_publication(self):
        errors = {
            field: "공개하려면 입력해 주세요. 미완성 상태는 초안 저장할 수 있습니다."
            for field in ["name", "address", "opening_hours"]
            if not getattr(self, field).strip()
        }
        if errors:
            raise ValidationError(errors)

    def publish(self, revision, **kwargs):
        revision.as_object().validate_for_publication()
        return super().publish(revision, **kwargs)

    def get_absolute_url(self):
        return reverse("branches") + "?branch=" + self.key

    def serve_preview(self, request, mode_name):
        if not request.user.has_perm("news.change_branch"):
            raise PermissionDenied
        from .branches import render_branches

        response = render_branches(request, preview=self)
        response["Cache-Control"] = "private, no-store"
        return response


class FacilityImage(Orderable):
    branch = ParentalKey(Branch, on_delete=models.CASCADE, related_name="facilities")
    image = models.ForeignKey(
        ContentImage,
        verbose_name="사진",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    title = models.CharField("제목", max_length=100, blank=True)
    description = models.TextField("설명", max_length=500, blank=True)
    alt = models.CharField("대체 설명", max_length=200, blank=True)
    position_x = models.PositiveSmallIntegerField(
        "가로 중심 (%)", default=50, validators=[MaxValueValidator(100)]
    )
    position_y = models.PositiveSmallIntegerField(
        "세로 중심 (%)", default=50, validators=[MaxValueValidator(100)]
    )

    panels = [
        FieldPanel(
            "image", help_text="이미지 없는 항목은 공개 화면에 표시하지 않습니다."
        ),
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("alt"),
        FieldPanel("position_x"),
        FieldPanel("position_y"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "시설 사진"
        verbose_name_plural = "시설 사진"
