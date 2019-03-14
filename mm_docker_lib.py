import argparse
import configparser
import os
import sys
import shutil
import zipfile
import datetime
import time
import uuid
import docker
import collections
import kubernetes
#make sure it is python-slugify
from slugify import slugify
from collections import OrderedDict
import mm_docker_k8s as utils
import mm_docker_aws
import mm_docker_gcp
import traceback
import json
import fileinput
import requests
import mmAuthorization

## version 0.4.2

logs_folder_name = "logs"
log_file_name = "cli.log"
host_port=8080
container_port=8080

cur_path = os.path.dirname(__file__)
logs_folder = os.path.join(cur_path, logs_folder_name)

if not os.path.isdir(logs_folder):
        os.mkdir(logs_folder)
log_file_full_path = os.path.join(logs_folder, log_file_name)

# load kubernetes config
def initK8s(context1):
    print("Initializing kubernetes configuration...", context1)
    try:
        kubernetes.config.load_kube_config(context=context1)
        k8s_beta = kubernetes.client.ExtensionsV1beta1Api()
        print("Initialized kubernetes configuration.")
        return True
    except:
        print("Failed initializing kubernetes configuration!")
        print(traceback.format_exc())
        return False
    
def convert_base_repo(registry):
        # remove https or http prefix
        registry = registry.lower()
        if 'http://' in registry:
            base_repo = registry[7:]
        elif 'https://' in registry:
            base_repo = registry[8:]
        else:
            base_repo = registry
        if not base_repo.endswith('/'):
            base_repo = base_repo + '/'
        return base_repo

# load configuration from file
# if provider value is passed in, it will overwrite the setting in cli.properties
# return False if failed
def initConfig(p=None):
    global model_repo_host
    global base_repo
    global base_repo_web_url
    global verbose_on
    global provider
    global kubernetes_context

    print("Loading configuration properties...")
    
    try:
        config = configparser.RawConfigParser()
        config.read('cli.properties')
        model_repo_host = config.get('SAS', 'model.repo.host');
        if config.has_option('CLI', 'verbose') and config.get('CLI', 'verbose') == 'True':
            verbose_on = True
        else:
            verbose_on = False

        if verbose_on:
            utils.setDebug(True)

        if p != None:
            provider = p
        else:
            if config.has_option('CLI', 'provider.type'):
                provider = config.get('CLI', 'provider.type')
            else:
                provider = 'Dev'
        
        base_repo_web_url = config.get(provider, 'base.repo.web.url');
        kubernetes_context = config.get(provider, 'kubernetes.context');
        
        if provider == 'AWS':
            # set aws profile in os env 
            aws_profile = config.get(provider, 'aws.profile');
            os.environ["AWS_PROFILE"] = aws_profile    

            # login amazon ecr
            registry = mm_docker_aws.login()
            if registry is None:
                return False
            base_repo = convert_base_repo(registry)
        elif provider == 'GCP':
            # login Google Container Registry
            key_file = config.get(provider, 'service.account.keyfile');
            project = config.get(provider, 'project.name');
            printmsg("key file:",key_file)
            printmsg("project name:",project)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS']=key_file
            registry = mm_docker_gcp.login(key_file, project)
            if registry is None:
                return False
            base_repo = convert_base_repo(registry)
        else:
            base_repo = config.get(provider, 'base.repo');
            
        if not initK8s(kubernetes_context):
            print("Please check environment settings.")
            return False
        
    except Exception as e:        
        print("Error loading configuration from cli.properties file! Double-check Docker daemon or other environment.")
        print(traceback.format_exc())
        return False
        
    print('  verbose:', verbose_on)
    print('  model.repo.host:', model_repo_host)
    print('  provider.type:', provider)
    print('  base.repo:', base_repo)
    print('  base.repo.web.url:', base_repo_web_url)
    print('  kubernetes.context:', kubernetes_context)

    print("===================================")
    return True
    

######
# timestamp, command, arguments, results
def log(*args):
    current_time = str(datetime.datetime.now())
    with open(log_file_full_path, 'a', encoding = 'utf-8') as f:
        f.write(current_time+',' + ','.join(args)+'\n')

def display_last_lines(file_name, number=None):
    with open(file_name, "r", encoding = 'utf-8') as f:
        all_logs = list(f)
        count=0
        for line in reversed(all_logs):
            if number == 'all' or number is None or count < int(number):
                print(line)
            count=count+1

