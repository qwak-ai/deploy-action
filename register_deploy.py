from qwak.qwak_client.builds.build import BuildStatus
from qwak import QwakClient
import subprocess
import re
import os
import time



SLEEP_BETWEEN_STATUS_QUERY = 10.0

# Initialize the Qwak client
_qwak_client = QwakClient()

# Define a dictionary to map status codes to their string representations
_status_code_to_name = {
    1: "INITIATING_DEPLOYMENT",
    2: "PENDING_DEPLOYMENT",
    3: "SUCCESSFUL_DEPLOYMENT",
    4: "FAILED_DEPLOYMENT",
    5: "SUCCESSFUL_UNDEPLOYMENT",
    6: "FAILED_UNDEPLOYMENT",
    7: "UNSET",
    8: "FAILED_INITIATING_DEPLOYMENT",
    9: "INITIATING_UNDEPLOYMENT",
    10: "PENDING_UNDEPLOYMENT",
    11: "ALL_BUILDS_UNDEPLOYED",
    12: "CANCELLED_DEPLOYMENT",
    13: "INITIATING_CANCEL_DEPLOYMENT",
    # Add more status codes and their names here as needed
}

# Function to get the status name from the status code
def _get_status_name(status_code) -> str:
    return _status_code_to_name.get(status_code, "UNKNOWN_STATUS")



def deploy_command():
    command = ["qwak", "models", "deploy"]

    # Deployment Type
    deploy_type = os.getenv('DEPLOY_TYPE')
    if deploy_type:
        if deploy_type in ['realtime', 'batch', 'stream']:
            command.append(deploy_type)
        else:
            print(f"Deployment type {deploy_type} is invalid. Please use realtime, batch or stream.")
            exit(1)

    # Model ID
    model_id = os.getenv('MODEL_ID')
    if model_id:
        command.extend(["--model-id", model_id])

    # Tags List - will be used later
    tags_list = os.getenv('TAGS')

    # Build ID
    build_id = os.getenv('BUILD_ID')
    if build_id:
        command.extend(["--build-id", build_id])
        print( "Build ID was specified, ignoring TAGS.\n")

    elif tags_list:
        tags = tags_list.split(",")

        print (f"The following Tags were specified: {tags} -> Looking for the latest SUCCESSFUL build with these Tags.\n")

        builds = _qwak_client.get_builds_by_tags(model_id=model_id,
                                        tags=tags)
        if builds:
            successful_builds = [build for build in builds if build.build_status == BuildStatus.SUCCESSFUL]

            if successful_builds:
                successful_builds.sort(key=lambda r: r.created_at)

                command.extend(["--build-id", successful_builds[-1].build_id])

                print (f"Found successful Build with the specified tags - Build ID: {successful_builds[-1].build_id}\n")
            else: 
                print ("No successful builds with these tags were found. Exiting...\n")
                exit(1)
        else: 
            print ("No builds with these tags were found. Exiting...\n")
            exit(1)

    else:
        print("Neither BUILD_ID nor TAGS provided -> Deploying the latest successful Build.\n")

    # Parameter List
    param_list = os.getenv('PARAM_LIST')
    if param_list:
        params = param_list.split(",")
        for param in params:
            key, value = param.split("=")
            command.extend([f"--{key}", value])

    # Environment Variables
    env_vars = os.getenv('ENV_VARS')
    if env_vars:
        env_vars_list = env_vars.split(",")
        for env_var in env_vars_list:
            command.extend(["-E", env_var])

    # Instance Type
    instance = os.getenv('INSTANCE')
    if instance:
        command.extend(["--instance", instance])

    # Replicas
    replicas = os.getenv('REPLICAS')
    if replicas:
        command.extend(["--replicas", replicas])

    # IAM Role ARN
    iam_role_arn = os.getenv('IAM_ROLE_ARN')
    if iam_role_arn:
        command.extend(["--iam-role-arn", iam_role_arn])

    # Environment
    environment = os.getenv('ENVIRONMENT')
    if environment:
        command.extend(["--environment", environment])

    # Timeout After
    timeout_after = os.getenv('TIMEOUT_AFTER')
    if deploy_type == "realtime" and timeout_after:
        command.extend(["--timeout", timeout_after])

    return " ".join(command)


