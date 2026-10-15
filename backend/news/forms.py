from django import forms
from wagtail.admin.forms.models import WagtailAdminModelForm

from .contacts import validate_kakao_chat_url


class BranchAdminForm(WagtailAdminModelForm):
    kakao_chat_url = forms.CharField(
        label="카카오톡 1:1 채팅 URL",
        required=False,
        max_length=500,
        strip=False,
        validators=[validate_kakao_chat_url],
    )
