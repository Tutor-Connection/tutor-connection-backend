from django.urls import path
from .views import (ChatRoomListCreateView,
    ChatRoomDetailView,
    ChatRoomMembersView,
    RemoveMemberView,
    SendMessageView,
    MessageHistoryView,
    MarkMessageSeenView,
    DeleteMessageView,
    NotificationListView,
    NotificationDetailView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    UnreadNotificationCountView,
)

urlpatterns = [
    path('chat/rooms/', ChatRoomListCreateView.as_view()),
    path('chat/rooms/<int:id>/', ChatRoomDetailView.as_view()),
    path('chat/rooms/<int:id>/members/', ChatRoomMembersView.as_view()),
    path('chat/rooms/<int:id>/members/<int:user_id>/', RemoveMemberView.as_view()),
    path('chat/messages/', SendMessageView.as_view()),
    path('chat/rooms/<int:id>/messages/', MessageHistoryView.as_view()),
    path('chat/messages/<int:id>/seen/', MarkMessageSeenView.as_view()),
    path('chat/messages/<int:id>/', DeleteMessageView.as_view()),
    
    path('', NotificationListView.as_view()),
    path('read-all/', MarkAllNotificationsReadView.as_view()),
    path('unread-count/', UnreadNotificationCountView.as_view()),
    path('<int:id>/', NotificationDetailView.as_view()),
    path('<int:id>/read/', MarkNotificationReadView.as_view()),
]