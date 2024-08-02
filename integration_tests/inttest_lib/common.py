
TARGET_MEANING = "inttest-target"

def get_target_sns_topic_name(stage_name: str) -> str:
        prefix = "topic"
        project_name = "salmon"
        meaning = TARGET_MEANING

        outp = f"{prefix}-{project_name}-{meaning}-{stage_name}"

        return outp    
