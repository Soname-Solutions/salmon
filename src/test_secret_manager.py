from lib.aws.secret_manager import SecretManager

client = SecretManager()
smtp_secret = client.get_secret("dev/smtp")

print(smtp_secret)
print(smtp_secret["SMTP_SERVER"])
