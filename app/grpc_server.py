import grpc, asyncio, structlog
from concurrent import futures
from sentiric.image.v1 import gateway_pb2, gateway_pb2_grpc
from app.core.engine import image_engine
from app.core.config import settings

logger = structlog.get_logger()

class ImageGatewayServicer(gateway_pb2_grpc.ImageGatewayServiceServicer):
    async def GenerateImage(self, request, context):
        metadata = dict(context.invocation_metadata())
        trace_id = metadata.get("x-trace-id", "unknown")
        
        try:
            uri = await image_engine.generate_sync(request.prompt, trace_id)
            return gateway_pb2.GenerateImageResponse(success=True, image_uri=uri)
        except Exception as e:
            return gateway_pb2.GenerateImageResponse(success=False, error_message=str(e))

async def serve_grpc():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=4))
    gateway_pb2_grpc.add_ImageGatewayServiceServicer_to_server(ImageGatewayServicer(), server)
    try:
        with open(settings.KEY_PATH, "rb") as f: pk = f.read()
        with open(settings.CERT_PATH, "rb") as f: cert = f.read()
        with open(settings.GRPC_TLS_CA_PATH, "rb") as f: ca = f.read()
        creds = grpc.ssl_server_credentials([(pk, cert)], root_certificates=ca, require_client_auth=True)
        server.add_secure_port(f"[::]:{settings.GRPC_PORT}", creds)
        logger.info(f"gRPC mTLS Ready", event_id="GRPC_SERVER_START")
    except Exception as e:
        logger.error(f"mTLS Fail: {e}", event_id="MTLS_FAIL")
        raise e
    await server.start()
    await server.wait_for_termination()
