.PHONY: setup clean dev-up dev-down dev-logs test

VENV = .venv
UV = uv

setup:
	@echo "🚀 Setting up virtual environment..."
	$(UV) venv $(VENV)
	$(UV) pip install -r requirements.txt

clean:
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +

dev-up:
	@echo "🔥 Starting Image-SDXL environment..."
	docker compose up --build -d

dev-logs:
	@echo "📋 Tailing logs..."
	docker compose logs -f image-sdxl-service

dev-down:
	@echo "🛑 Shutting down..."
	docker compose down -v

setup-test:
	uv venv
	uv pip install grpcio 
	uv pip install sentiric-contracts-py git+https://github.com/sentiric/sentiric-contracts.git@v1.25.0

test:
	@echo "🧪 Running Image-SDXL Test..."
	@. $(VENV)/bin/activate && python test_client.py


test-photorealistic:
	@echo "🧪 Running Image-SDXL Test... category"
	@. $(VENV)/bin/activate && python test_client.py --category photorealistic	

test-concept_art:
	@echo "🧪 Running Image-SDXL Test... category"
	@. $(VENV)/bin/activate && python test_client.py --category concept_art		

test-3d_render:
	@echo "🧪 Running Image-SDXL Test... category"
	@. $(VENV)/bin/activate && python test_client.py --category 3d_render			

test-storyboard:
	@echo "🧪 Running Image-SDXL Test... category"
	@. $(VENV)/bin/activate && python test_client.py --category storyboard		