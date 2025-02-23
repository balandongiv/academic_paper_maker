# How to install
grobid require wsl
-   The usage assume you already have wsl installed on your windows machine
- In my case, Im using wsl2 with ubuntu 22.04
- we also need to have docker, and should be running when we are using grobid


The process for retrieving and running the image is as follow:

    Pull the image from docker HUB (check the latest version number):

> docker pull grobid/grobid:${latest_grobid_version}

Current latest version:

> docker pull grobid/grobid:0.8.1

    Run the container:

Then, open the ubuntu terminal and run the following command:
> docker run --rm --gpus all --init --ulimit core=0 -p 8070:8070 grobid/grobid:0.8.1
Then, any browser (tested with firefox and chrome), open http://localhost:8070/

https://grobid.readthedocs.io/en/latest/Grobid-docker/