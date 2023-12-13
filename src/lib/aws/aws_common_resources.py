

class AWSCommonResources:
    @classmethod
    def get_lambda_powertools_layer_arn(cls, region):
        return f"arn:aws:lambda:{region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:52"