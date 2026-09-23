# VYBE — single-image build (Section 31).
#
# Stage 1 builds the React frontend; stage 2 is the Python/FastAPI backend,
# which serves the API on /api/* and the built frontend as static files on
# everything else (app/main.py mounts VYBE_STATIC_DIR when set). One image,
# one container, one port - the simplest way to containerize this cleanly
# per CLAUDE.md Section 31's "serve the built React app as static files
# from the backend" option.
#
# GPU access inside the container is NOT automatic - see docker-compose.yml
# and the README's "Installation — Docker" section for the NVIDIA Container
# Toolkit host prerequisite.

FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# StaticFiles(html=True) falls back to 404.html for unmatched paths (e.g.
# /history/<id>) - copying index.html there lets client-side routing
# (react-router) take over on a full-page load of a deep link.
RUN cp dist/index.html dist/404.html

FROM python:3.12-slim AS backend
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/run.py ./run.py
COPY --from=frontend-build /frontend/dist ./static

ENV VYBE_STATIC_DIR=/app/static
ENV VYBE_DATA_DIR=/app/data
ENV VYBE_HOST=0.0.0.0
ENV VYBE_PORT=8000

EXPOSE 8000

CMD ["python", "run.py"]
