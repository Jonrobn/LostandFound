from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('list/', views.item_list, name='item_list'),
    path('items/<int:item_id>/', views.item_detail, name='item_detail'),
    path('items/<int:item_id>/edit/', views.item_edit, name='item_edit'),
    path(
        'items/<int:item_id>/delete/',
        views.item_confirm_delete,
        name='item_confirm_delete',
    ),
    path('items/<int:item_id>/comments/add/', views.add_comment, name='add_comment'),
    path('comments/<int:comment_id>/edit/', views.comment_edit, name='comment_edit'),
    path(
        'comments/<int:comment_id>/delete/',
        views.comment_delete,
        name='comment_delete',
    ),
    path('items/<int:item_id>/resolve/', views.mark_resolved, name='mark_resolved'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('accounts/profile/', views.profile, name='profile'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/login/', views.LostFoundLoginView.as_view(), name='login'),
    path('accounts/logout/', views.LostFoundLogoutView.as_view(), name='logout'),
]