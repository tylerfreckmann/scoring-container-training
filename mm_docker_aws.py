import base64, docker, boto3
import subprocess

# return aws ecr registry url and docker client
def login():
    print('Login into AWS ECR...')
    docker_client = docker.from_env()
    ecr_client = boto3.client('ecr')
    token = ecr_client.get_authorization_token()
    username, password = base64.b64decode(token['authorizationData'][0]['authorizationToken']).decode().split(':')
    registry = token['authorizationData'][0]['proxyEndpoint']
    #print(username, password, registry)
    try:
        docker_client.login(username, password, registry=registry)
    except docker.errors.APIError as err:
        print("Failed to login AWS ECR! Please check your AWS configuration!")
        print(str(err))
        return None
    print("Login AWS ECR succeeded!")
    return registry

# return true if exists
def check_ecr_repo(name):
    print('Checking remote repo', name, 'in AWS ECR...')
    docker_client = docker.from_env()
    ecr_client = boto3.client('ecr')
    try:
        response = ecr_client.describe_repositories(repositoryNames=[name])
    except:
        return False
    return True
    
def create_ecr_repo(name):
    print('Creating remote repo', name, 'in AWS ECR...')    
    docker_client = docker.from_env()
    ecr_client = boto3.client('ecr')
    # checking existence
    try:
        response = ecr_client.describe_repositories(repositoryNames=[name])
    except:
        ecr_client.create_repository(repositoryName=name)

def get_auth_config_payload():
    docker_client = docker.from_env()
    ecr_client = boto3.client('ecr')
    token = ecr_client.get_authorization_token()
    username, password = base64.b64decode(token['authorizationData'][0]['authorizationToken']).decode().split(':')
    auth_config_payload = {'username': username, 'password': password}
    return auth_config_payload

def get_aws_token(cluster_name):
    args = ("aws-iam-authenticator", "token", "-i", cluster_name, "--token-only")
    popen = subprocess.Popen(args, stdout=subprocess.PIPE)
    popen.wait()
    return popen.stdout.read().rstrip()
