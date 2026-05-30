from app.config import settings
print('has_key', bool(settings.gemini_api_key))
print('model', settings.gemini_model_name)
