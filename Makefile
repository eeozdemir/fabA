build:
\tdocker build -t ozdemire/fastapi-app:latest .

run:
\tdocker run -p 8000:8000 ozdemire/fastapi-app:latest

lint:
\tpipx run flake8 app/ || true

scan:
\ttrivy image ozdemire/fastapi-app:latest || true

sbom:
\tsyft ozdemire/fastapi-app:latest -o json > sbom.json
