from fastapi import FastAPI, HTTPException
import httpx
import asyncio
from contextlib import asynccontextmanager
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import logging
from fastapi import FastAPI
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from httpx import AsyncClient, AsyncHTTPTransport, HTTPError
from opentelemetry.instrumentation.httpx import AsyncOpenTelemetryTransport
from opentelemetry.trace import get_tracer

app = FastAPI()

# Конфигурация ресурсов
resource = Resource.create({
    SERVICE_NAME: "fastapi-gateway",
    SERVICE_VERSION: "1.0.0",
    "environment": "production"
})

metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(),
    export_interval_millis=1000
)
metric_provider = MeterProvider(
    resource=resource,
    metric_readers=[metric_reader]
)
metrics.set_meter_provider(metric_provider)

# Настройка трейсов
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(TracerProvider(resource=resource))
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter())
)

# Настройка логов
logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(
        OTLPLogExporter(),
        schedule_delay_millis=1000,
    )
)

# logging
LoggingInstrumentor().instrument(set_logging_format=True)
handler = LoggingHandler()
logging.getLogger().addHandler(handler)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] trace_id=%(trace_id)s span_id=%(span_id)s - %(message)s'
)


app = FastAPI()
PROFILE_SERVICE_URL = "http://localhost:8001"
DOCUMENT_SERVICE_URL = "http://localhost:8002"


# Инструментация FastAPI
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()
# HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)


# global_client = httpx.AsyncClient(timeout=10.0)
# @asynccontextmanager
# async def get_async_client():
#     yield global_client


@asynccontextmanager
async def get_async_client():
    async with httpx.AsyncClient(timeout=10.0) as client:
    # async with httpx.AsyncClient(timeout=10.0, transport=AsyncOpenTelemetryTransport(AsyncHTTPTransport(), tracer_provider=tracer_provider)) as client:
        yield client


@app.get("/profile/{profile_id}/full")
async def get_full_profile(profile_id: int):
    tracer = get_tracer(__name__)
    
    span = tracer.start_span("HTTPX initialize")

    async with get_async_client() as client:
        span.end()
        # Последовательный запрос к сервисам
        with tracer.start_as_current_span("data fetch"):
            profile_response = await client.get(f"{PROFILE_SERVICE_URL}/profile/{profile_id}")
            docs_response = await client.get(f"{DOCUMENT_SERVICE_URL}/documents/{profile_id}")

        # Параллельный запрос к сервисам
        # with tracer.start_as_current_span("data fetch"):
        #     profile_task = client.get(f"{PROFILE_SERVICE_URL}/profile/{profile_id}")
        #     docs_task = client.get(f"{DOCUMENT_SERVICE_URL}/documents/{profile_id}")

        #     responses = await asyncio.gather(
        #         profile_task, docs_task, return_exceptions=True
        #     )

        #     profile_response, docs_response = responses

        # Обработка ошибок
        errors = []
        if (
            isinstance(profile_response, Exception)
            or profile_response.status_code != 200
        ):
            errors.append("Profile service unavailable")
        if isinstance(docs_response, Exception) or docs_response.status_code != 200:
            errors.append("Documents service unavailable")

        if errors:
            raise HTTPException(status_code=503, detail=", ".join(errors))
        return {"profile": profile_response.json(), "documents": docs_response.json()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, loop="asyncio")
