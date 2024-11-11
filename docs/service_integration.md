# SALMON New Service Integration

This article describes the steps required to integrate a new AWS service into the existing SALMON solution. 

#### Overview of Integration Components
The modular and flexible SALMON architecture ensures a seamless addition of components and their corresponding tests. \
The following diagram illustrates the necessary components and their relationships for integrating the new service: 

![Overview](/docs/images/new-service.png "Overview")

Below is a detailed explanation of each component.

#### Monitored Environment

In the `InfraMonitoredStack` located in the `cdk/monitored_environment/` folder the following steps should be performed:

- **Extend IAM Role Permissions**: \
    Update the IAM Role to include the necessary read permissions for the resources associated with the new service. This ensures metrics can be extracted and the digest report can be generated accordingly. 

- **Create an AWS EventBridge Rule**: \
    New EventBridge rule must be defined to route events from the new service to the centralized EventBridge bus in the Tooling Environment. 


#### Tooling Environment

The Tooling Environment requires the implementation of the following components:

- **Metrics Extraction Libraries**: \
    Implement a new child class inheriting from `BaseMetricsExtractor` (in the `src/lib/metrics_extractor/` folder) to prepare the metrics specific to the new service and write them to the Timestream database for further analysis.

- **Event Mapper Libraries**: \
    Implement a new child class based on `GeneralAwsEventMapper` (in the `src/lib/event_mapper/` folder) to convert raw event data into structured alert messages for monitoring and notification purposes.

- **Digest Libraries**: \
    Extend the `BaseDigestDataExtractor` class (in the `src/lib/digest_service/` folder) to create a new child class responsible for extracting digest data specific to the new service.

- **Grafana Dashboard**: \
    Create a `YAML` template at `cdk/tooling_environment/stacks/grafana/` folder that defines the Grafana dashboard for visualizing key metrics related to this new service.

#### Testing
To ensure the new service operates correctly within the SALMON, comprehensive testing is required:

- **Unit Tests**: \
    Write unit tests for the new service's components. Existing tests in the `tests/unit-tests/src/lib/` folder can be used as templates for consistency.

- **Integration Tests**: \
    Develop integration tests (in the `tests/integration-tests/` folder) and add the resources associated with the new service to the integration testing stand (in the `cdk/integration_testing_stand/` folder) so to verify the end-to-end functionality of the new service. These tests ensure the service interacts correctly with the monitored environment, tooling environment, and any other dependent components.
