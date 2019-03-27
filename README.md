# Productionizing Models

This project contains a prototype of a process for productionizing models in containers. In general, here is how the process works:

* A CLI is provided that automates a lot of this process. It:
    * Queries SAS Model Manager for available models
    * Pulls down model files and base container templates to build a purpose-built container for scoring that particular model
    * Pushes the container to a repo and launches the container on a Kubernetes cluster
    * Executes scoring of a file against that container

See Setup.txt for general setup instructions. This README describes how to set up the environment to run in the images we've configured for the EYAP bootcamp. Please contact [Tyler Freckmann](mailto:tyler.freckmann@sas.com) if you have questions about this.

<img src="img/overview-image.png" width="1200">

## About the project

The jupyter notebook files (.ipynb) contain examples of how to run the CLI. This prototype has been tested and works on 3 environments: Dev, AWS, and GCP. The configuration for these different environments can be found in `cli.properties`. 

## Set Up (on EYAP bootcamp servers)

Make sure you are on the environment you've configured for the EYAP bootcamp. The exercises will use GCP, so we will be verifying and configuring for that environment, but if you'd like to run in Dev or AWS mode, make sure you've configured those environments appropriately according to Setup.txt

### 0.0 Verify User

**WE WILL BE LOGGING IN AS CLOUD-USER AND REMAIN AS CLOUD-USER FOR THE DURATION OF THE EXERCISES. MAKE SURE YOU ARE CLOUD-USER.**

```sh
$ whomai
cloud-user
```

### 0.1 Clone (and fork if you desire) this repo into your home directory

```sh
cd ~
git clone https://gitlab.sas.com/eyapbootcamp/thursday.git
cd thursday
```

### 0.2 Verify Docker, Kubernetes, and GCP configuration

Verify Docker is installed:

```sh
docker --version
```

