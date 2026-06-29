from django.urls import path
from . import views

urlpatterns = [
    # authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # home page
    path('', views.home, name='home'),

    # rule management
    path('rules/', views.rule_list, name='rule_list'),
    path('rules/add/', views.add_rule, name='add_rule'),
    path('rules/edit/<int:rule_id>/', views.edit_rule, name='edit_rule'),
    path('rules/delete/<int:rule_id>/', views.delete_rule, name='delete_rule'),
    path('rules/toggle/<int:rule_id>/', views.toggle_rule, name='toggle_rule'),

    # approval workflow (admin only)
    path('approvals/', views.pending_approvals, name='pending_approvals'),
    path('approvals/approve/<int:rule_id>/', views.approve_rule, name='approve_rule'),
    path('approvals/reject/<int:rule_id>/', views.reject_rule, name='reject_rule'),

    # evaluation
    path('evaluate/', views.evaluate, name='evaluate'),

    # history
    path('history/', views.evaluation_history, name='evaluation_history'),
    path('history/<int:log_id>/', views.evaluation_detail, name='evaluation_detail'),

    # simulation
    path('simulate/', views.simulate, name='simulate'),

    # dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
]
