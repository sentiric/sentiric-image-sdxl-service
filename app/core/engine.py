# [ARCH-COMPLIANCE] SOP-01: Eksiksiz Teslimat
import torch, uuid, os, boto3, asyncio, structlog, aio_pika
from diffusers import AutoPipelineForText2Image
from botocore.config import Config
from app.core.config import settings
from sentiric.event.v1 import event_pb2
from google.protobuf.timestamp_pb2 import Timestamp

logger = structlog.get_logger()

class ImageEngine:
    def __init__(self):
        self.pipe = None
        self.semaphore = asyncio.Semaphore(1) 
        self.s3 = boto3.client('s3', 
            endpoint_url=settings.S3_ENDPOINT, 
            aws_access_key_id=settings.S3_ACCESS_KEY, 
            aws_secret_access_key=settings.S3_SECRET_KEY, 
            config=Config(signature_version='s3v4')
        )

    def initialize(self):
        logger.info(f"Loading SD-Turbo Engine: {settings.MODEL_ID}", event_id="MODEL_INIT")
        try:
            # SD-Turbo modelini fp16 (hızlı ve hafif) modunda yükle
            self.pipe = AutoPipelineForText2Image.from_pretrained(
                settings.MODEL_ID, 
                torch_dtype=torch.float16, 
                variant="fp16"
            )

            # [PERFORMANS]: Watermark mekanizmasını tamamen devre dışı bırak
            # Bu sayede invisible-watermark kütüphanesine ihtiyaç kalmaz
            if hasattr(self.pipe, "watermark"):
                self.pipe.watermark = None

            if settings.DEVICE == "cuda":
                self.pipe.to("cuda")
                # Bellek verimliliği için VAE dilimlemeyi aç
                self.pipe.vae.enable_slicing()
            
            self.pipe.set_progress_bar_config(disable=True)
            logger.info("SD-Turbo Ready. Watermark Disabled.", event_id="MODEL_READY")
        except Exception as e:
            logger.error(f"Load Fail: {e}", event_id="MODEL_INIT_FAIL")

    async def generate_async(self, prompt: str, trace_id: str, tenant_id: str) -> str:
        # GPU koruma kilidi
        async with self.semaphore:
            logger.info(f"Generating image for: {prompt[:50]}...", event_id="IMAGE_GEN_START", trace_id=trace_id)
            job_id = str(uuid.uuid4())
            path = f"/tmp/{job_id}.png"
            
            def render():
                # num_inference_steps=4 kaliteyi artırır, Turbo için idealdir.
                with torch.inference_mode():
                    img = self.pipe(
                        prompt=prompt, 
                        num_inference_steps=4, 
                        guidance_scale=0.0
                    ).images[0]
                img.save(path)
            
            try:
                # GPU işlemini asenkron çalıştır
                await asyncio.to_thread(render)
                
                # S3'e yükle
                object_name = f"images/{job_id}.png"
                await asyncio.to_thread(self.s3.upload_file, path, settings.S3_BUCKET, object_name)
                
                if os.path.exists(path): 
                    os.remove(path)
                
                s3_uri = f"s3://{settings.S3_BUCKET}/{object_name}"
                logger.info("Image uploaded", event_id="IMAGE_GEN_SUCCESS", trace_id=trace_id, uri=s3_uri)
                
                # RabbitMQ'ya olay fırlat
                await self._publish_event("media.generation.completed", trace_id, job_id, tenant_id, True, s3_uri)
                return s3_uri
                
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Image Render failed: {err_msg}", event_id="IMAGE_GEN_FAIL", trace_id=trace_id)
                if os.path.exists(path): 
                    os.remove(path)
                await self._publish_event("media.generation.failed", trace_id, job_id, tenant_id, False, "", err_msg)
                raise e
            finally:
                if settings.DEVICE == "cuda":
                    torch.cuda.empty_cache()

    async def _publish_event(self, event_type, trace_id, job_id, tenant_id, success, uri, err=""):
        try:
            conn = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            async with conn:
                ch = await conn.channel()
                ex = await ch.declare_exchange("sentiric_events", aio_pika.ExchangeType.TOPIC, durable=True)
                ts = Timestamp(); ts.GetCurrentTime()
                evt = event_pb2.MediaGenerationCompletedEvent(
                    event_type=event_type, trace_id=trace_id, job_id=job_id, tenant_id=tenant_id, 
                    media_type="image", success=success, result_uri=uri, error_message=err, timestamp=ts
                )
                await ex.publish(aio_pika.Message(body=evt.SerializeToString(), content_type="application/protobuf"), routing_key=event_type)
        except Exception as e:
            logger.error(f"RMQ Fail: {e}")

image_engine = ImageEngine()