Verify Kubernetes kubectl is installed (Don't worry if you get a connection error. Just make sure the command is recognized.)

```sh
kubectl version
```

Make sure your GCP account is configured with:

```sh
gcloud info
```

The expected output should contain an account, project, and compute region and zone toward the bottom of the response like so:

```
Account: [tyler.freckmann@sas.com]
Project: [sas-tyfrec]

Current Properties:
  [core]
    project: [sas-tyfrec]
    account: [tyler.freckmann@sas.com]
    disable_usage_reporting: [True]
  [compute]
    region: [us-east1]
    zone: [us-east1-b]
```

Make sure you're logged in as your SAS account, and the project you are working in is `sas-<YOUR_USER>`. The region and zone don't matter, but make sure they are set to something.

If this is not the case, run `gcloud init`, select your `sas-<USER>` project, and configure a default zone (doesn't matter which but choose one).

### 0.3 Run the setup script

```sh
./setup.sh
```

This setup script does the following (necessary for running this prototype):
* Makes `/workshop` accessible to cloud-user
* Adds cloud-user to the docker group
* Installs anaconda3
* Sets up jupyter notebook
* Installs required python packages for this CLI
* Mounts the astore directory of the remote Model Manager environment for the CLI to access
* Configures gcloud to use docker
* Creates a Google Kubernetes Engine (GKE) cluster
* Opens the GCP firewall to the applications we'll be running on that cluster

**AFTER THE SCRIPT RUNS, YOU NEED TO LOG BACK IN TO A NEW SHELL TO ASSUME THE NEWLY CREATED PERMISSIONS AND PROPERTIES**

### 0.4 Acquire GCP service account key

While the above script is running, sign into [GCP](https://console.cloud.google.com) as your SAS account and make sure you are in your sas-<USER> project.

Using the left-side navigation bar, find "APIs & Services" -> "Credentials":

![gcp-apis-credentials](img/Credentials1.PNG)

Select "Create credentials" -> "Service account key":

![gcp-cred2](img/cred2.PNG)

Select "Compute Engine default service account". Make sure JSON is selected. Click "Create" and download the key:

![gcp-cred3](img/cred3.PNG)

## 0 Docker, the Kubernetes client, and the AWS/GCP/Azure CLIs

The CLI uses Docker, the Kubernetes client, and the various cloud CLIs in order to deploy the scoring containers.

Make sure that you've gone through the following pre-work steps:

1. [Pre-work 01](https://gitlab.sas.com/eyapbootcamp/prework/blob/master/01-openstack-basics.md)
2. [Pre-work 02](https://gitlab.sas.com/eyapbootcamp/prework/blob/master/02-docker-basics.md)

## 1 Install Anaconda3 and relevant python packages

The CLI uses Python 3 and a couple other packages. We install them below.

**Make sure you are yourself (e.g. tyfrec)** and download and install Anaconda3:

```sh
cd /tmp
curl https://repo.anaconda.com/archive/Anaconda3-2018.12-Linux-x86_64.sh -Lvo Anaconda.sh
chmod +x Anaconda.sh
./Anaconda.sh -b -p /workshop/anaconda3 
cd
export PATH="/workshop/anaconda3/bin:$PATH"
```

(You'll have to export the apropriate python path for any subsequent shell sessions)

Verify that you've successfully installed python 3:

```sh
$ python --version
Python 3.7.1
```

Install the relevant python packages:

```sh
pip install docker "kubernetes==8.0.1" python-slugify boto3
```

## 2 Mount the astore directory of your Viya environment

We must mount the shared astore directory of our Model Manager environment for now, until the CLI has a better way to download astore files from Model Manager.

```sh
sudo mkdir /astore
sudo mount eyap-mas.gtp-americas.sashq-d.openstack.sas.com:/opt/sas/viya/config/data/modelsvr/astore /astore/
```

## 3 Download this repo

```sh
cd ~
git clone https://gitlab.sas.com/eyapbootcamp/thursday.git
cd thursday
```

## 4 Configure GCP

### 4.1 Set up GCP GKE (Kubernetes) cluster for model deployments

1. Configure Docker to use gcloud tool to authenticate requests

```sh
gcloud auth configure-docker
```

2. Go to [Google Cloud Platform Console](https://console.cloud.google.com/) and make sure you are signed into your SAS account and project that you have been using for the class.
3. Navigate to the Kubernetes Engine and create a new cluster to host the scoring applications. Name it whatever you want (I'm naming mine eyap-mas) and keep all the defaults. It will take a few minutes to spin up.
4. Navigate to APIs & Services > Credentials
5. Select Create Credentials > Service account key
6. Select "Compute Engine default service account". Make sure JSON is selected. Click "Create" and download the key to your network drive and then inside the eyap-mas repository. (U:\eyapmas drive on Windows or \\\\sashq\\root\\u\\<YOUR_USERNAME>\\eyapmas). Or move it there after the fact. The CLI needs this key.
7. Fetch cluster endpoint and auth data and update kubeconfig entry (auth token expires every 60 mins). Replay CLUSTER with your Kubernetes cluster name below (eyap-mas in my case) and ZONE with your zone (us-central1-a in my case)

```sh
CLUSTER="eyap-mas"
ZONE="us-central1-a"
gcloud container clusters get-credentials $CLUSTER --zone $ZONE
kubectl get nodes
```

8. Configure firewall to allow the node port range (30000-32767)

```sh
gcloud compute firewall-rules create gke-rule --allow tcp:30000-32767
```

9. Get the GCP Kubernetes Engine context. Run the following command and take note of the context (current-context value). It should be something like `gke_project-name_zone_cluster-name`. We'll need to to set up the CLI.

```sh
kubectl config view
```

### 4.2 Configure CLI properties

1. Open cli.properties, and perform the following modifications
2. Under `[CLI]`, comment out `provider.type=Dev`, and uncomment `provider.type=GCP`
3. Under `[SAS]`, set `model.repo.host` to `http://eyap-mas.gtp-americas.sashq-d.openstack.sas.com`
4. Even though we're not using the `[DEV]` environment, for good practice, let's change it to our personal settings: Set `base.repo` to `docker.sas.com/<YOUR_USERNAME>/`. Set `base.repo.web.url` to `docker.sas.com/repository/<YOUR_USERNAME/`
5. You can set the `[AWS]` settings later (if you'd like to deploy to an AWS kubernetes).
6. Under `[GCP]` set `project.name` to your project name
7. Under `[GCP]` set `service.account.keyfile` to the name of the keyfile you created earlier (sas-tyfrec-209092a0e3d2.json)
8. Under `[GCP]` set `base.repo.web.url` to your GCP Docker repo. It will look like this: `console.cloud.google.com/gcr/images/<YOUR-PROJECT-NAME>`
9. Under `[GCP]` set `kubernetes.context` to the kubernetes context you got from the `kubeclt config view` command. Something like: `gke_project-name_zone_cluster-name`

## 5 Configure mmAuthorization.py

Open the mmAuthorization.py file in this repo to edit the authorization info for Model Manager.

In the `getAuthToken` function on line 29, change `user` and `password` to be `viyademo01` and `lnxsas`.

## 6 Start Jupyter Notebook to walk through demo

We need to configure jupyter notebook to be externally accessible. Run the following command to generate a jupyter notebook config file:

```sh
jupyter notebook --generate-config
```

It will create the following config file: `~/.jupyter/jupyter_notebook_config.py`. Open it up and edit it as follows:

1. Find line 82, uncomment it and set it as follows: `c.NotebookApp.allow_remote_access = True`
2. Find line 204, uncomment it and set it as follows: `c.NotebookApp.ip = '*'`
3. Find line 267, uncomment it and set it as follows: `c.NotebookApp.open_browser = False`

Then, run the jupyter notebook from this directory (eyapmas):

```sh
jupyter notebook
```

It will print out a link for you to copy/paste into your browser. Something like: http://(hostname or 127.0.0.1):8888?token=asldkf. Copy/Paste it into a browser, but edit out the ()'s and "or 127.0.0.1" portions so that it will actually work. Fundamentally you need to hit your host at port 8888 with the provided token.

# Walk through script

Once you hit that jupyter notebook, click on the Docker CLI-GCP.ipynb notebook and we can walk through the examples together.
