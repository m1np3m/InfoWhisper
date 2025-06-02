from phoenix.otel import register
import os

def setup_tracer():
    # os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = ""
    # os.environ["PHOENIX_CLIENT_HEADERS"] = ""
    # os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = ""

    tracer_provider = register(
      project_name="AI-News",
      auto_instrument=True,
      batch=True,
      endpoint='http://localhost:6006/v1/traces'
    )
    return tracer_provider