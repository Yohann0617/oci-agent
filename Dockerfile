FROM python:3.11-slim AS builder

WORKDIR /app
COPY . .

RUN apt-get install -y build-essential python3-dev patchelf upx scons && rm -rf /var/lib/apt/lists/*
RUN pip install pyinstaller staticx
RUN pip install -r requirements.txt
RUN pyinstaller --onefile --name systeminfo main.py
RUN staticx dist/systeminfo dist/systeminfo-static

FROM scratch AS export
COPY --from=builder /app/dist/systeminfo-static /systeminfo
