# NØD Node — public deployment image
FROM python:3.12-slim

WORKDIR /opt/nod

COPY pyproject.toml README.md ./
COPY NOD-GENESIS-MANIFEST.json ./
COPY docs ./docs
COPY src ./src
COPY node ./node
COPY tests ./tests

ENV PYTHONPATH=/opt/nod/src
ENV NOD_HOST=0.0.0.0
ENV NOD_PORT=8642

EXPOSE 8642

# Run the reference node as a TCP server (TLS certs mounted at /opt/nod/certs).
CMD ["python", "node/nod_node.py", "--serve", "8642", "--agent", "public-node"]
