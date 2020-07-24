FROM python:3.8

USER root
COPY requirements.txt /tmp/
RUN pip install --upgrade pip --no-cache-dir && \
    python -m pip install -r /tmp/requirements.txt --no-cache-dir
WORKDIR /workspace
#COPY files/ /workspace/.
CMD ["/bin/bash", "flask/files/start.sh"]
