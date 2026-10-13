# apps/accounts/api/

**This app's part of the REST API** (`/api/v1/`). `serializers.py` turns models into JSON and checks input; `views.py` holds thin ViewSets that call the app's `services.py` and limit every query to what the logged-in user may see. Routes are registered in `config/api_urls.py`.
