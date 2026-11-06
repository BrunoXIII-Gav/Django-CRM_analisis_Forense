from django.urls import path

from . import views
from .forensics import case_views

urlpatterns = [
    path("forense/casos/nuevo/", case_views.new_case, name="forensic_new_case"),
    path("forense/corridas/<str:case_id>/", case_views.workflow_detail, name="forensic_workflow"),
    path("forense/corridas/<str:case_id>/<str:phase>/iniciar/", case_views.start_phase, name="forensic_start_phase"),
    path("forense/casos/", case_views.case_list, name="forensic_cases"),
    path("forense/casos/<str:case_id>/", case_views.case_detail, name="forensic_case"),
    path("", views.home, name="home"),
    path("logout/", views.logout_user, name="logout"),
    path("register/", views.register_user, name="register"),
    path("record/<int:pk>/", views.customer_record, name="record"),
    path("record/<int:pk>/delete/", views.delete_record, name="delete_record"),
    path("record/add/", views.add_record, name="add_record"),
    path("record/<int:pk>/update/", views.update_record, name="update_record"),
]
