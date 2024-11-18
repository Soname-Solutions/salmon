
# Limiting CDK Execution Role Privileges

By default, the `cdk bootstrap` command in AWS CDK creates a CloudFormation execution role with AdministratorAccess privileges. In environments where such a high level of access is unacceptable, it is possible to limit these privileges. This document describes how to configure a CDK bootstrap environment with restricted permissions tailored for the SALMON project.

## Using a Custom IAM Policy for CDK Bootstrap

The SALMON repository includes an IAM policy with permissions sufficient to deploy the project. You can instruct CDK to use this policy instead of the default. Follow these steps to set up a restricted CDK bootstrap.

### 1. Create a Custom CDK Cloudformation Execution Policy

Navigate to `/cdk` folder in this repo and deploy the custom policy using the following command:

```bash
aws cloudformation deploy --template-file salmon_cdk_cloudformation_exec_policy.yaml --stack-name cf-salmon-cdk-cloudformation-exec-policy-all --capabilities CAPABILITY_NAMED_IAM
```

After deployment, note the `PolicyArn` from the `cf-salmon-cdk-cloudformation-exec-policy-all` stack outputs in the **CloudFormation console**.

### 2. Create CDK Bootstrap with Limited Permissions

Use the custom policy to bootstrap the CDK environment with the following command:

```bash
cdk bootstrap --cloudformation-execution-policies <<policy_arn>>
```

Replace <<policy_arn>> with the `PolicyArn` from the previous step.

### 3. Verify the Configuration

To verify the permissions assigned to the CDK IAM role:

1. Navigate to the **CloudFormation Console** and locate the `CDKToolkit` stack.
2. Open the **Resources** tab and find the resource with the logical ID `CloudFormationExecutionRole`.
3. Click on the role to review its permissions, ensuring it no longer uses AdministratorAccess and adheres to the custom policy.

## Handling Conflicts with an Existing CDK Bootstrap

In some cases, an existing CDK bootstrap in the same AWS account/region may already be used by other projects. To avoid conflicts, you can create an alternative bootstrap identified by a unique qualifier.

### Prerequisite

Ensure you have created a policy as demonstrated in Step 1 of the previous section.

### 1. Create an Isolated CDK Bootstrap

Run the following command to create a separate bootstrap stack:

```bash
cdk bootstrap --qualifier <<your_qualifier_name>> --cloudformation-execution-policies <<put created policy Arn here>> --toolkit-stack-name <<your_stack_name>>
```

Replace placeholders:

- **your_qualifier_name**: A unique string (up to 10 characters) to identify this bootstrap. It will be used when running CDK commands. You can use `salmon`, for example.
- **your_stack_name**: A custom name for the bootstrap CloudFormation stack. For example, use CDKToolkitSalmon instead of the default CDKToolkit.

### 2. Using the Custom CDK Bootstrap for Deployments

To use the custom bootstrap during deployment, specify the qualifier using CDK context:

```bash
cdk deploy -c "@aws-cdk/core:bootstrapQualifier=<<your_qualifier_name>>" --context stage-name=<<you_stage_name>>
```

Replace placeholders:

- **your_qualifier_name** with the name of the qualifier you used during the bootstrap process.
- **you_stage_name** with the Salmon's stage-name.

## Additional consideration if you plan to contribute to Salmon project

In order to check your changes before creating a pull request, it's recommended to run Integration and Deployment tests.
Deployment tests should preferably be executed with limited-privileged CDK Bootstrap.
In order to do this:

1. **Create a Separate Bootstrap**: Follow the steps outlined in the previous section to create an isolated bootstrap.
2. **Set a GitHub Repository Variable**:
   - Name: CDK_BOOTSTRAP_QUALIFIER
   - Value: The qualifier name you created (e.g., salmon).
3. **Run Deployment Tests**:
   - The deployment tests will automatically use the value of CDK_BOOTSTRAP_QUALIFIER to select the correct bootstrap.
