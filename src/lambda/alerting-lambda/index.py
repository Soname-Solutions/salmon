import os
import json


def generate_hello_world():
    return "Hello World!"


def lambda_handler(event, context):
    helloworld = generate_hello_world()
    return {"message": helloworld}
