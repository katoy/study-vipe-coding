FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install flask

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
