"""/notifications/: each user reads and marks their own notifications."""
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .services import mark_read


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "message", "link", "is_read", "read_at", "created_at"]
        read_only_fields = fields


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    queryset_model = Notification
    filterset_fields = ["is_read", "kind"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="read")
    def read(self, request, pk=None):
        return Response(NotificationSerializer(mark_read(self.get_object())).data)
