import grpc, os, uuid, time, argparse, random
from sentiric.image.v1 import gateway_pb2, gateway_pb2_grpc

# --- 🎨 PROFESYONEL GÖRÜNTÜ KATALOĞU ---
# d (detail_steps): Turbo için 1 (hızlı) ile 4 (kaliteli) arası
EXAMPLES = {
    "photorealistic": [
        "Hyper-realistic portrait of an elderly artisan in a workshop, dust motes in sunlight, 8k, highly detailed skin texture",
        "Modern glass skyscraper reflecting a dramatic sunset, architectural photography, cinematic lighting, sharp focus",
        "A plate of gourmet pasta with steam rising, macro photography, shallow depth of field, natural lighting"
    ],
    "concept_art": [
        "Epic landscape of a floating island with waterfalls, digital painting, Studio Ghibli style, vibrant colors",
        "Dark gothic cathedral interior with glowing blue energy runes on the floor, fantasy art, intricate details",
        "A futuristic cyberpunk marketplace, neon signs, rainy street, low angle shot, blade runner aesthetic"
    ],
    "3d_render": [
        "Cute isometric 3D bedroom scene, soft pastel colors, blender render, claymation style, cozy lighting",
        "A futuristic sports car made of translucent liquid metal, unreal engine 5 render, raytracing, 8k resolution"
    ],
    "storyboard": [
        # Karakter Tutarlılığı Testi (Video öncesi çok kritik)
        "A brave female knight in silver armor, standing in a green forest, looking at camera",
        "A brave female knight in silver armor, walking through a burning village, side profile",
        "A brave female knight in silver armor, resting by a campfire at night, cinematic lighting"
    ]
}

def send_job(stub, prompt, trace_id):
    print(f"🎨 Üretiliyor: '{prompt[:60]}...'")
    start = time.time()
    try:
        response = stub.GenerateImage(gateway_pb2.GenerateImageRequest(
            tenant_id="test-tenant",
            trace_id=trace_id,
            prompt=prompt
        ))
        if response.success:
            print(f"  ✅ TAMAMLANDI | Süre: {time.time()-start:.2f}s")
            print(f"  🔗 URI: {response.image_uri}")
        else:
            print(f"  ❌ HATA: {response.error_message}")
    except grpc.RpcError as e:
        print(f"  🚨 gRPC HATASI: {e.details()}")

def run_test():
    parser = argparse.ArgumentParser(description="Sentiric Image-SDXL Master Test Suite")
    parser.add_argument("--category", type=str, choices=list(EXAMPLES.keys()) + ["all"], help="Kategori testi")
    parser.add_argument("--stress", type=int, default=1, help="Ard arda kaç tane üretilsin?")
    parser.add_argument("--prompt", type=str, help="Özel prompt")
    args = parser.parse_args()

    # mTLS Auth
    base_cert_dir = "../sentiric-certificates/certs"
    with open(os.path.join(base_cert_dir, "ca.crt"), "rb") as f: ca = f.read()
    with open(os.path.join(base_cert_dir, "image-sdxl-service-chain.crt"), "rb") as f: cert = f.read()
    with open(os.path.join(base_cert_dir, "image-sdxl-service.key"), "rb") as f: key = f.read()
    creds = grpc.ssl_channel_credentials(ca, key, cert)

    with grpc.secure_channel("localhost:16211", creds) as channel:
        stub = gateway_pb2_grpc.ImageGatewayServiceStub(channel)
        
        if args.prompt:
            for i in range(args.stress):
                send_job(stub, args.prompt, f"stress-{i}")
        
        elif args.category:
            cats = EXAMPLES.keys() if args.category == "all" else [args.category]
            for cat in cats:
                print(f"\n📂 KATEGORİ: {cat.upper()}")
                for p in EXAMPLES[cat]:
                    send_job(stub, p, str(uuid.uuid4()))
        else:
            # Rastgele bir tane
            cat = random.choice(list(EXAMPLES.keys()))
            send_job(stub, random.choice(EXAMPLES[cat]), str(uuid.uuid4()))

if __name__ == "__main__":
    run_test()