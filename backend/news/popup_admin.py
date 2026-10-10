import json

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import PopupSetting, Post


class PopupForm(forms.ModelForm):
    version = forms.IntegerField(min_value=0, widget=forms.HiddenInput)

    class Meta:
        model = PopupSetting
        fields = ["enabled", "starts_at", "ends_at"]
        widgets = {
            name: forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
            )
            for name in ["starts_at", "ends_at"]
        }


@login_required(login_url="wagtailadmin_login")
@require_http_methods(["GET", "POST"])
def popup_settings(request, pk):
    if not all(
        request.user.has_perm(permission)
        for permission in [
            "wagtailadmin.access_admin",
            "news.change_post",
            "news.publish_post",
        ]
    ):
        raise PermissionDenied
    post = get_object_or_404(
        Post.objects.select_for_update()
        if request.method == "POST"
        else Post.objects.all(),
        pk=pk,
    )
    setting = PopupSetting.objects.filter(post=post).first() or PopupSetting(post=post)
    is_json = request.content_type == "application/json"
    lock = post.get_lock()
    if request.method == "POST" and lock and lock.for_user(request.user):
        message = "게시글이 잠겨 있습니다. 기존 편집 잠금을 해제한 뒤 팝업 설정을 적용해 주세요."
        if is_json:
            return JsonResponse({"errors": {"__all__": [message]}}, status=409)
        raise PermissionDenied(message)
    data = None
    status = 200
    applied = False
    if request.method == "POST":
        try:
            data = json.loads(request.body) if is_json else request.POST
            if not isinstance(data, dict) and is_json:
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            return JsonResponse(
                {"errors": {"__all__": ["입력 형식을 확인해 주세요."]}}, status=400
            )
    form = PopupForm(data, instance=setting, initial={"version": setting.version})
    if request.method == "POST":
        if form.is_valid():
            if form.cleaned_data["version"] != setting.version:
                form.add_error(
                    None,
                    "다른 화면에서 팝업 설정을 변경했습니다. 입력을 보관하고 최신 설정을 다시 확인해 주세요.",
                )
                status = 409
            else:
                setting.version += 1
                setting.save()
                applied = True
                form = PopupForm(instance=setting, initial={"version": setting.version})
        else:
            status = 400
    # ModelForm validation mutates its instance even on invalid/stale input.
    # Status describes saved data; leave attempted values in the form itself.
    saved = PopupSetting.objects.filter(post=post).first() or PopupSetting(post=post)
    state, reason = saved.display_state()
    if is_json:
        return JsonResponse(
            {
                "applied": applied,
                "version": setting.version,
                "state": state,
                "reason": reason,
                "errors": {name: list(errors) for name, errors in form.errors.items()},
                "serverTime": timezone.localtime().isoformat(),
            },
            status=status,
        )
    return render(
        request,
        "news/admin/popup_settings.html",
        {
            "post": post,
            "form": form,
            "state": state,
            "reason": reason,
            "applied": applied,
        },
        status=status,
    )
