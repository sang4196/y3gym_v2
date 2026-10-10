from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.urls import path
from django.utils.html import format_html
from wagtail import hooks
from wagtail.permission_policies.base import ModelPermissionPolicy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    CreateView,
    EditView,
    SnippetViewSet,
    UnpublishView,
)

from .models import Branch, BrandContent, Post


class ConcurrentEditView(EditView):
    def get_object(self, queryset=None):
        if self.request.method == "POST":
            # ATOMIC_REQUESTS holds this lock through validation and revision save.
            queryset = self.model.objects.select_for_update()
        return super().get_object(queryset)

    def is_valid(self, form):
        valid = super().is_valid(form)
        if not self.request.POST.get("loaded_revision_id") or self.is_out_of_date:
            form.add_error(
                None,
                "다른 화면에서 더 최근 내용이 저장되었습니다. 현재 입력을 보관하고 다시 열어 확인해 주세요.",
            )
            self.produced_error_code = "invalid_revision"
            self.produced_error_message = "최신 내용 확인이 필요합니다."
            return False
        return valid


class ConcurrentUnpublishView(UnpublishView):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.request.method == "POST":
            # Wagtail 7.4's UnpublishView ignores the queryset argument. Fetch
            # the current row explicitly; ATOMIC_REQUESTS holds this lock until
            # the inherited permission checks, hooks and unpublish commit end.
            return get_object_or_404(self.model.objects.select_for_update(), pk=obj.pk)
        return obj


class PostViewSet(SnippetViewSet):
    model = Post
    icon = "doc-full"
    menu_label = "소식"
    add_to_admin_menu = True
    list_display = ["title", "category", "first_published_at"]
    list_filter = ["category", "live"]
    search_fields = ["title", "summary"]
    edit_view_class = ConcurrentEditView
    unpublish_view_class = ConcurrentUnpublishView


register_snippet(PostViewSet)


class BrandPermissionPolicy(ModelPermissionPolicy):
    def user_has_permission(self, user, action):
        if action == "add" and self.model.objects.exists():
            return False
        # Site-wide content is withdrawn, not deleted. Deletion/restore policy
        # has not been decided and is outside this milestone.
        if action == "delete":
            return False
        return super().user_has_permission(user, action)


class BrandPublishValidationMixin:
    def is_valid(self, form):
        valid = super().is_valid(form)
        if valid and self.action == "publish":
            try:
                form.instance.validate_for_publication()
            except ValidationError as error:
                for field, messages in error.message_dict.items():
                    for message in messages:
                        form.add_error(field, message)
                self.produced_error_code = "validation_error"
                self.produced_error_message = (
                    "공개 필수 항목을 확인해 주세요. 입력한 내용은 유지됩니다."
                )
                return False
        return valid


class BrandCreateView(BrandPublishValidationMixin, CreateView):
    pass


class BrandEditView(BrandPublishValidationMixin, ConcurrentEditView):
    pass


class BrandViewSet(SnippetViewSet):
    model = BrandContent
    icon = "home"
    menu_label = "브랜드·홈"
    add_to_admin_menu = True
    list_display = ["__str__", "last_published_at"]
    add_view_class = BrandCreateView
    edit_view_class = BrandEditView
    unpublish_view_class = ConcurrentUnpublishView

    @property
    def permission_policy(self):
        return BrandPermissionPolicy(self.model)


register_snippet(BrandViewSet)


class BranchPermissionPolicy(ModelPermissionPolicy):
    def user_has_permission(self, user, action):
        if action == "delete":
            return False
        return super().user_has_permission(user, action)


class BranchUnpublishView(ConcurrentUnpublishView):
    pass


class BranchViewSet(SnippetViewSet):
    model = Branch
    icon = "site"
    menu_label = "지점"
    add_to_admin_menu = True
    list_display = ["__str__", "headquarters", "display_order", "last_published_at"]
    list_filter = ["live"]
    search_fields = ["name", "address"]
    add_view_class = BrandCreateView
    edit_view_class = BrandEditView
    unpublish_view_class = BranchUnpublishView

    @property
    def permission_policy(self):
        return BranchPermissionPolicy(self.model)


register_snippet(BranchViewSet)


@hooks.register("insert_global_admin_js")
def flush_rich_text_before_submit():
    return format_html(
        '<script src="{}"></script><script src="{}"></script>',
        static("news/editor-save.js"),
        static("news/popup-settings.js"),
    )


@hooks.register("register_admin_urls")
def popup_admin_urls():
    from .popup_admin import popup_settings

    return [path("news-popup/<int:pk>/", popup_settings, name="news_popup_settings")]


@hooks.register("construct_main_menu")
def remove_unused_menus(request, menu_items):
    # No page builder, documents or scheduling are part of this milestone.
    menu_items[:] = [
        item for item in menu_items if item.name not in {"explorer", "documents"}
    ]
