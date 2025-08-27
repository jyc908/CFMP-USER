from django.urls import path,register_converter
from . import views
from rest_framework import routers

#指定命名空间
app_name = 'user'
router = routers.SimpleRouter()

urlpatterns = router.urls
urlpatterns += [
    path('user/avatar/', views.UploadAvatarView.as_view(), name='upload_portrait'),

    path('auth/register/',views.RegisterView.as_view(),name='register'),
    path('auth/login-with-password/',views.login_passwordView.as_view(),name='login_password'),
    path('auth/login-with-captcha/',views.login_captchaView.as_view(),name='login_captcha'),
    path('security/email/',views.modify_email.as_view(), name='modify_email'),
    path('security/password/',views.modify_password.as_view(), name='modify_password'),
    path('captcha/', views.CaptchaView.as_view(), name='captcha'),

    path('user/<int:user_id>/', views.UserIdViewSet.as_view(), name='user'),
    path('user/me/',  views.UserInfoView.as_view(), name='update_user'),
    path('user/me/products/<int:user_id>/', views.UserProductsViewSet.as_view(), name='user-products'),
    path('user/complaint/',views.UserComplaintViewSet.as_view(), name='user-complaint'),
    path('user/follow/<int:followee>/',views.FollowUserDetailsViewSet.as_view(), name='user-follow-detail'),
    path('user/follow/',views.FollowUserViewSet.as_view(), name='user-follow-list'),
    path('user/followee/',views.FolloweeUserViewSet.as_view(), name = 'user-followee-list'),
    path('user/me/products/<int:user_id>/', views.UserProductsViewSet.as_view()),
    path('user/chat/<int:user_id>/',  views.ChatLogViewSet.as_view(), name = 'user-chat-detail'),
    path('user/message/',  views.MessageViewSet.as_view(), name='user-message-list'),
    path('user/password/',views.getPassword.as_view())
]
