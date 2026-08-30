# NØD Node — public deployment image
FROM python:3.12-slim

WORKDIR /opt/nod

COPY pyproject.toml README.md ./
COPY src ./src
COPY node ./node

ENV PYTHONPATH=/opt/nod/src
ENV NOD_HOST=0.0.0.0
ENV NOD_PORT=8642

EXPOSE 8642

# Run the reference node as a TLS-capable TCP server.
# TLS certs are mounted at /opt/nod/certs (see docker-compose).
CMD ["python", "node/nod_node.py", "--serve", "8642", "--agent", "public-node"]
