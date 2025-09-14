FROM python:3.12-slim-bookworm

COPY src /src
COPY conf /conf
COPY .env* /
COPY requirements.txt /requirements.txt

RUN pip install -r requirements.txt

CMD ["python", "/src/main.py"]
