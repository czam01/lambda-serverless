# Laboratorio: VotaNet - Despliegue Serverless con CI/CD

## Objetivo

Desplegar un sistema serverless de consulta de votantes en AWS usando Lambda, DynamoDB, API Gateway y un pipeline de CI/CD con CodePipeline + CodeBuild.

## Arquitectura Final

```
GitHub (master)
    |
    v
CodePipeline
    |
    |-- Source --> GitHub
    |-- Build  --> CodeBuild (SAM package)
    '-- Deploy --> CloudFormation (Change Set)
                        |
                        v
                   AWS Lambda (Python 3.12)
                        |
    API Gateway <-------'
        |
        v
    DynamoDB (lablambda)
```

## Estructura del Repositorio

```
├── lambda_function.py                    # Funcion Lambda
├── template.yml                          # SAM template (Lambda + IAM Role)
├── config/
│   └── buildspec.yml                     # Configuracion de CodeBuild
├── dynamo/
│   ├── dynamo.yml                        # CloudFormation para tabla DynamoDB
│   └── dynamo.sh                         # Script de despliegue de DynamoDB
├── prereq/
│   ├── aws-codepipeline-prereq.yml       # Pre-requisitos (roles, bucket, policies)
│   └── aws-codepipeline-prereq.sh        # Script de despliegue de pre-requisitos
└── README.md
```

## Tecnologias

- Runtime: Python 3.12
- Infraestructura: AWS SAM + CloudFormation
- CI/CD: AWS CodePipeline + CodeBuild
- Base de datos: Amazon DynamoDB (PAY_PER_REQUEST, SSE habilitado)
- Compute: AWS Lambda (128 MB, timeout 10s)

## Modelo de Datos

La tabla DynamoDB almacena registros de votantes con la siguiente estructura:

| Campo      | Tipo   | Descripcion          |
|------------|--------|----------------------|
| cc         | String | Cedula (Partition Key) |
| nombre     | String | Nombre del votante   |
| apellido   | String | Apellido del votante |
| direccion  | String | Direccion            |
| puesto     | String | Puesto de votacion   |

## Pre-requisitos

- Cuenta de AWS con permisos de administrador
- AWS CLI instalado y configurado (aws configure)
- Repositorio en GitHub con el codigo del proyecto
- Region: us-east-1 (N. Virginia)

---

## Fase 1: Desplegar Pre-Requisitos (IAM Roles, Bucket S3, Policies)

Esta fase crea la infraestructura base: bucket S3 para artefactos, roles de IAM para CodeBuild y CodePipeline, y las politicas que usara la Lambda.

### 1.1 Ejecutar el script

```bash
cd prereq
chmod +x aws-codepipeline-prereq.sh
./aws-codepipeline-prereq.sh
```

### 1.2 Verificar el despliegue

```bash
aws cloudformation describe-stacks \
  --stack-name codepipeline-lambda-prereq \
  --region us-east-1 \
  --query "Stacks[0].StackStatus"
```

Debe retornar "CREATE_COMPLETE".

### 1.3 Verificar los outputs

```bash
aws cloudformation describe-stacks \
  --stack-name codepipeline-lambda-prereq \
  --region us-east-1 \
  --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" \
  --output table
```

Deberias ver estos outputs:

| Output              | Descripcion                          |
|---------------------|--------------------------------------|
| PipelineRole        | ARN del rol de CodePipeline          |
| CodeBuildRole       | ARN del rol de CodeBuild             |
| S3ArtifactsBucket   | Nombre del bucket de artefactos      |
| LambdaPolicyDynamo  | ARN de la policy de DynamoDB         |
| LambdaPolicyCW      | ARN de la policy de CloudWatch Logs  |

IMPORTANTE: Copia el nombre del S3ArtifactsBucket, lo necesitaras en la Fase 3.

### Recursos creados

