FROM python:3.6.8


WORKDIR /papaya_server

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

ENV INCLUSTER_K8S_CONFIG 1
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV FLASK_APP papaya_server

ENV NOT_BUILDING 1

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]