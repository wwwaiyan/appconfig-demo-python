FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir boto3 python-dotenv
COPY .env /app/.env
EXPOSE 8080
CMD ["python", "appconfig_demo.py"]
