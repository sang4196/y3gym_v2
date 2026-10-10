from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls

from news import views
from news.branches import branches
from news.home import home

urlpatterns = [
    path("admin/", include(wagtailadmin_urls)),
    path("", home, name="home"),
    path("branches/", branches, name="branches"),
    path("popups/<int:pk>/", views.popup_detail, name="popup_detail"),
    path("popups/<int:pk>/data/", views.popup_data, name="popup_data"),
    path(
        "news/",
        include(
            (
                [
                    path("", views.news_list, name="list"),
                    path("<int:pk>/", views.news_detail, name="detail"),
                ],
                "news",
            )
        ),
    ),
    path("media/<path:name>", views.protected_media, name="protected_media"),
]
