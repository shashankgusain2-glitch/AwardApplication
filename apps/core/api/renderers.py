"""Every successful API response uses the same shape: {success, data, message, errors}."""
from rest_framework.renderers import JSONRenderer


class EnvelopeJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")
        if response is not None and response.status_code == 204:   # "No Content" must have no body
            return b""
        already_wrapped = isinstance(data, dict) and {"success", "data", "message", "errors"} <= set(data)
        if response is not None and not already_wrapped and response.status_code < 400:
            data = {"success": True, "data": data, "message": "", "errors": None}
        return super().render(data, accepted_media_type, renderer_context)