- S3 Bucket: codepipeline-artefactos-{ACCOUNT_ID}-us-east-1 (con encryption AES256 y public access bloqueado)
- CodeBuildRole: Permisos para logs, S3 y CloudFormation
- CodePipelineRole: Permisos para S3, CodeBuild, CloudFormation e IAM PassRole
- LambdaPolicyDynamo: dynamodb:Query y dynamodb:GetItem
- LambdaPolicyCW: logs:CreateLogGroup, CreateLogStream, PutLogEvents

---

## Fase 2: Desplegar Tabla DynamoDB

### 2.1 Ejecutar el script

```bash
cd dynamo
chmod +x dynamo.sh
./dynamo.sh
```

### 2.2 Verificar la tabla

```bash
aws dynamodb describe-table \
  --table-name lablambda \
  --region us-east-1 \
  --query "Table.{Name:TableName, Status:TableStatus, Key:KeySchema[0].AttributeName, Billing:BillingModeSummary.BillingMode}"
```

Debe mostrar:

```json
{
    "Name": "lablambda",
    "Status": "ACTIVE",
    "Key": "cc",
    "Billing": "PAY_PER_REQUEST"
}
```

### 2.3 Insertar datos de prueba

Desde la consola de AWS:

1. Ir a DynamoDB, Tables, lablambda
2. Click en Explore table items, Create item
3. Agregar los siguientes atributos (todos tipo String):

Votante 1:

| Atributo   | Valor           |
|------------|-----------------|
| cc         | 123456789       |
| nombre     | Pedro           |
| apellido   | Gomez           |
| direccion  | Cra 1 1-1       |
| puesto     | mesa 50         |

Votante 2:

| Atributo   | Valor           |
|------------|-----------------|
| cc         | 987654321       |
| nombre     | Maria           |
| apellido   | Lopez           |
| direccion  | Calle 10 5-20   |
| puesto     | mesa 12         |

Tambien puedes insertar por CLI:

```bash
aws dynamodb put-item \
  --table-name lablambda \
  --region us-east-1 \
  --item '{
    "cc": {"S": "123456789"},
    "nombre": {"S": "Pedro"},
    "apellido": {"S": "Gomez"},
    "direccion": {"S": "Cra 1 1-1"},
    "puesto": {"S": "mesa 50"}
  }'

aws dynamodb put-item \
  --table-name lablambda \
  --region us-east-1 \
  --item '{
    "cc": {"S": "987654321"},
    "nombre": {"S": "Maria"},
    "apellido": {"S": "Lopez"},
    "direccion": {"S": "Calle 10 5-20"},
    "puesto": {"S": "mesa 12"}
  }'
```

### 2.4 Verificar los datos

```bash
aws dynamodb scan \
  --table-name lablambda \
  --region us-east-1 \
  --query "Items[*].{CC:cc.S, Nombre:nombre.S, Apellido:apellido.S}" \
  --output table
```

---

## Fase 3: Crear el Pipeline de CI/CD

### 3.1 Conectar GitHub con AWS

1. Ir a CodePipeline en la consola de AWS (region us-east-1)
2. En el menu lateral, ir a Settings, Connections
3. Click en Create connection
4. Seleccionar GitHub como proveedor
5. Nombre de la conexion: github-votanet
6. Click en Connect to GitHub, autorizar AWS en tu cuenta de GitHub
7. Seleccionar Install a new app, seleccionar el repositorio
8. Click en Connect

NOTA: La conexion queda en estado Available. Copia el ARN de la conexion.

### 3.2 Crear proyecto de CodeBuild

1. Ir a CodeBuild, Build projects, Create build project

2. Project configuration:
   - Project name: VotaNet-Build

3. Source:
   - Source provider: No source (el source viene del pipeline)

4. Environment:
   - Environment image: Managed image
   - Compute: EC2
   - Operating system: Amazon Linux
   - Runtime: Standard
   - Image: aws/codebuild/amazonlinux2-x86_64-standard:5.0
   - Service role: Existing service role
   - Role ARN: Seleccionar el rol CodeBuildRole (creado en Fase 1)
   - Marcar: Allow AWS CodeBuild to modify this service role

