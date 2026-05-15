import os

class Settings:
    APP_VERSION = "1.0.0"
    ENV = os.getenv("ENV", "production")
    DEVICE = os.getenv("IMAGE_SERVICE_DEVICE", "cuda")
    MODEL_ID = os.getenv("SDXL_MODEL_ID", "stabilityai/sdxl-turbo")
    
    HTTP_PORT = int(os.getenv("SDXL_SERVICE_HTTP_PORT", "16210"))
    GRPC_PORT = int(os.getenv("SDXL_SERVICE_GRPC_PORT", "16211"))
    
    GRPC_TLS_CA_PATH = os.getenv("GRPC_TLS_CA_PATH", "/sentiric-certificates/certs/ca.crt")
    CERT_PATH = os.getenv("SDXL_SERVICE_CERT_PATH", "/sentiric-certificates/certs/image-sdxl-service-chain.crt")
    KEY_PATH = os.getenv("SDXL_SERVICE_KEY_PATH", "/sentiric-certificates/certs/image-sdxl-service.key")

    S3_ENDPOINT = os.getenv("BUCKET_ENDPOINT_URL", "http://minio:9000")
    S3_ACCESS_KEY = os.getenv("BUCKET_ACCESS_KEY_ID", "sentiric")
    S3_SECRET_KEY = os.getenv("BUCKET_SECRET_ACCESS_KEY", "sentiric-secret-key")
    S3_BUCKET = os.getenv("BUCKET_NAME", "sentiric")

settings = Settings()
