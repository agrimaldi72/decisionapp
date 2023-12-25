FROM alpine:3.18.4
RUN apk add --no-cache python3-dev \
    && python3 -m ensurepip --upgrade \
    && pip3 install --upgrade pip \
    && mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN pip3 --no-cache-dir install -r requirements.txt
COPY decisionApp.py /app
EXPOSE 5000
CMD ["python3","decisionApp.py"]