def lastlogs(number=None):
    display_last_lines(log_file_full_path, number)

# wait for service up
def wait_for_service_up(service_url):
    num=0
    while num< 10:
        num=num+1
        print('Checking whether the instance is up or not...')
        # timeout is 1 second
        try:
            r = requests.get(service_url, timeout=30)
            if r.status_code == 200 and r.text == 'pong':
                print('Instance is up!')
                return(True)
        except:
            print(num, '==Sleep 10 seconds...')
            time.sleep(10)

######
def listmodel(key=None):
    global base_repo
    global model_repo_host
    printmsg("Getting model list...")
    try:
        mmAuth = mmAuthorization.mmAuthorization("myAuth")
        authToken = mmAuth.getAuthToken(model_repo_host)
        headers={
            mmAuthorization.AUTHORIZATION_HEADER:mmAuthorization.AUTHORIZATION_TOKEN+ authToken
        }
    except:
        raise RuntimeError("ERROR! Failed to auth token")

    models_url = model_repo_host + "/modelRepository/models?limit=999&start=0"
    try:        
        response = requests.get(models_url, headers=headers)
        jsondata = response.json()
        models=jsondata['items']
        if len(models) > 0:
            for model in models:
                #print(model)
                model_name = model['name']
                model_name = model_name.lower()
                model_id = model['id']
                model_version = model['modelVersionName']
                if key != None:
                   key = key.lower()
                # ignore if there's partial key and the model name doesn't have the key (case insensitive)
                if key != None and key != 'all' and key not in model_name:
                    continue
                print("Model name",model_name)
                print("Model UUID",model_id)
                print("Model version",model_version)
                if 'projectName' in model.keys() and model['projectName'] != None:
                    print("Project name",model['projectName'])
                if 'scoreCodeType' in model.keys():
                    print("Score Code Type",model['scoreCodeType'])
                else:
                    print('Warning! No score code type defined!')
                model_name = slugify(model_name)
                tagname = model_name +'_' + model_id                
                repo = base_repo + tagname + ":latest"
                # TODO compare the model version with the image version
                print("Image URL (not verified):",repo)
                print("==========================")
        printmsg("Guides: > python mm_docker_cli.py publish <uuid>")
        printmsg("Guides: > python mm_docker_cli.py launch <image url>")
        printmsg("Guides: > python mm_docker_cli.py score <image url> <input file>")
    except:
        raise RuntimeError("ERROR! Failed to get model list")
    
######
def retrieve_model_info(model_url, headers):
    try:
        response = requests.get(model_url, allow_redirects=True, headers=headers)
        #jsondata = json.loads(response.text)
        jsondata = response.json()
        model_name = jsondata['name']
        model_version_id = jsondata['modelVersionName']
        code_type = jsondata['scoreCodeType']
        printmsg(model_name, model_version_id, code_type)
        return(model_name, model_version_id, code_type)
    except:
        raise RuntimeError("ERROR! Failed to get model file")

# check whether AstoreMetadata.json inside or not
def is_astore_model(z):
    for x in z.namelist():
        if x == 'AstoreMetadata.json':
            return True
    return False

####
def get_astore_name(z):
    if is_astore_model(z):
        for x in z.namelist():
            if x.startswith("_"):
                return x
    return None

####
def extract_req_file(z, subfolder):
    for x in z.namelist():
        if x == 'requirements.json':
            z.extract("requirements.json", subfolder)
            return x
    return None

#####
# WARNING: the shared astore directory (MM cluster) should be able to be mounted in current
# system where the CLI is being running!

# add astore file if need
def copy_astore(subfolder, zip_file):

    f = zipfile.ZipFile(zip_file, "r")
    astore_file_name = get_astore_name(f)
    f.close()
    if astore_file_name == None:
        return
    if not astore_file_name.endswith('.astore'):
        astore_file_name = astore_file_name + ".astore"
        
    print("Copying astore from shared directory...")
    printmsg("Make sure that the shared directory has been mounted locally")
    printmsg("For Windows, the local directory will be at z drive")
    printmsg("For Linux, the local directory will be /astore")
    if os.name == 'nt':
        prefix = "z:/"
    else:
        prefix = "/astore/"
    printmsg(prefix+ astore_file_name)
    if (os.path.isfile(prefix+ astore_file_name)):
        printmsg(subfolder)
        shutil.copy(prefix+ astore_file_name, subfolder)
        os.chmod(os.path.join(subfolder, astore_file_name), 0o777)
    
