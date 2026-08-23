FROM python:3.12-slim
WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scheduler ./scheduler
RUN pip install --no-cache-dir -e scheduler
COPY apps/api/alembic.ini .
COPY apps/api/alembic ./alembic
COPY apps/api/app ./app
EXPOSE 8000
