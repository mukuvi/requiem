SHELL := /bin/bash
MODEL := /home/mukuvi/Github/Personal/dozer/models/gemma-3-1b-it-Q4_K_M.gguf
LLAMA := /home/mukuvi/Github/Personal/dozer/.llama.cpp/bin/llama-server
PORT := 8099

.PHONY: models llama server demo test run kill

models:
	@echo "Model: $(MODEL)"
	@test -f $(MODEL) && echo "OK" || (echo "missing"; exit 1)

llama:
	@echo "llama: $(LLAMA)"
	@test -f $(LLAMA) && echo "OK" || (echo "missing"; exit 1)

server:
	@echo "Starting llama-server on :$(PORT)..."
	$(LLAMA) -m $(MODEL) -c 2048 -t 4 --host 127.0.0.1 --port $(PORT) -np 1

demo: examples/segv
	PYTHONPATH=. python3 -m requiem run -- python3 examples/lost_config.py || true
	PYTHONPATH=. python3 -m requiem run -- python3 examples/split_the_bill.py || true
	PYTHONPATH=. python3 -m requiem run -- ./examples/segv || true
	PYTHONPATH=. python3 -m requiem list

examples/segv: examples/segv.c
	gcc -O0 -g -o examples/segv examples/segv.c

test:
	PYTHONPATH=. python3 -m pytest tests/ -v

kill:
	-pkill -f "llama-server.*8099" || true
