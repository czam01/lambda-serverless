import boto3
import json
import os
import logging
from boto3.dynamodb.conditions import Key

# VotaNet - Sistema de consulta de votantes

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

DYNAMO_BD = os.environ['DYNAMO_BD']
DYNAMO_KEY = os.environ.get('DYNAMO_KEY', 'cc')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMO_BD)


def lambda_handler(event, context):
    try:
        body = event if isinstance(event, dict) and DYNAMO_KEY in event else json.loads(event.get('body', '{}'))
        cc = body.get(DYNAMO_KEY)

        if not cc:
            return response(400, {'error': f'Campo "{DYNAMO_KEY}" es requerido'})

        result = table.query(KeyConditionExpression=Key(DYNAMO_KEY).eq(str(cc)))
        items = result.get('Items', [])

        if not items:
            return response(404, {'error': 'Registro no encontrado'})

        return response(200, items[0])

    except json.JSONDecodeError:
        return response(400, {'error': 'JSON inválido en el body'})
    except Exception as e:
        logger.error(f'Error: {e}')
        return response(500, {'error': 'Error interno del servidor'})


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body, default=str)
    }
