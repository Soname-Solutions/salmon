# SALMON: Steps to Integrate New AWS Service

This article describes the steps required to integrate a new AWS service into the existing SALMON solution. 

#### Overview of Integration Components

The following diagram illustrates the necessary components and their relationships for integrating the new service: 

![Overview](/docs/images/new-service.png "Overview")

The modular and flexible SALMON architecture ensures a seamless addition of components and their corresponding tests. Below you may find more details on each component.

#### Monitored Environment

In the `InfraMonitoredStack` located in the `cdk/monitored_environment/` folder, perform the following steps:

- **Extend IAM Role Permissions**: \
    Update the IAM Role to include the necessary read permissions for the resources associated with the new service. This ensures metrics can be extracted and the digest report can be generated accurately. 

- **Create an AWS EventBridge Rule**: \
    Define a new EventBridge rule to route events from the new service to the centralized EventBridge bus in the Tooling Environment.

#### Tooling Environment

The Tooling Environment requires the implementation of the following components:

- **Metrics Extraction Libraries**: \
    Implement a new child class inheriting from `BaseMetricsExtractor` (in the `src/lib/metrics_extractor/` folder). This class should prepare metrics specific to the new service for further analysis.

- **Event Mapper Libraries**: \
    Implement a new child class based on `GeneralAwsEventMapper` (in the `src/lib/event_mapper/` folder) to convert raw event data into structured alert messages for monitoring and notification purposes.

- **Digest Libraries**: \
    Extend the `BaseDigestDataExtractor` class (in the `src/lib/digest_service/` folder) to create a new child class responsible for extracting digest data specific to the new service.

- **Grafana Dashboard**: \
    Create a `YAML` template at `cdk/tooling_environment/stacks/grafana/` folder that defines the Grafana dashboard for visualizing key metrics related to this new service.

#### Testing
The SALMON's testing process includes both unit and integration tests:

- **Unit Tests**: \
    Write unit tests for all new service's components. Use the existing tests in the `tests/unit-tests/src/lib/` folder for consistency.

- **Integration Tests**: \
    Develop integration tests to verify the end-to-end functionality of the new service. Add these tests to the `tests/integration-tests/` folder. Additionally, include the resources associated with the new service in the integration testing stand (located in the `cdk/integration_testing_stand/` folder). These tests ensure the service interacts correctly with the monitored environment, tooling environment, and other dependent components.
