from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# Настройка ресурса с именем сервиса
resource = Resource(
    attributes={"service.name": "my-fastapi-service", "service.version": "1.0.0"}
)

# Инициализация провайдера трейсов
trace_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(trace_provider)

# Настройка OTLP экспортера для Elastic APM
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")

# Добавление процессора для экспорта трейсов
trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Создание FastAPI приложения
app = FastAPI()

# Инструментация FastAPI
FastAPIInstrumentor.instrument_app(app)

# Инструментация HTTP клиента
# HTTPXClientInstrumentor().instrument()


@app.get("/")
async def read_root():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("root_span"):
        return {"Hello": "World"}


@app.get("/err")
async def read_err():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("root_span"):
        raise Exception("something went wrong")
        return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int):
    with trace.get_tracer(__name__).start_as_current_span("item_span") as span:
        span.set_attribute("item_id", item_id)
        return {"item_id": item_id}
