from django.urls import path, include
from . import views
urlpatterns = [
    path("", views.stockPicker),
    path("stocktracker/", views.stocktracker, name="stocktracker")
]