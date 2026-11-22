from django.contrib import admin
from django.urls import path

from reconcile import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/disagreements/", views.disagreements),
    path("api/orgs/", views.orgs),
    path("api/reasons/", views.reasons),
]