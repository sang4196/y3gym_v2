from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls

from config.health import readiness
from news import views
from news.branches import branches
from news.favicon import favicon
from news.home import home
from news.seo import robots_txt, sitemap_xml

urlpatterns = [
    path("favicon.png", favicon, name="favicon"),
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("healthz/", readiness, name="readiness"),
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
