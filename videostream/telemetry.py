# videostream/telemetry.py
from opentelemetry import trace

def setup_tracing():
    # Ne PAS créer de TracerProvider ici — l'auto-instrumentation
    # de l'OpenTelemetry Operator l'a déjà fait (via l'init container).
    # On récupère simplement le tracer global déjà configuré.
    return trace.get_tracer(__name__)
