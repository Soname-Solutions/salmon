

class AWS_Common_Resources:
    @classmethod
    def get_Lambda_Powertools_Layer_Arn(cls, region):
        return f"arn:aws:lambda:{region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:52"