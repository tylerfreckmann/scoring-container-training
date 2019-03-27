#!/bin/bash

# make /workshop accessible to me
sudo chmod 777 /workshop

# add me to docker group
sudo usermod -aG docker $(whoami)

# install anaconda3
PREFIX=/workshop/anaconda3
cd /tmp
curl https://repo.anaconda.com/archive/Anaconda3-2018.12-Linux-x86_64.sh -Lvo Anaconda.sh
chmod +x Anaconda.sh
./Anaconda.sh -b -p $PREFIX
rm ./Anaconda.sh
cd

# add anaconda3 to path
cat >> ~/.bashrc << EOF
# added by Anaconda3 2018.12 installer
# >>> conda init >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="\$(CONDA_REPORT_ERRORS=false '$PREFIX/bin/conda' shell.bash hook 2> /dev/null)"
if [ \$? -eq 0 ]; then
    \\eval "\$__conda_setup"
else
    if [ -f "$PREFIX/etc/profile.d/conda.sh" ]; then
        . "$PREFIX/etc/profile.d/conda.sh"
        CONDA_CHANGEPS1=false conda activate base
    else
        \\export PATH="$PREFIX/bin:\$PATH"
    fi
fi
unset __conda_setup
# <<< conda init <<<
EOF

# activate anaconda3
source ~/.bashrc

# set up jupyter notebook
mkdir ~/.jupyter
cat >> ~/.jupyter/jupyter_notebook_config.py << EOF
# Configuration file for jupyter-notebook.
# Make jupyter notebook externally accessible
c.NotebookApp.allow_remote_access = True
c.NotebookApp.ip = '*'
c.NotebookApp.open_browser = False
EOF

# install python packages for mas container CLI
pip install docker "kubernetes==8.0.1" python-slugify boto3

# mount astore directory from Model Manager environment
MODELMANAGERHOST=eyap-mas.gtp-americas.sashq-d.openstack.sas.com
sudo mkdir /astore
sudo mount $MODELMANAGERHOST:/opt/sas/viya/config/data/modelsvr/astore /astore/

# configure GCP
CLUSTERNAME=eyap-mas
gcloud auth configure-docker --quiet
gcloud container clusters create --num-nodes=3                  \
                                   --machine-type="n1-standard-2" \
                                   $CLUSTERNAME
gcloud container clusters get-credentials $CLUSTERNAME
kubectl get nodes
gcloud compute firewall-rules create gke-rule --allow tcp:30000-32767

# restart shell
echo YOU NEED TO LOG BACK IN TO A NEW SHELL TO ASSUME THE NEWLY CREATED PERMISSIONS AND PROPERTIES