##########
# prepare the dependency lines from requirements.json 
# and append them before ENTRYPOINT in Dockerfile
####
def add_dep_lines(subfolder):
    # search for special requirements.json file
    requirements_with_full_path = os.path.join(subfolder, 'requirements.json')
    if not os.path.isfile(requirements_with_full_path):
        return
    print("Installing dependencies defined from requirements.json...")
    dep_lines = ''
    with open(requirements_with_full_path) as f:
        json_object = json.load(f, object_pairs_hook=OrderedDict)
        for row in json_object:
            step = row['step']
            command = row['command']
            dep_lines = dep_lines + '#'+step+'\n'
            dep_lines = dep_lines + 'RUN '+command+'\n'
    dockerfile_path = os.path.join(subfolder, 'Dockerfile')
    printmsg('Inserting dependency lines in Dockerfile')
    printmsg(dep_lines)
    for line in fileinput.FileInput(dockerfile_path,inplace=1):
        if line.startswith("ENTRYPOINT"):
            line=line.replace(line, dep_lines+line)
        print(line,end='')

# unzip the requirements.json from model zip file if available
# examine the requirements.json and include the command lines into Dockerfile in the same subfolder
def handle_dependencies(subfolder, zip_file):
    f = zipfile.ZipFile(zip_file, "r")
    req_file_name = extract_req_file(f, subfolder)
    f.close()
    if req_file_name == None:
        return
    add_dep_lines(subfolder)

######
#  push the image to remote repo
######
def push_to_repo(myimage, tagname, version_id):
    global base_repo_web_url
    global base_repo
    global provider
    repo = base_repo + tagname
    
    printmsg("Docker repository URL: ", base_repo)
    
    if provider == 'AWS':
        mm_docker_aws.create_ecr_repo(tagname)
        
    # default is latest, always using latest
    remote_version_tag = repo + ':' + version_id
    remote_version_latest = repo + ':latest'
    
    printmsg(remote_version_tag)
    if myimage.tag(repo, version_id) is False:
        raise RuntimeError("failed on tagging")

    if myimage.tag(repo, "latest") is False:
        raise RuntimeError("failed on tagging remote latest")
    
    print("Pushing to repo...")

    client = docker.from_env()
    if provider == 'AWS':
        auth_config = mm_docker_aws.get_auth_config_payload()
        result = client.images.push(remote_version_tag, auth_config=auth_config)
        result = client.images.push(remote_version_latest, auth_config=auth_config)
    else:
        result = client.images.push(remote_version_tag)
        result = client.images.push(remote_version_latest)
    #print(result)
    image_repo_web_url = base_repo_web_url + tagname + "/"
    print("Pushed. Please verify it at", image_repo_web_url)
    print("Model image URL:", remote_version_latest)
    return(remote_version_latest)


# return True if good
def url_ok(image_url):
    global provider
    
    print("Validating image repository url...")
    client = docker.from_env()
        
    try:
        if provider == 'AWS':
            auth_config = mm_docker_aws.get_auth_config_payload()
            client.images.pull(image_url, auth_config=auth_config)
        else:
            client.images.pull(image_url)
    except Exception as e:
        print("Failed on validating", image_url)
        print(traceback.format_exc())
        return False
    print("Completed validation.")    
    return True

