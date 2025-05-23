FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY src/ ./src/
COPY config/ ./config/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["python", "src/main.py"]