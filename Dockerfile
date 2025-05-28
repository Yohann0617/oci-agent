FROM python:3.11-slim AS builder

WORKDIR /app
COPY . .

RUN pip install pyinstaller staticx && \
    pip install -r requirements.txt && \
    pyinstaller --onefile --name systeminfo main.py && \
    staticx dist/systeminfo dist/systeminfo-static

FROM scratch AS export
COPY --from=builder /app/dist/systeminfo-static /systeminfo
