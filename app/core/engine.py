import torch, uuid, os, boto3, asyncio, structlog
from diffusers import AutoPipelineForText2Image
from botocore.config import Config
from app.core.config import settings

logger = structlog.get_logger()

class ImageEngine:
    def __init__(self):
        self.pipe = None
        self.s3 = boto3.client('s3', endpoint_url=settings.S3_ENDPOINT, aws_access_key_id=settings.S3_ACCESS_KEY, aws_secret_access_key=settings.S3_SECRET_KEY, config=Config(signature_version='s3v4'))

    def initialize(self):
        logger.info(f"Loading {settings.MODEL_ID}", event_id="MODEL_INIT")
        try:
            self.pipe = AutoPipelineForText2Image.from_pretrained(settings.MODEL_ID, torch_dtype=torch.float16, variant="fp16").to(settings.DEVICE)
            logger.info("SDXL Turbo Ready.", event_id="MODEL_READY")
        except Exception as e:
            logger.error(f"Load Fail: {e}", event_id="MODEL_INIT_FAIL")

    async def generate_sync(self, prompt: str, trace_id: str) -> str:
        logger.info("Generating image...", event_id="IMAGE_GEN_START", trace_id=trace_id)
        job_id = str(uuid.uuid4())
        path = f"/tmp/{job_id}.png"
        
        # SDXL Turbo 1-4 stepte üretir (Çok hızlıdır)
        def render():
            img = self.pipe(prompt=prompt, num_inference_steps=2, guidance_scale=0.0).images[0]
            img.save(path)
        
        await asyncio.to_thread(render)
        
        object_name = f"images/{job_id}.png"
        await asyncio.to_thread(self.s3.upload_file, path, settings.S3_BUCKET, object_name)
        os.remove(path)
        
        s3_uri = f"s3://{settings.S3_BUCKET}/{object_name}"
        logger.info("Image uploaded", event_id="IMAGE_GEN_SUCCESS", trace_id=trace_id, uri=s3_uri)
        return s3_uri

image_engine = ImageEngine()
