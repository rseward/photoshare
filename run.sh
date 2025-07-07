#!/bin/bash

. .venv/bin/activate

#cd app
#uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-config logging.ini
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
