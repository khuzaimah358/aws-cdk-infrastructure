# ============================================================
# 👨‍💻 DEVELOPER — Write your users handler code here
# ============================================================
# Available Environment Variables (configured by DevOps):
#   DB_HOST        → RDS PostgreSQL endpoint
#   DB_PORT        → 5432
#   DB_NAME        → myappdb
#   DB_SECRET_ARN  → Secrets Manager ARN for DB password
#   S3_BUCKET      → S3 bucket name
#   ENVIRONMENT    → dev / staging / prod
#   LOG_LEVEL      → DEBUG / INFO / ERROR
#
# DO NOT:
#   ❌ Hardcode passwords or secret keys
#   ❌ Rename the handler function (keep: lambda_handler)
#   ❌ Change the file name (keep: handler.py)
# ============================================================
import json


def lambda_handler(event, context):
    """
    Users Lambda Handler
    Handles: GET/POST/PUT/DELETE /users
    """
    # TODO: Developer implements logic here
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'message': 'Users handler - implement me!',
            'method': http_method,
            'path': path,
        }),
    }