######
def publish(model_id):
    """
 * Get model by model_id and always getting the latest version.
 * Get model by name, project, version, repository, etc
 * Retrieve model zip file from model respository, such as modelxxxxxx.zip
 * Get astore by scp temporarily until the other method is ready to pull astore file from the SAS server
 * create subfolder <tag>, and store zip file and template files in subfolder
 * return image url if succeed
    """
    global model_repo_host
    
    if model_id is None:
        raise RuntimeError('Error! Model UUID is empty')
    
    print("Downloading model", model_id,"from model repository...")

    # images folder under the current directory
    data_path = os.path.join(cur_path, 'images')
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    printmsg("Images folder:", data_path)

    filename = "model-"+model_id+".zip"
    # remove extension
    tmpname = os.path.splitext(filename)[0]
    # must be lowercase
    tmpname = tmpname.lower()

    subfolder = os.path.join(data_path, tmpname)
    if not os.path.exists(subfolder):
        os.makedirs(subfolder)
 
    model_file_full_path = os.path.join(subfolder, filename)

    try:
        mmAuth = mmAuthorization.mmAuthorization("myAuth")
        authToken = mmAuth.getAuthToken(model_repo_host)
        headers={
            mmAuthorization.AUTHORIZATION_HEADER:mmAuthorization.AUTHORIZATION_TOKEN+ authToken
        }
    except:
        raise RuntimeError("ERROR! Failed to auth token")

    model_url = model_repo_host + "/modelRepository/models/"+model_id
    try:
        #http://<host>/modelRepository/models/d00bb4e3-0672-4e9a-a877-39249d2a98ab?format=zip
        result_url = model_url+"?format=zip"
        r = requests.get(result_url, allow_redirects=True, headers=headers)
        #print(r.status_code)
        if r.status_code == 404:
            raise RuntimeError("ERROR! Failed to get model file")

        open(model_file_full_path, 'wb').write(r.content)
        printmsg("Model zip file has been downloaded at",model_file_full_path)
    except:
        raise RuntimeError("ERROR! Failed to get model file")

    # get model_name, version_id, code_type too
    model_name, version_id, code_type=retrieve_model_info(model_url, headers)
    
    # verify meta data
    if model_name == None or version_id == None:
        raise RuntimeError('Unable to retrieve model name or current version!')

    model_name = slugify(model_name)
    printmsg("The name has been normalized to", model_name)
    
    if code_type == 'python' or code_type == 'Python':
        template_folder_name = 'template-py' # pyml-base
    elif code_type == 'R' or code_type == 'r':
        template_folder_name = 'template-r' # r-base
    else:
        template_folder_name = 'template'  # maspy-base
        
    template_folder = os.path.join(cur_path, template_folder_name)
    if not os.path.exists(template_folder):
        raise RuntimeError("Template folder not existed!")

    dockerfile = os.path.join(template_folder, 'Dockerfile')
    # make sure that one of files is named after Dockerfile
    if not os.path.isfile(dockerfile):
        raiseError("There's no Dockerfile under template folder")  

    printmsg("Template folder:", template_folder)
    
    # copy template files into subfolder
    src_files = os.listdir(template_folder)
    for file_name in src_files:
        full_file_name = os.path.join(template_folder, file_name)
        if (os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, subfolder)

    # download astore file if available
    copy_astore(subfolder, model_file_full_path)
    
    # read requirements.json from zip file if available 
    # and include the dependency lines in Dockerfile
    handle_dependencies(subfolder, model_file_full_path)

    tagname = model_name +'_' + model_id   

    local_tag = tagname + ':' + version_id
    local_tag_latest = tagname + ':latest'

    # build local image with docker daemon
    client = docker.from_env()

    print("Building image...")
    printmsg(local_tag)
    myimage, _ = client.images.build(path=subfolder, tag=local_tag, nocache=True)
    # tag it as latest version too
    printmsg(local_tag_latest)
#    myimage.tag(local_tag_latest)
    myimage.tag(tagname, "latest")

    printmsg("Tag the image into a repository", myimage.short_id)
    remote_version_latest = push_to_repo(myimage, tagname, version_id)
    
    printmsg("==========================")
    printmsg("Guides: > python mm_docker_cli.py launch", remote_version_latest)
    printmsg("Guides: > python mm_docker_cli.py score", remote_version_latest,"<input file>")
    log('publish',model_id, version_id, remote_version_latest)
    return(remote_version_latest)
   
def launch(image_url):
    """
 * submit request to kubernetes to start a pod instance
 * return deployment_name and service url
    """
    global provider
    global kubernetes_context

    if not url_ok(image_url):
        return

    print("Launching container instance...")    
    printmsg(image_url)
    
    # get the model_name
    tagname = image_url.rsplit('/', 1)[-1]
    tagname = tagname.rsplit('_', 1)[0]
    tagname = slugify(tagname)
    # make sure it is not more than 64 characters
    printmsg(tagname)
    deployment_name, service_url = utils.deploy_application(provider, kubernetes_context, tagname, image_url, host_port, container_port)
    printmsg("==========================")
    if service_url is None:
       print("Deployment failed! Please check environment settings!")
       stop(deployment_name)
        
    log('launch',image_url,deployment_name, service_url)
    wait_for_service_up(service_url)
    if utils.check_pod_status(kubernetes_context, deployment_name):
        printmsg("Guides: > python mm_docker_cli.py execute ", service_url, "<input file>")
        printmsg("Guides: > python mm_docker_cli.py stop", deployment_name)
        return(deployment_name, service_url)
    else:
        print("Deployment failed! Please check docker image url!")
        stop(deployment_name)

