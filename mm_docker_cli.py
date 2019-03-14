import argparse
from mm_docker_lib import *

## TODO
# - allow to set number of workers in gunicorn, ex --workers=N
# - support authentication or use SSL
#   > gunicorn --certfile=server.crt --keyfile=server.key --bind 0.0.0.0:443 test:app
# - convert to golang

if __name__ == '__main__':
    __version__ = "0.4.2"
    #### parse arguments
    parser = argparse.ArgumentParser(description='Model Container Deployer CLI')
    subparsers = parser.add_subparsers(title="actions",dest="action")

    parser_list = subparsers.add_parser("listmodel")
    parser_list.add_argument("key", help='partial model name or \'all\'')
    parser_list.add_argument("-v", "--verbose", help='turn on verbose', action="store_true")

    parser_log = subparsers.add_parser("lastlogs")
    parser_log.add_argument("number", help='last N lines or \'all\'')
    parser_log.add_argument("-v", "--verbose", help='turn on verbose', action="store_true")
    
    parser_syslog = subparsers.add_parser("systemlog")
    parser_syslog.add_argument("service_url", help='The exposed service URL')
    parser_syslog.add_argument("-v", "--verbose", help='turn on verbose', action="store_true")

    parser_publish = subparsers.add_parser("publish")
    parser_publish.add_argument("model_id", help='Model UUID')
    parser_publish.add_argument("-v", "--verbose", help='turn on verbose', action="store_true")

    parser_launch = subparsers.add_parser("launch")
    parser_launch.add_argument("image_url", help='Docker image URL')
    parser_launch.add_argument("-v", "--verbose", help='turn on verbose', action="store_true")    

    parser_execute = subparsers.add_parser("execute")
    parser_execute.add_argument("service_url", help='The exposed service URL')
    parser_execute.add_argument("csv_file", help='The test data in csv format')
    parser_execute.add_argument("-v", "--verbose", help='turn on verbose', action="store_true")

    parser_query = subparsers.add_parser("query")
    parser_query.add_argument("service_url", help='The exposed service URL')
    parser_query.add_argument("test_id", help='The test id returned from score execution')
    parser_query.add_argument("-v", "--verbose", help='turn on verbose', action="store_true")
    
    parser_stop = subparsers.add_parser("stop")
    parser_stop.add_argument("deployment_name",help='The deployment name from score execution')
    parser_stop.add_argument("-v", "--verbose", help='turn on verbose', action="store_true")
    
    parser_score = subparsers.add_parser("score")
    parser_score.add_argument("image_url", help='Docker image URL')
    parser_score.add_argument("csv_file", help='The test data in csv format')
    parser_score.add_argument("-v", "--verbose", help='turn on verbose', action="store_true")
    
    args = parser.parse_args()
    kwargs = vars(args)

    if "verbose" in kwargs:
        if args.verbose:
            setVerbose(True)
        del kwargs["verbose"]

    if kwargs["action"] is None:
        parser.print_help()
        exit(0)

    if not initConfig():
        exit(1)
    
    try:
        #print(globals())        
        globals()[kwargs.pop('action')](**kwargs)
    except RuntimeError as err:
        print("Runtime Error: ",err)

      

