import os
import boto3

from fastapi import UploadFile
from botocore.exceptions import ClientError
from loguru import logger

from dotenv import load_dotenv
load_dotenv()

# AWS 설정 정보 
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
BUCKET_NAME = "capstone-conveyor-videos-2026"
REGION = "ap-northeast-2"

# S3 클라이언트 생성
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION
)

def upload_video_to_s3_from_memory(upload_file: UploadFile, s3_file_name: str) -> str:
    try:
        logger.info(f"S3 업로드 시작: {s3_file_name}")
        upload_file.file.seek(0) # 파일 포인터를 처음으로 이동

        s3_client.upload_fileobj(
            upload_file.file,
            BUCKET_NAME,
            s3_file_name,
            ExtraArgs={'ContentType': 'video/mp4'}
        )
        
        url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{s3_file_name}"
        logger.info(f"S3 업로드 완료! URL: {url}")
        return url
        
    except Exception as e:
        logger.error(f"S3 업로드 중 에러 발생: {e}")
        return ""