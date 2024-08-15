from aws_cdk import aws_glue_alpha as glue
from aws_cdk import aws_iam as iam
from constructs import Construct


def create_python_shell_glue_job(
    scope: Construct, job_id: str, job_name: str, role: iam.Role, script: glue.Code
) -> glue.Job:
    """
    Create a Python shell job in AWS Glue.

    Args:
        scope (Construct): The scope in which to define this construct.
        job_id (str): A unique identifier for this job within the scope.
        job_name (str): The name of the Glue job.
        role (iam.Role): The IAM role for the Glue job.
        script (glue.Code): The Glue code object representing the job script.

    Returns:
        glue.Job: The newly created Python shell Glue job.
    """

    return glue.Job(
        scope,
        job_id,
        job_name=job_name,
        role=role,
        executable=glue.JobExecutable.python_shell(
            glue_version=glue.GlueVersion.V1_0,
            python_version=glue.PythonVersion.THREE,
            script=script,
        ),
    )


def create_pyspark_glue_job(
    scope: Construct,
    job_id: str,
    job_name: str,
    role: iam.Role,
    script: glue.Code,
    default_arguments: dict,
) -> glue.Job:
    """
    Create a PySpark job in AWS Glue.

    Args:
        scope (Construct): The scope in which to define this construct.
        job_id (str): A unique identifier for this job within the scope.
        job_name (str): The name of the Glue job.
        role (iam.Role): The IAM role for the Glue job.
        script (glue.Code): The Glue code object representing the job script.

    Returns:
        glue.Job: The newly created PySpark Glue job.
    """

    return glue.Job(
        scope,
        job_id,
        job_name=job_name,
        role=role,
        executable=glue.JobExecutable.python_etl(
            glue_version=glue.GlueVersion.V3_0,
            python_version=glue.PythonVersion.THREE,
            script=script,
        ),
        default_arguments=default_arguments,
        worker_count=2,
        worker_type=glue.WorkerType.G_1_X,
    )
