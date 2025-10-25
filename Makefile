venv:
	uv venv --system-site-packages

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
	# pip install litecli
	#sqlite3 photoshare.db
	litecli photoshare.db
lint:
	ruff check
	#ruff check --fix



