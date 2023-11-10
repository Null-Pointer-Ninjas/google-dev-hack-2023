# Use the official lightweight Python image.
FROM python:3.9-slim
# Allow statements and log 
ENV PYTHONUNBUFFERED True
# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . $APP_HOME
# Install production dependencies.
RUN pip install -r requirements.txt
# Run
CMD uvicorn main:app --port=8000 --host=0.0.0.0