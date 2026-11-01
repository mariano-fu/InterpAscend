from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'srs'

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='srs/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    
    # Password reset URLs - Using clean templates without tracking URLs
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='srs/auth/password_reset_form.html',
             email_template_name='srs/auth/password_reset_email_clean.html',
             html_email_template_name='srs/auth/password_reset_email_clean.html',
             subject_template_name='srs/auth/password_reset_subject.txt',
             success_url='/srs/password-reset/done/'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='srs/auth/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='srs/auth/password_reset_confirm.html',
             success_url='/srs/reset/done/'
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='srs/auth/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    
    # SRS URLs
    path('', views.dashboard, name='dashboard'),
    path('categories/', views.category_list, name='category_list'),
    path('study/<slug:category_slug>/', views.study_session, name='study_session'),
    path('stats/', views.user_stats, name='user_stats'),
    
    # HTMX endpoints for study sessions
    path('study/<slug:category_slug>/next-card/', views.get_next_card, name='get_next_card'),
    path('study/<slug:category_slug>/show-answer/', views.show_answer, name='show_answer'),
    path('study/<slug:category_slug>/review/', views.review_card, name='review_card'),
]