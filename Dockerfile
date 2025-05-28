FROM python:3.11-slim AS builder

WORKDIR /app
COPY . .

RUN pip install pyinstaller staticx -r requirements.txt
RUN pyinstaller --onefile --name systeminfo main.py
RUN staticx dist/systeminfo dist/systeminfo-static

# 最终镜像只复制可执行文件，方便导出
FROM scratch AS export
COPY --from=builder /app/dist/systeminfo-static /systeminfo
