# Use a slim version of the official Python 3.13 image as a base.
FROM python:3.13-slim

# Set environment variables for Poetry to ensure dependencies are installed directly
# into the Docker container's system site-packages (fixes the previous error).
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/root/.local/bin:$PATH"

# Set the working directory in the container.
WORKDIR /usr/src/app

# 1. Install necessary system packages (tar and gzip) for extracting the artifact.
# This step is often necessary for 'slim' base images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tar gzip \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Poetry using pip. We use a fixed version for stability.
RUN pip install poetry==1.8.3

# 3. Copy only the dependency management files first. This allows Docker to cache the install step.
COPY pyproject.toml poetry.lock ./

# 4. Install the dependencies based on the lock file.
# The --no-root flag prevents installing the project itself as a package,
# as it will be copied and extracted in the next steps.
RUN poetry install --without test --no-root

# --- Application Artifact Steps ---

# 5. Copy the pre-built tarball artifact.
# IMPORTANT: This assumes 'dist/' is relative to your Docker build context.
# We use a wildcard '*' to match the version number in the filename.
COPY dist/features_pipeline-*.tar.gz ./

# 6. Extract the artifact and clean up the tarball.
# --strip-components=1 removes the top-level directory, placing contents directly in /usr/src/app.
RUN tar -xzf features_pipeline-*.tar.gz --strip-components=1 \
    && rm features_pipeline-*.tar.gz \
    && echo "--- Contents after extraction ---" \
    && ls -lR

# 7. Copy the .env file now that the application structure is in place.
COPY .env .

# Copy run script
COPY dev.py ./

# Set the entrypoint to use poetry's executable.
ENTRYPOINT ["poetry", "run"]

# The command is updated to look inside the package directory: features_pipeline/main.py.
# This is the standard location for source files in a Poetry-built sdist.
CMD ["python", "dev.py"]
