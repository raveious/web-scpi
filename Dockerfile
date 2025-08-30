FROM python:3.13-alpine3.22

ENV CODE_DIR=/code
ENV CONFIG_DIR=${CODE_DIR}/config
ENV CONFIG_FILE=config.json

WORKDIR ${CODE_DIR}

RUN mkdir -p ${CONFIG_DIR}
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt pip install --no-cache-dir -r /tmp/requirements.txt

COPY *.py ${CODE_DIR}
COPY *.json ${CONFIG_DIR}

#CMD [ "python", "" ]
