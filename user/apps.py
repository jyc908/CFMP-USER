from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'

    def ready(self):
        from config.nacos_heartbeat import start_nacos_heartbeat
        start_nacos_heartbeat()