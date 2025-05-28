FROM python:3.11-slim AS builder

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y build-essential python3-dev patchelf scons && rm -rf /var/lib/apt/lists/* && \
 pip install --upgrade pip && pip install pyinstaller staticx && \
 pip install -r requirements.txt && \
 pyinstaller --onefile --name systeminfo main.py && \
 staticx dist/systeminfo dist/systeminfo-static

FROM scratch AS export
COPY --from=builder /app/dist/systeminfo-static /systeminfo
