FROM python:3.11

# Set working directory
WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

# Command to run the app
CMD ["python", "app.py"]