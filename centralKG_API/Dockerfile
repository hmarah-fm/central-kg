# see https://hub.docker.com/r/anaconda/miniconda
FROM anaconda/miniconda:26.5.3

RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

RUN conda install -c conda-forge fastapi
RUN conda install conda-forge::pydantic

RUN pip install fastapi[all] python-dotenv requests uvicorn

WORKDIR /app

COPY ./main.py ./telemetry_rdf.py ./

#see https://docs.docker.com/reference/dockerfile/#cmd
CMD ["uvicorn",  "main:app",  "--host",  "0.0.0.0",  "--port", "8000"]