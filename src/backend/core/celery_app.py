from celery import Celery

# Crea la app de Celery
celery = Celery(
    "worker",
    broker="amqp://guest:guest@localhost:5672//",
    backend="rpc://"
)
celery.conf.task_track_started = True

# Importa aquí el módulo de tareas para registrarlas
import app.services.tasks  # noqa