def execute(service_url, csv_file):
    print("Performing scoring in the container instance...") 
    printmsg("service_url:", service_url)
    printmsg("csv_file:", csv_file)
    if not os.path.isfile(csv_file):
        raise RuntimeError('Error! Test data file doesn\'t exist!')
                           
    if not service_url.endswith('/'):
        service_url = service_url + '/'
    execution_url = service_url + 'executions'
    headers = {
       'Accept': 'application/json'
       # don't send Content-type header by self
       #'Content-Type': 'multipart/form-data'
    }
    file_name = os.path.basename(csv_file)
    files = {
        'file': (file_name, open(csv_file, 'rb'), 'application/octet-stream')
        }

    # r = requests.post(url, files=files, data=data, headers=headers)
    response = requests.post(execution_url, files=files, headers=headers)
    
    resp_json = response.json()

    if response.status_code != 201:
        printmsg(response.content)
        raise RuntimeError('Error! Failed to perform score execution!'+resp_json)
    
    printmsg(resp_json)
    test_id = resp_json['id']
    print('The test_id from score execution:', test_id)
    printmsg("==========================")
    printmsg("Guides: > python mm_docker_cli.py query", service_url, test_id)
    dest_file = os.path.join(logs_folder, test_id +'_input.csv')
    shutil.copy(csv_file, dest_file)
    log('execute',service_url, dest_file, test_id)
    return(test_id)

def query(service_url, test_id):
    printmsg("service_url:", service_url)
    printmsg("test_id:", test_id)

    if not service_url.endswith('/'):
        service_url = service_url + '/'

    result_file = test_id + '.csv'    
    result_url = service_url + 'query/'+result_file
    
    r = requests.get(result_url, allow_redirects=True)
    open(result_file, 'wb').write(r.content)
    print("The test result has been retrieved and written into file", result_file)
    
    print("Head is the first 5 lines")
    with open(result_file) as myfile:
        max=5
        for line in myfile:
            max=max-1
            print(line.strip())
            if max<1:
                break
            
    printmsg("==========================")
    printmsg("Guides: 1) remember to stop instance after uage. You can find the deployment name by running")
    printmsg("    > kubectl get deployment")
    printmsg("Then execute: > python mm_docker_cli.py stop <deployment_name>")
    printmsg("Guides: 2) if result file includes error message, you could find the pod name and debug inside the instance as below")
    printmsg("    > kubectl get pod")
    printmsg("    > kubectl exec -it <pod name> -- /bin/bash")
    shutil.move(result_file, os.path.join(logs_folder,result_file) )
    log('query',service_url, test_id, result_file)    
    return(result_file)

def systemlog(service_url):
    printmsg("Retrieving systemlog from container...")
    printmsg("service_url:", service_url)

    if not service_url.endswith('/'):
        service_url = service_url + '/'

    result_url = service_url + 'systemlog'
    systemlog_file = 'gunicorn.log'

    r = requests.get(result_url, allow_redirects=True)
    # just override
    open(systemlog_file, 'wb').write(r.content)
    print("The system log has been retrieved and written into file",systemlog_file)

    print("Displaying the last 5 lines")
    display_last_lines(systemlog_file, 5)
    return(systemlog_file)

def stop(deployment_name):
    """
 * Accept name=<deployment_name>
 * submit request to kubernetes to stop a pod instance and delete the deployment
    """
    global provider
    global kubernetes_context
    
    if deployment_name is None:
        raise RuntimeError('Error! Deployment name is empty!')

    printmsg(deployment_name)
    
    if utils.delete_application(provider, kubernetes_context, deployment_name):
        log('stop',deployment_name)
        print('Deletion succeeded')
    else:
        raise RuntimeError('Deletion failed')

def score(image_url, csv_file):
    deployment_name, service_url = launch(image_url)
    print("===============================")
    test_id = execute(service_url, csv_file)
    print("===============================")
    query(service_url, test_id)
    print("===============================")
    stop(deployment_name)

def setVerbose(b):
    global verbose_on
    print("Verbose:",b)
    verbose_on = b
    
def printmsg(*args):
    global verbose_on
    if verbose_on:
        print(*args)

