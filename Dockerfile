FROM python:3.14.0rc1-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir boto3 python-dotenv
COPY .env /app/.env
EXPOSE 80
CMD ["python", "appconfig_demo.py"]
