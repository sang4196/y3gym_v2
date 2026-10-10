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


class TrainerManagementPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "news/admin/trainer_management.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context["saved_branch"] = bool(self.instance.pk)
            context["can_manage_trainers"] = self.request.user.has_perm(
                "news.change_trainer"
            )
            context["can_add_trainer"] = self.request.user.has_perm("news.add_trainer")
            if self.instance.pk:
                query = "?branch=" + str(self.instance.pk)
                context["trainer_list_url"] = (
                    reverse("wagtailsnippets_news_trainer:list") + query
                )
                context["trainer_add_url"] = (
                    reverse("wagtailsnippets_news_trainer:add") + query
                )
            return context
