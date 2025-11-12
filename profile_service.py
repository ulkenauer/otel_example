from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, select
import asyncio

# main.py
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
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

app = FastAPI()

# Конфигурация ресурсов
resource = Resource.create(
    {
        SERVICE_NAME: "fastapi-profile",
        SERVICE_VERSION: "1.0.0",
        "environment": "production",
    }
)

metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(), export_interval_millis=1000
)
metric_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(metric_provider)
tracer_provider = TracerProvider(resource=resource)
# Настройка трейсов
trace.set_tracer_provider(tracer_provider)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

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
    format="%(asctime)s [%(levelname)s] trace_id=%(trace_id)s span_id=%(span_id)s - %(message)s",
)

DATABASE_URL = "postgresql+asyncpg://postgres:mysecretpassword@localhost/demo"

app = FastAPI()

# Инструментация FastAPI

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, future=True
)
SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
FastAPIInstrumentor.instrument_app(
    app, tracer_provider=tracer_provider, meter_provider=metric_provider
)


class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    email = Column(String(100))
    bio = Column(String(500))


@app.on_event("startup")
async def startup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/profile/{profile_id}")
async def read_profile(profile_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Profile).where(Profile.id == profile_id))
        profile = result.scalars().first()

        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        return {
            "id": profile.id,
            "name": profile.name,
            "email": profile.email,
            "bio": profile.bio,
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, loop="asyncio")
