# Dockerfile to build a Lambda layer containing matplotlib & dependencies
FROM amazonlinux:2

# Install system packages needed for matplotlib
RUN yum -y update && \
    yum -y install python3-devel python3-pip gcc gcc-c++ libX11-devel libXext-devel freetype-devel libpng-devel zlib-devel && \
    yum clean all

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Create a directory to assemble the layer
RUN mkdir -p /opt/python

# Copy requirements file into container
COPY requirements.txt /tmp/requirements.txt

# Install python packages into /opt/python (lambda layer layout)
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt -t /opt/python

# Package the layer
RUN cd /opt && zip -r /opt/matplotlib_layer.zip python

# The resulting file will be at /opt/matplotlib_layer.zip