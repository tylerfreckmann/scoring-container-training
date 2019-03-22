# Set Up

## 0 Docker, the Kubernetes client, and the AWS/GCP/Azure CLIs

The CLI uses Docker, the Kubernetes client, and the various cloud CLIs in order to deploy the scoring containers.

Make sure that you've gone through the following pre-work steps:

1. [Pre-work 01](https://gitlab.sas.com/eyapbootcamp/prework/blob/master/01-openstack-basics.md)
2. [Pre-work 02](https://gitlab.sas.com/eyapbootcamp/prework/blob/master/02-docker-basics.md)

## 1 Install Anaconda3 and relevant python packages

The CLI uses Python 3 and a couple other packages. We install them below.

**Make sure you are yourself (e.g. tyfrec)** and download and install Anaconda3:

```sh
cd ~
wget https://repo.anaconda.com/archive/Anaconda3-2018.12-Linux-x86_64.sh
chmod +x Anaconda3-2018.12-Linux-x86_64.sh
./Anaconda3-2018.12-Linux-x86_64.sh
```

When it asks you where you want to install Anaconda3, put `/workshop/anaconda3`. It will be the prompt after accepting the license like below:

```sh
Anaconda3 will now be installed into this location:
/r/ge.unx.sas.com/vol/vol610/u61/tyfrec/anaconda3

  - Press ENTER to confirm the location
  - Press CTRL-C to abort the installation
  - Or specify a different location below

[/r/ge.unx.sas.com/vol/vol610/u61/tyfrec/anaconda3] >>> /workshop/anaconda3
```

Reply `yes` to the installer initializing Anaconda3 in your `~/.bashrc` file.

Reply `no` to installing VSCode.

Source your `~/.bashrc` file to activate python:

```sh
source ~/.bashrc
```

If had trouble with the .bashrc file, do this:

```sh
export PATH="/workshop/anaconda3/bin:$PATH
```

(Only lasts for this session).


Verify that you've successfully installed python 3:

```sh
$ python --version
Python 3.7.1
```

Install the relevant python packages:

```sh
pip install docker kubernetes python-slugify boto3
```

## 2 Mount the astore directory of your Viya environment

We must mount the shared astore directory of our Model Manager environment for now, until the CLI has a better way to download astore files from Model Manager.

```sh
sudo mkdir /astore
sudo mount gtpisilon.unx.sas.com:/ifs/viyafiles/astore /astore
```

## 3 Download this repo

```sh
cd ~
git clone https://gitlab.sas.com/tyfrec/eyapmas.git
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
6. Select "Compute Engine default service account". Make sure JSON is selected. Click "Create" and download the key to your network drive and then inside the eyap-mas repository. (U:\eyapmas drive on Windows or \\sashq\root\<your_username>\eyapmas). Or move it there after the fact. The CLI needs this key.
7. Fetch cluster endpoint and auth data and update kubeconfig entry (auth token expires every 60 mins). Replay CLUSTER with your Kubernetes cluster name below (eyap-mas in my case) and ZONE with your zone (us-central1-a in my case)

```sh
CLUSTER="eyap-mas"
ZONE="us-central1-a"
gcloud container clusters get-credentials $CLUSTER --zone $ZONE
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

1. Open cli.properties
2. Edit the following properties:
