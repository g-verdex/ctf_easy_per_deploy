FROM python:3.11-slim

WORKDIR /app

# Copy application file
COPY task.py /app/

# Install dependencies
RUN pip install --no-cache-dir flask

# Environment variable for the flag
ENV FLAG="CTF{generic_flag_for_testing}"

# Expose the web server port
EXPOSE 80

# Run the application
CMD ["python", "task.py"]
