import base64, docker
import subprocess

# return gcp gcr registry url
def login(key_file = None, project = None):
    if key_file == None:
        print("Please specify GCP token key file!")
        return None
    if project == None:
        print("Please specify the project name in GCP!")
        return None
    
    print('Login into GCP GCR...')

    with open(key_file, 'r') as myfile:
        password=myfile.read().replace('\n', '') # remove line break!
    #print(password)

    docker_client = docker.from_env()
    username = "_json_key"
    registry = "https://gcr.io/v2/" + project # https://gcr.io/v2/{project}/{repo}/tags/list
    
    #print(username, password, registry)
    try:
        docker_client.login(username, password, registry=registry)
    except docker.errors.APIError as err:
        print("Failed to login GCP GCR! Please check your gcloud configuration!")
        print(str(err))
        return None
    print("Login GCP GCR succeeded!")
    return "https://gcr.io/"+project

##def get_gcp_token():
##    args = ("gcloud", "auth", "application-default", "print-access-token")
##    popen = subprocess.Popen(args, stdout=subprocess.PIPE)
##    popen.wait()
##    return popen.stdout.read().rstrip()

