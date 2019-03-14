import random
import string
import requests

from kubernetes import client, config
from kubernetes.client import api_client
from kubernetes.client.apis import core_v1_api
from kubernetes.client import configuration as k8s_config
from mm_docker_aws import get_aws_token

DEBUG_ON = False

def setDebug(b):
    global DEBUG_ON
    DEBUG_ON = b
    
def debug(*args):
    if DEBUG_ON:
        print('debug', *args)

# get configured namespace in the context
def get_namespace(context1):
    contexts, active_context = config.list_kube_config_contexts()

    # get namespace value from context
    k8s_namespace = 'default'
    for context in contexts:
        if context1 == context['name']:
            if 'namespace' in context['context']:
                k8s_namespace = context['context']['namespace']
                debug("namespace:", k8s_namespace)
            break
    return(k8s_namespace)
    
def create_deployment_object(deployment_name, container_port, tagged_image):

    # Configure Pod template container
    container = client.V1Container(
        name=deployment_name,
        image=tagged_image,
        ports=[client.V1ContainerPort(container_port=container_port)])

    # Create and configurate a spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": deployment_name}),
        spec=client.V1PodSpec(containers=[container]))

    deployment = ''
    # Create the specification of deployment
    spec = client.AppsV1beta1DeploymentSpec(
        replicas=1,
        template=template)

    # Instantiate the deployment object
    deployment = client.AppsV1beta1Deployment(
        api_version="apps/v1beta1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=deployment_name),
        spec=spec)
    
    return deployment

def append_auth_token(token):
    token = token.decode("utf-8")
    debug(token)
    configuration = client.Configuration()
    configuration.api_key['authorization'] = token
    configuration.api_key_prefix['authorization'] = 'Bearer'
        
def create_deployment(deployment, namespace):
    configuration = client.Configuration()
        
    apps_v1beta1 = client.AppsV1beta1Api(client.ApiClient(configuration))
    api_response = apps_v1beta1.create_namespaced_deployment(
        body=deployment,
        namespace=namespace)
    print("Deployment created. ")
    #print("status='%s'" % str(api_response.status))

def delete_deployment(deployment_name, namespace):
        print("Deleting app deployment...", deployment_name)
        configuration = client.Configuration()       
        extensions_v1beta1 = client.ExtensionsV1beta1Api()
        delete_options = client.V1DeleteOptions()
        delete_options.grace_period_seconds = 0
        delete_options.propagation_policy = 'Foreground'
        try:
            api_response = extensions_v1beta1.delete_namespaced_deployment(
                name=deployment_name,
                body=delete_options,
                grace_period_seconds=0,
                namespace=namespace)
            #print("Delete deployment response:%s" % api_response)
        except Exception as e:
            print(str(e))
            raise e

def list_deployments(namespace="default"):
    print("Get list of deployments...")
    extensions_v1beta1 = client.ExtensionsV1beta1Api()
    try:
            api_response = extensions_v1beta1.list_namespaced_deployment(
                limit=50,
                namespace=namespace)
            #print("List deployment response:%s" % api_response)
            dnames = []
            for deployment in api_response.items:
                dnames.append(deployment.metadata.name)
            return(dnames)
    except Exception as e:
            print(str(e))
            raise e
        
def check_pod_status(context, deployment_name):

    core_v1 = client.CoreV1Api()
    namespace = get_namespace(context)
    pod_list = core_v1.list_namespaced_pod(namespace)
    for pod in pod_list.items:
        if deployment_name in pod.metadata.name:
            return 'Running' == pod.status.phase;

def create_service(deployment_name, host_port, container_port, namespace):

    v1_object_meta = client.V1ObjectMeta()
    v1_object_meta.name = deployment_name

    v1_service_port = client.V1ServicePort(port=host_port,
                                           target_port=container_port)

    v1_service_spec = client.V1ServiceSpec()
    v1_service_spec.ports = [v1_service_port]
    v1_service_spec.type = "NodePort"   #"LoadBalancer"
    v1_service_spec.selector = {"app": deployment_name}

    v1_service = client.V1Service()
    v1_service.spec = v1_service_spec
    v1_service.metadata = v1_object_meta

    core_v1 = client.CoreV1Api()
    api_response = core_v1.create_namespaced_service(
        namespace=namespace,
        body=v1_service)
    print("Service created.")
    return(api_response)

def delete_service(name, namespace="default"):
    print("Deleting service", name)
    v1 = client.CoreV1Api()
    delete_options = client.V1DeleteOptions()
    try:
        v1.delete_namespaced_service(name, namespace,delete_options)
    except client.rest.ApiException as e:
        print(str(e))
        return False
    else:
        print('deleted svc/{} from ns/{}'.format(name, namespace))
        return True 

def getRandomString(N):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=N))

def get_service_url(v1_service):
    print("Getting service url...")
    node_port = v1_service.spec.ports[0].node_port
    #print("node_port", node_port)
    cluster_ip = v1_service.spec.cluster_ip
    #print("cluster_ip", cluster_ip)
    #lb_ip = v1_service.spec.load_balancer_ip
    #print("lb_ip", lb_ip)

    config = k8s_config.Configuration()
    client1 = api_client.ApiClient(configuration=config)
    v1=core_v1_api.CoreV1Api(client1)
    nodes = v1.list_node()
    addresses = nodes.items[0].status.addresses
    node_ip = None
    for addr in addresses:
        if addr.type == 'ExternalIP':
            node_ip = addr.address
    #        print(node_ip)

    #print("trying internal ips")
    if not node_ip:
        for addr in addresses:
            if addr.type == 'InternalIP':
                node_ip = addr.address
    #            print(node_ip)

    pod_service_url = 'http://%s:%s' % (node_ip, node_port)
    return(pod_service_url)

def deploy_application(provider, context, app_name, image_url, host_port, container_port):
    if provider == 'AWS':
        cluster_name = context.split('cluster/')[-1]
        token = get_aws_token(cluster_name)
        append_auth_token(token)
        
    deployment_name = app_name + "-" + getRandomString(6)

    namespace = get_namespace(context)
    deployment_obj = create_deployment_object(deployment_name, container_port, image_url)
    try:
        create_deployment(deployment_obj, namespace)
    except Exception as e:
        print('deployment-error '+str(e))
        return(deployment_name,None)

    ## TODO check whether pod status is 'InvalidImageName' or not
    print("Deployment name: ", deployment_name)

    try:
        my_service = create_service(deployment_name, host_port, container_port, namespace)
        my_service_url = get_service_url(my_service)
        print("Service URL: ", my_service_url)
        
    except Exception as e:
        print('create service-error '+str(e))
        return(deployment_name,None)
    return(deployment_name, my_service_url)
    
# return True if succeed
def delete_application(provider, context, deployment_name):
    if provider == 'AWS':
        cluster_name = context.split('cluster/')[-1]
        token = get_aws_token(cluster_name)
        append_auth_token(token)
        
    try:
        namespace = get_namespace(context)
        delete_service(deployment_name, namespace)
        delete_deployment(deployment_name, namespace)
    except Exception as e:
        print('Deletion failed', str(e))
        return(False)
    return(True)
  
