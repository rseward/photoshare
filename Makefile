build:
	uv pip install -r requirements.txt
	#uv pip install -e .

index:
	./indexer.py index

run:
	./run.sh
