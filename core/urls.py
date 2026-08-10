from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from blog.api import router as blog_router
from blog.api_v2 import router as blog_v2_router
from core.health import live, ready

api = NinjaAPI()
api.add_router("/", blog_router)
api.add_router("/v2/", blog_v2_router)

urlpatterns = [
    path("health/live", live),
    path("health/ready", ready),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
