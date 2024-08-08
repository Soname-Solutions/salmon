import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
lib_path = os.path.join(project_root, 'src')
sys.path.append(lib_path)

from inttest_lib.runners.lambda_function_runner import LambdaFunctionRunner

lambda_function_name = "lambda-salmon-digest-devam"

runner = LambdaFunctionRunner([lambda_function_name],"eu-central-1")

payload = "{'test' : 'qqq'}"

response = runner.initiate()

print(response)

runner.await_completion(poll_interval=2)