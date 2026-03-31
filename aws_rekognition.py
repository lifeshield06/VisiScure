"""
AWS Rekognition face comparison module.
Credentials are loaded from environment variables — never hardcoded.

Required .env variables:
  AWS_ACCESS_KEY   – IAM access key ID
  AWS_SECRET_KEY   – IAM secret access key
  AWS_REGION       – e.g. ap-south-1
"""
import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError


def _get_client():
    """Create a Rekognition client using env-var credentials (read fresh each call)."""
    from dotenv import load_dotenv
    load_dotenv(override=True)   # re-read .env so credential changes take effect without restart
    return boto3.client(
        "rekognition",
        aws_access_key_id     = os.getenv("AWS_ACCESS_KEY"),
        aws_secret_access_key = os.getenv("AWS_SECRET_KEY"),
        region_name           = os.getenv("AWS_REGION", "ap-south-1"),
    )


def compare_faces(source_bytes: bytes, target_path: str, threshold: float = 80.0) -> dict:
    """
    Compare a source face (bytes) against a target image stored on disk.

    Args:
        source_bytes:  Raw bytes of the uploaded query image.
        target_path:   Filesystem path to the stored selfie (e.g. static/uploads/…).
        threshold:     Minimum similarity to consider a match (default 80 %).

    Returns:
        {
          "matched":    bool,
          "similarity": float | None,   # highest face-match similarity
          "error":      str  | None,    # set when an error occurred
        }
    """
    # Read target image from disk
    if not os.path.exists(target_path):
        return {"matched": False, "similarity": None, "error": "target_not_found"}

    try:
        with open(target_path, "rb") as f:
            target_bytes = f.read()
    except OSError as e:
        return {"matched": False, "similarity": None, "error": str(e)}

    client = _get_client()

    try:
        response = client.compare_faces(
            SourceImage={"Bytes": source_bytes},
            TargetImage={"Bytes": target_bytes},
            SimilarityThreshold=threshold,
        )
    except client.exceptions.InvalidParameterException:
        # No face detected in one of the images
        return {"matched": False, "similarity": None, "error": "no_face_detected"}
    except (BotoCoreError, ClientError) as e:
        return {"matched": False, "similarity": None, "error": str(e)}

    face_matches = response.get("FaceMatches", [])
    if not face_matches:
        return {"matched": False, "similarity": 0.0, "error": None}

    # Take the highest similarity score
    best = max(face_matches, key=lambda m: m["Similarity"])
    similarity = round(best["Similarity"], 1)
    return {"matched": similarity >= threshold, "similarity": similarity, "error": None}
