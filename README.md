# Qwak Model `DEPLOY` Action

This GitHub Action triggers a Qwak Cloud Deployment for a machine learning model Build. It provides a seamless integration with Qwak's platform, allowing you to deploy and monitor your models directly from your GitHub repository.

<br>

## Table of Contents

- [Action Flow](#action-flow)
- [Requirements](#requirements)
- [Inputs](#inputs)
- [Outputs](#outputs)
- [Deployment Types](#deployment-types)
  - [Realtime](#realtime)
  - [Stream](#stream)
  - [Batch](#batch)
- [Example Usage](#example-usage)
- [Support](#support)

<br>

## Action Flow

1. **Initialize Deployment**: Trigger build using the `qwak models deploy` CLI command.
2. **Extract IDs**: Retrieve the Deployment ID and Build ID from the command output.
3. **Monitor Status**: Continuously check the Deployment status from the Qwak Cloud every 10 seconds while it's in the `PENDING` or `INITIALIZING` state.
4. **Output Results**: Once the deployment is complete, the Action outputs the Deployment ID and STATUS.

<br>

## Requirements

- A [Qwak API key](https://app.qwak.ai/qwak-admin#personal-api-keys) must be set up as a repository secret named `QWAK_API_KEY`.

## Inputs

- `sdk-version`: Specifies the Qwak-SDK version required to trigger this deploy. Default is `latest`.
- `deploy-type`: **(Required)** Type of deployment. Supported types are `realtime`, `stream`, and `batch`.
- `model-id`: **(Required)** The ID of the model to be deployed.
- `build-id`: The Build ID to be deployed. If not specified, the latest successful build will be deployed.
- `param-list`: A list of key-value pairs representing deployment parameters. These are specified in the format `NAME=VALUE` and separated by commas. For a complete list of available parameters for each deployment type, refer to [Deployment Types](#deployment-types).
- `env-vars`: Environment variables for the deployment, specified in the format `NAME=VALUE` and separated by commas. These can be used to set or override environment settings within the deployment process.
- `instance`: Specifies the hardware type to deploy the model on. The instance defines the allocated CPU/GPU and Memory resources. [Instances list.](https://docs-saas.qwak.com/docs/instance-sizes) Default is `small`.
- `replicas`: The number of selected instances to provision for this deployment. Default is `1`.
- `iam-role-arn`: Custom IAM Role ARN that Qwak should assume in order to access external resources during the build process.
- `environment`: Specifies the Qwak environment to use, such as `dev`, `staging`, or `production`. If not specified, the default environment will be used.
- `timeout-after`: Specifies how many minutes to wait for the build to complete before timing out. Default is `30`.

<br>

## Outputs

- `deploy-id`: The ID of the deployment.
- `deploy-status`: The status of the deployment once it has finished execution or times out.


Output Example 
```bash
deploy-id=bc3ceeca-e4ed-48b9-8ff1-80427923f1cf
deploy-status=SUCCESSFUL_DEPLOYMENT
```

<br>

## Deployment Types


### Realtime
Qwak real time models deploy your ML models with a lightweight, simple and scalable REST API wrapper. We set up the network requirements and deploy your model on a managed Kubernetes cluster, allowing you to leverage auto-scaling and security

#### Parameters

| Parameter            | Type    | Default Value | Description                                                                                     |
|----------------------|---------|---------------|-------------------------------------------------------------------------------------------------|
| `timeout`            | INT     |               | Inference request timeout in MS.                                                                 |
| `server-workers`     | INT     |               | Number of workers running the HTTP server.                                                       |
| `daemon-mode`        | BOOLEAN | `true`        | Configure Gunicorn daemon mode.                                                                  |
| `max-batch-size`     | INT     | `0`           | Max batch size in prediction. A value of 0 means it's dynamic.                                  |
| `variation-name`     | TEXT  | `default`     | The model variation name.                                                                        |
| `deployment-timeout` | INT     | `1800`        | The number of seconds the deployments can be in progress before it is considered as failed.      |
| `protected`          | BOOLEAN | `false`       | Whether the deployment variation is protected.                                                   |



#### `param-list` example
```bash
timeout=3000,server-workers=4,variation-name=default,daemon-mode=false
```

### Stream

Streaming deployments let you easily connect Kafka streams with your models to perform real-time inference.

Using streaming deployments can be useful for processing large amounts of distributed data to avoiding complex triggering and scheduling architectures as fresh data arrives. A streaming deployment will consume messages from a Kafka topic and produce predictions into a Kafka topic of your choice.


#### Parameters

| Parameter                  | Type   | Description                                                                 | Default | Possible Values |
|----------------------------|--------|-----------------------------------------------------------------------------|---------|-----------------|
| `bootstrap-server`         | TEXT   | Kafka consumer/producer bootstrap server.                                    |         |                 |
| `consumer-bootstrap-server`| TEXT   | Kafka consumer bootstrap server.                                             |         |                 |
| `consumer-topic`           | TEXT   | Kafka consumer topic.                                                        |         |                 |
| `consumer-group`           | TEXT   | Kafka consumer group.                                                        |         |                 |
| `consumer-auto-offset-reset`| ENUM  | Kafka consumer auto offset reset.                                            | `unset` | `unset`, `latest`, `earliest` |
| `consumer-timeout`         | INT    | Kafka consumer polling timeout. Should be in range of kafka admin configuration `group.min.session.timeout.ms` and `group.max.session.timeout.ms`. |         |                 |
| `consumer-max-batch-size`  | INT    | The maximum number of records returned in a single call to `poll()`.         |         |                 |
| `consumer-max-poll-latency`| FLOAT  | The maximum delay between invocations of `poll()` when using consumer group management. |         |                 |
| `producer-bootstrap-server`| TEXT   | Kafka producer bootstrap server.                                             |         |                 |
| `producer-topic`           | TEXT   | Kafka producer topic.                                                        |         |                 |
| `producer-compression-type`| ENUM   | Kafka producer compression type.                                             | `uncompressed` | `uncompressed`, `gzip`, `snappy`, `lz4`, `zstd` |

#### `param-list` example
```bash
consumer-bootstrap-server="10.0.0.8",consumer-topic="model-input-topic",producer-bootstrap-server="10.0.0.9",producer-topic="model-output-topic"
```


### Batch

This deployment type allows you to run batch inference executions in the system, and handle data files from an online cloud storage provider.

>**No additional parameters are required for batch deployments.**

<br>

## Example Usage

### Basic Example

```yaml
- name: Build Qwak Model
  uses: qwak-ai/deploy-action@v1
  with:
    model-id: <your-model-id>
    deploy-type: realtime
    param-list: 'timeout=3000,server-workers=4'
```

### Example with GPU configuration

```yaml
- name: Build Qwak Model with GPU
  uses: qwak-ai/deploy-action@v1
  with:
    model-id: <your-model-id>
    instance: 'gpu.t4.xl'
    deploy-type: batch
```


### Example with Timeout Configuration

```yaml
- name: Build Qwak Model with Timeout
  uses: qwak-ai/build-action@v1   
  with:
    model-id: 'your-model-id'
    timeout-after: 60
```

### Trigger a Streaming Deployment when after a successful model Build

```yaml

name: Deploy ML Model after successful Build

on:
  workflow_run:
    workflows: ["Build ML Model on Pull Request"]  # Name of the build workflow
    types:
      - completed

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    steps:
    - name: Deploy Qwak Model
      uses: qwak-ai/deploy-action@v1
      with:
        model-id: <your-model-id>
        build-id: <your-build-id>
        deploy-type: stream
        sdk-version: '0.5.18'
        instance: 'medium'
        iam-role-arn: 'arn:aws:iam::<account-id>:role/<role-name>'
        param-list: 'consumer-bootstrap-server="10.0.0.8",consumer-topic="model-input-topic",producer-bootstrap-server="10.0.0.9",producer-topic="model-output-topic"'
        # other inputs as needed
```

## Support

For support or any questions related to this action, please contact the Qwak team.