5. Environment variables:

   | Name        | Value                                              | Type       |
   |-------------|----------------------------------------------------|------------|
   | S3_BUCKET   | codepipeline-artefactos-{ACCOUNT_ID}-us-east-1     | Plaintext  |

   Reemplaza {ACCOUNT_ID} con tu ID de cuenta AWS.

6. Buildspec:
   - Build specifications: Use a buildspec file
   - Buildspec name: config/buildspec.yml

7. Click en Create build project

### 3.3 Crear el Pipeline

1. Ir a CodePipeline, Pipelines, Create pipeline

2. Step 1 - Pipeline settings:
   - Pipeline name: VotaNet-Pipeline
   - Pipeline type: V2
   - Execution mode: Queued
   - Service role: Existing service role
   - Role ARN: Seleccionar el rol PipelineRole (creado en Fase 1)
   - Marcar: Allow AWS CodePipeline to create a service role
   - Click en Next

3. Step 2 - Source stage:
   - Source provider: GitHub (via AWS CodeStar Connections)
   - Connection: Seleccionar github-votanet (creada en paso 3.1)
   - Repository name: Seleccionar tu repositorio
   - Branch name: master
   - Output artifact format: CodePipeline default
   - Trigger: Push in a branch
   - Click en Next

4. Step 3 - Build stage:
   - Build provider: AWS CodeBuild
   - Region: US East (N. Virginia)
   - Project name: VotaNet-Build
   - Build type: Single build
   - Click en Next

5. Step 4 - Deploy stage:
   - Deploy provider: AWS CloudFormation
   - Region: US East (N. Virginia)
   - Action mode: Create or replace a change set
   - Stack name: VotaNet-Lambda
   - Change set name: VotaNet-ChangeSet
   - Template:
     - Artifact name: BuildArtifact
     - File name: output.yml
   - Capabilities: Marcar CAPABILITY_IAM y CAPABILITY_AUTO_EXPAND
   - Role name: Seleccionar el PipelineRole
   - Click en Next

6. Step 5 - Review:
   - Revisar toda la configuracion
   - Click en Create pipeline

### 3.4 Agregar accion de Execute Change Set

El pipeline se crea pero solo genera el Change Set sin ejecutarlo. Hay que agregar la accion de ejecucion:

1. En el pipeline recien creado, click en Edit
2. En el stage Deploy, click en Edit stage
3. Click en + Add action group (debajo de la accion existente)
4. Configurar:
   - Action name: Execute-ChangeSet
   - Action provider: AWS CloudFormation
   - Input artifacts: BuildArtifact
   - Action mode: Execute a change set
   - Stack name: VotaNet-Lambda
   - Change set name: VotaNet-ChangeSet
5. Click en Done, Save, Save

### 3.5 Ejecutar el Pipeline

El pipeline se ejecuta automaticamente al crearlo. Si necesitas ejecutarlo manualmente:

1. Click en Release change, Release

2. Esperar a que las 3 etapas pasen a verde:
   - Source
   - Build
   - Deploy

Tiempo estimado: 3-5 minutos

### 3.6 Verificar la Lambda

```bash
aws lambda get-function \
  --function-name VotaNet \
  --region us-east-1 \
  --query "Configuration.{Name:FunctionName, Runtime:Runtime, Memory:MemorySize, Timeout:Timeout, State:State}"
```

Debe mostrar:

```json
{
    "Name": "VotaNet",
    "Runtime": "python3.12",
    "Memory": 128,
    "Timeout": 10,
    "State": "Active"
}
```

### 3.7 Probar la Lambda directamente

