build:
	uv pip install -r requirements.txt
	#uv pip install -e .

index:
	./indexer.py index

run:
	./run.sh

backup:
	rsync -aPv photoshare.db  /cifs/legolas2/family/Pictures/

test:
	pytest

query:
	sqlite3 photoshare.db