def wait_for_deployment(deployment_id: str, timeout: int) -> str:

    # Record the start time to track how long we've been waiting
    start_time = time.time()
    
    current_status=None

    try:
        # Keep checking the deployment status until a timeout is reached
        while time.time() - start_time < 60 * timeout:
            # Wait a specified amount of time between each status check
            time.sleep(SLEEP_BETWEEN_STATUS_QUERY)

            # Get the current deployment object from the Qwak client
            deployment_status_object = _qwak_client._get_deployment_management().get_deployment_status(deployment_id)

            verbal_deployment_status = _get_status_name(deployment_status_object.status)

            # Print the current deployment status if changed
            if verbal_deployment_status is not current_status:
                print(f"Current deployment {deployment_id} status is: {verbal_deployment_status}\n")
                current_status = verbal_deployment_status

            # Check if the deployment is SUCCESSFUL
            if verbal_deployment_status is _get_status_name(3): #SUCCESSFUL_DEPLOYMENT
                elapsed_time = time.time() - start_time
                minutes, seconds = divmod(elapsed_time, 60)
                print(f"Deployment finished after {int(minutes)} minutes and {seconds:.2f} seconds with status {verbal_deployment_status}\n")
                return verbal_deployment_status
            
            # Check if the deployment has failed
            elif verbal_deployment_status not in [_get_status_name(1), _get_status_name(2)]: #INITIATING_DEPLOYMENT or PENDING_DEPLOYMENT
                print(f"Deployment failed with status {verbal_deployment_status} -> Please check the logs in the Qwak dashboard for more information.")
                return verbal_deployment_status
            
        
        

        # If the loop exits without returning, the deployment has timed out
        raise TimeoutError(f"Deployment {deployment_id} timed out after {timeout} minutes.")
    
    except Exception as e:
        # Catch any other exceptions, print an error message, and re-raise the exception
        print(f"An error occurred while waiting for deployment {deployment_id}:\n {str(e)}")
        raise e
    


if __name__ == '__main__':

    timeout_for_failing = int(os.getenv('TIMEOUT_AFTER', 30)) # Default 30 minutes
 
    qwak_deploy_model_command = deploy_command()
    print(f"Printing the Qwak CLI command for debug purposes:\n{qwak_deploy_model_command}\n")

    deployment_id = None # Define deployment_id variable outside the try block

    try:
        
        # Create a Popen object to run the command
        process = subprocess.Popen(qwak_deploy_model_command, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                shell=True, 
                                text=True)


        # Wait for the process to finish and get the return code
        return_code = process.wait()
        stdout, stderr = process.communicate()

        # Print the standard output
        print(f"Command Output:\n\n{stdout}\n")
        #for char in stdout:
        #    print(f"{char}: {ord(char)}")

        # Check if the command was successful
        if return_code != 0:
            print(f"An error occurred while running the `qwak models deploy` command.\n {stderr}")
            exit(1)

        # Extract the build ID using a regular expression - careful with the escape codes!!!
        deployment_id_pattern = re.compile(r'Deployment ID\s+│\s+([\w-]+)')
        match_deployment = deployment_id_pattern.search(stdout)

        # Extract the build ID using a regular expression - careful with the escape codes!!!
        build_id_pattern = re.compile(r'Build ID\s+│\s+([\w-]+)')
        match_build = build_id_pattern.search(stdout)
        
        if match_deployment:
            deployment_id = match_deployment.group(1).strip()
            print(f"Extracted Deployment ID: {deployment_id}\n")

            if match_build:
                build_id = match_build.group(1).strip()
                print(f"Extracted Build ID: {build_id}\n")
            else:
                print(f"Couldn't extract Build ID from command output.\n")

            # Call the wait_for_build method with the specified build ID
            deployment_status = wait_for_deployment(deployment_id, timeout_for_failing)

            # Write the outputs to the GitHub environment file
            with open(os.getenv('GITHUB_ENV'), 'a') as file:
                file.write(f"deploy-id={deployment_id}\n")
                file.write(f"deploy-status={deployment_status}\n")

        else:
            print("Deployment ID not found in the command output. Please contact the Qwak team for assistance.")
            exit(1)

    except TimeoutError as timeout_error:
          # Handle the timeout exception specifically
        if deployment_id:
            print(f"The deployment process hasn't ended, but the Action for deployment {deployment_id} timed out: {str(timeout_error)}")

            # Write "TIMEOUT" to the build_status in the GitHub environment file
            with open(os.getenv('GITHUB_ENV'), 'a') as file:
                file.write(f"deploy-id={deployment_id}\n")
                file.write("deploy-status=TIMEOUT\n")
        else:
            print("Deployment ID not found. Cannot handle timeout exception without a Deployment ID.")
            exit(1)

    except Exception as general_error:
        # Handle any other exceptions that might occur
        print(f"An unexpected error occurred while waiting for build: {str(general_error)}")
        #traceback.print_exc() # This will print the stack trace
        exit(1)


