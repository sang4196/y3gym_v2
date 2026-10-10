from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
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
    IndexView,
    SnippetViewSet,
    UnpublishView,
)

from .models import Branch, BrandContent, Post, Trainer


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


class TrainerCreateView(BrandCreateView):
    def get_initial_form_instance(self):
        instance = super().get_initial_form_instance() or self.model()
        branch_id = self.request.GET.get("branch", "")
        if branch_id.isdigit():
            instance.branch = Branch.objects.filter(pk=int(branch_id)).first()
        return instance


class TrainerIndexView(IndexView):
    def get_search_form(self):
        form = super().get_search_form()
        branch_id = self.request.GET.get("branch", "")
        if form and branch_id.isdigit():
            # Wagtail submits the search and publication filters together.
            # Keep the branch entry point in that form without adding visible UI.
            form.fields["branch"] = forms.CharField(
                required=False, initial=branch_id, widget=forms.HiddenInput
            )
        return form

    def search_queryset(self, queryset):
        if not self.is_searching:
            return queryset
        query = Q()
        for field in self.search_fields:
            # Match the revision shown in this list. Empty draft values must
            # never fall back to the previously published model values.
            query |= Q(
                **{f"latest_revision__content__{field}__icontains": self.search_query}
            ) | Q(
                latest_revision__isnull=True,
                **{f"{field}__icontains": self.search_query},
            )
        return queryset.filter(query)

    def get_add_url(self):
        url = super().get_add_url()
        branch_id = self.request.GET.get("branch", "")
        if url and branch_id.isdigit():
            url += ("&" if "?" in url else "?") + "branch=" + branch_id
        return url

    def get_queryset(self):
        queryset = super().get_queryset()
        branch_id = self.request.GET.get("branch")
        if branch_id is not None:
            if not branch_id.isdigit():
                return queryset.none()
            # Admin affiliation follows the newest draft, public affiliation
            # follows live_revision. A move must be findable in its draft branch.
            queryset = queryset.filter(
                Q(latest_revision__content__branch=int(branch_id))
                | Q(latest_revision__isnull=True, branch_id=int(branch_id))
            )
        return queryset


class TrainerViewSet(SnippetViewSet):
    model = Trainer
    icon = "user"
    add_to_admin_menu = False
    list_display = [
        "editing_name",
        "editing_branch",
        "editing_order",
        "last_published_at",
    ]
    list_filter = ["live"]
    search_fields = ["name", "intro"]
    index_view_class = TrainerIndexView
    add_view_class = TrainerCreateView
    edit_view_class = BrandEditView
    unpublish_view_class = ConcurrentUnpublishView

    @property
    def permission_policy(self):
        return BranchPermissionPolicy(self.model)


register_snippet(TrainerViewSet)


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
