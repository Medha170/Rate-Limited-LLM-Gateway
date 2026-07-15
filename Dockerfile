# 1. Use an official, lightweight Python environment
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy our requirements file first to take advantage of Docker caching
COPY requirements.txt .

# 4. Install all the necessary Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of our application code into the container
COPY . .

# 6. Expose the network port our app runs on (FastAPI defaults to 8000)
EXPOSE 8000

# 7. The command to launch our server when the container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]