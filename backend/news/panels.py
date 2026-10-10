from django.urls import reverse
from wagtail.admin.panels import Panel


class PopupSettingsPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "news/admin/popup_panel.html"

        def get_context_data(self, parent_context=None):
            from .models import PopupSetting

            context = super().get_context_data(parent_context)
            post = self.instance
            context["saved_post"] = bool(post.pk)
            if post.pk:
                settings = PopupSetting.objects.filter(post_id=post.pk).first()
                settings = settings or PopupSetting(post=post)
                context.update(
                    popup=settings,
                    popup_state=settings.display_state(),
                    popup_url=reverse("news_popup_settings", args=[post.pk]),
                    can_apply=self.request.user.has_perm("news.publish_post"),
                )
            return context
