import os
import boto3
from botocore.exceptions import ClientError
from config import settings

class S3DeliveryService:
    def __init__(self):
        """
        Initializes the official AWS Boto3 SDK Client configuration layers.
        """
        # AWS Key Parameters Extraction
        self.bucket_name = settings.AWS_S3_BUCKET or os.getenv("S3_BUCKET_NAME", "")
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "ap-south-1")
        )
        self.court_folder = "PeshawarHigh Court Judgments"  # Mandated section 1 constant folder map

    def upload_file_idempotent(self, local_path: str, artifact_type: str, leaf_filename: str) -> str:
        """
        Uploads a file to Amazon S3 with strict Content-Type matching and space-to-plus serialization.
        Enforces idempotency mapping before attempting a put_object stream.
        """
        # Mandatory Rule: Replace spaces with '+' in the structural S3 keys
        s3_filename = f"Peshawar High Court - {leaf_filename}".replace(" ", "+")
        
        # Determine the directory type prefix schema path
        # Expected outputs: pdfs/, markdown/, metadata/
        s3_key = f"{artifact_type}/{self.court_folder}/{s3_filename}"

        # Assign strictly mandated Content-Type allocations
        content_type_map = {
            "pdfs": "application/pdf",
            "markdown": "text/markdown; charset=utf-8",
            "metadata": "application/json"
        }
        content_type = content_type_map.get(artifact_type, "binary/octet-stream")

        try:
            # Idempotent verification rule: Check with head_object before executing any PUT
            # Exception rule: Citation update path bypasses this, handled explicitly
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            print(f"[S3 IDEMPOTENCY] File already exists on S3 bucket: {s3_key}. Skipping upload.")
            return f"s3://{self.bucket_name}/{s3_key}"
        except ClientError as e:
            # 404 implies file is not present, meaning it is genuinely new
            if e.response['Error']['Code'] == "404":
                try:
                    print(f"[S3 UPLOAD] Deploying artifact stream onto S3 Key: {s3_key}...")
                    self.s3_client.upload_file(
                        local_path, 
                        self.bucket_name, 
                        s3_key,
                        ExtraArgs={'ContentType': content_type}
                    )
                    return f"s3://{self.bucket_name}/{s3_key}"
                except Exception as upload_err:
                    raise IOError(f"AWS S3 put_object pipeline structural crash: {str(upload_err)}")
            else:
                raise IOError(f"AWS S3 metadata handshake execution failed: {str(e)}")