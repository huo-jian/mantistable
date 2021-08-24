FROM python:3.6

# The enviroment variable ensures that the python output is set straight
# to the terminal with out buffering it first
ENV PYTHONUNBUFFERED 1
ENV TERM=xterm

# Create root directory for our project in the container
RUN mkdir /mantistable

# Copy the current directory contents into the container
COPY ./requirements.txt /mantistable

# Set the working directory
WORKDIR /mantistable

# Install npm dependecies
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash - && apt-get install -y nodejs && npm install

# Install python requiremensts
RUN pip install -r requirements.txt && python -c 'import nltk; nltk.download("stopwords"); nltk.download("punkt")'