```bash
aws lambda invoke \
  --function-name VotaNet \
  --region us-east-1 \
  --payload '{"cc": "123456789"}' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

Respuesta esperada:

```json
{
  "statusCode": 200,
  "headers": {"Content-Type": "application/json"},
  "body": "{\"nombre\": \"Pedro\", \"apellido\": \"Gomez\", \"cc\": \"123456789\", \"direccion\": \"Cra 1 1-1\", \"puesto\": \"mesa 50\"}"
}
```

---

## Fase 4: Configurar API Gateway

### 4.1 Crear el API REST

1. Ir a API Gateway, Create API
2. Seleccionar REST API, Build
3. Configurar:
   - API name: VotaNet-API
   - API endpoint type: Regional
4. Click en Create API

### 4.2 Crear recurso y metodo

1. Click en Create resource
   - Resource path: /
   - Resource name: votante
   - Click en Create resource

2. Seleccionar el recurso /votante, click en Create method
   - Method type: POST
   - Integration type: Lambda function
   - Marcar: Lambda proxy integration
   - Lambda function: VotaNet
   - Region: us-east-1
   - Click en Create method

3. Confirmar el permiso para que API Gateway invoque la Lambda

### 4.3 Desplegar el API

1. Click en Deploy API
2. Stage: New stage
   - Stage name: prod
3. Click en Deploy
4. Copiar la Invoke URL que aparece arriba

### 4.4 Probar el API

```bash
curl -X POST https://{API_ID}.execute-api.us-east-1.amazonaws.com/prod/votante \
  -H "Content-Type: application/json" \
  -d '{"cc": "123456789"}'
```

Respuesta esperada:

```json
{
  "nombre": "Pedro",
  "apellido": "Gomez",
  "cc": "123456789",
  "direccion": "Cra 1 1-1",
  "puesto": "mesa 50"
}
```

### 4.5 Probar casos de error

Cedula no encontrada:

```bash
curl -X POST https://{API_ID}.execute-api.us-east-1.amazonaws.com/prod/votante \
  -H "Content-Type: application/json" \
  -d '{"cc": "000000000"}'
```

```json
{"error": "Registro no encontrado"}
```

Sin campo cc:

```bash
curl -X POST https://{API_ID}.execute-api.us-east-1.amazonaws.com/prod/votante \
  -H "Content-Type: application/json" \
  -d '{"nombre": "test"}'
```

```json
{"error": "Campo \"cc\" es requerido"}
```

---

## Verificacion Final

### Checklist

- [ ] Stack codepipeline-lambda-prereq en estado CREATE_COMPLETE
- [ ] Stack dynamo-lambda-lab en estado CREATE_COMPLETE
- [ ] Tabla lablambda con datos de prueba insertados
- [ ] Proyecto CodeBuild VotaNet-Build creado
- [ ] Pipeline VotaNet-Pipeline con las 3 etapas en verde
- [ ] Lambda VotaNet en estado Active con runtime python3.12
- [ ] API Gateway VotaNet-API desplegado en stage prod
- [ ] Consulta POST con cedula valida retorna datos del votante
- [ ] Consulta POST con cedula invalida retorna error 404

### Probar el flujo CI/CD completo

1. Hacer un cambio en lambda_function.py (por ejemplo, agregar un log)
2. Hacer git commit y git push a la rama master
3. Verificar que el pipeline se ejecuta automaticamente en CodePipeline
4. Esperar a que las 3 etapas pasen a verde
5. Probar la Lambda actualizada con curl

---

## Limpieza de Recursos

Para eliminar todos los recursos creados, ejecutar en este orden:

```bash
# 1. Eliminar API Gateway (desde la consola: seleccionar API, Delete)

# 2. Eliminar stack de la Lambda
aws cloudformation delete-stack \
  --stack-name VotaNet-Lambda \
  --region us-east-1

# 3. Eliminar el pipeline (desde la consola de CodePipeline)

# 4. Eliminar proyecto de CodeBuild (desde la consola de CodeBuild)

# 5. Eliminar tabla DynamoDB
aws cloudformation delete-stack \
  --stack-name dynamo-lambda-lab \
  --region us-east-1

# 6. Vaciar el bucket S3 antes de eliminar el stack de prereqs
aws s3 rm s3://codepipeline-artefactos-{ACCOUNT_ID}-us-east-1 --recursive --region us-east-1

# 7. Eliminar pre-requisitos
aws cloudformation delete-stack \
  --stack-name codepipeline-lambda-prereq \
  --region us-east-1
```

Reemplaza {ACCOUNT_ID} con tu ID de cuenta AWS.
