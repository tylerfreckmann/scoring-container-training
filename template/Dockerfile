From docker.sas.com/honxin/maspy-base:latest
MAINTAINER Hongjie Xin <Hongjie.xin@sas.com>
LABEL docker image with embedded SAS model

# copy both zip and/or astore file (if any) to model directory
COPY *.* /pybox/model/

#ENTRYPOINT ["/bin/bash"]
ENTRYPOINT ["/bin/bash", "startServer.sh"]


