#================================================= Build Time Arguments ===================================================
# App Related Arguments
ARG PYTHON_VERSION="3.9"


# # Distribution Arguments
ARG ALPINE_VERSION="3.15"

# Set base image (host OS) 
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} 

WORKDIR /app 

COPY requirements.txt requirements.txt


RUN pip install --no-cache-dir --upgrade pip    && \
    pip install --no-cache-dir -r requirements.txt


COPY main.py main.py
CMD ["python","./main.py"]
