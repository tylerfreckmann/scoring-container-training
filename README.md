# Set Up

## 1 Install Anaconda3 and relevant python packages

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

Source your `~/.bashrc` file to activate python: `$ source ~/.bashrc`. If had trouble with the .bashrc file, do this:

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

```sh
sudo mkdir /astore
sudo mount gtpisilon.unx.sas.com:/ifs/viyafiles/astore /astore
```

## 3 Download this repo

```sh
cd ~
git clone https://gitlab.sas.com/tyfrec/eyapmas.git
```