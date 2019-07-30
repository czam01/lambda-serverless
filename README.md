# Proyecto Platzi

## Despliegue del proyeto

### Pre-Requisitos
Acá se deben desplegar todos los pre-requisitos para el proyecto, los cuales incluyen lo siguiente: 
*  Buckets.
*  Roles del pipeline.
*  Llaves KMS.
Para esta fase se debe desplegar primero --> https://github.com/czam01/cloudformation/tree/master/codepipeline 
*  Se puede crear una instancia de Cloud9 y se ejecuta el .sh, este ejecutará el template YML el cual desplegará todos los recursos necesarios de ahora en adelante para el proyecto.

### DynamoDB
Se debe realizar el despliegue de la BD DynamoDB la cual almacenará el registro de los votantes con la siguiente información:
*  DNI/CC
*  Nombre
*  Apellido
*  Dirección
*  Puesto de votación

Esta BD se debe desplegar con el siguiente template --> https://github.com/czam01/cloudformation/blob/master/nested/dynamo.yml 
Recuerden los parámetros de este template como Nombre y Key de la tabla, adicionalmente los datos de usuarios se deben ingresar de forma manual, en este despliegue solo se crea la tabla no la data dentro de ella.

### Pipeline y Lambda
Ahora debemos desplegar el pipeline que tendrá la función de automatizar el despliegue de nuestra serverless function.



