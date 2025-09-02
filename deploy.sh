set -e

# pede o nome da stack ao inves de tentar descobrir (Role não funciona direito)
if [ -z "$1" ]; then
    echo "ERRO: O nome da stack do CloudFormation não foi fornecido."
    echo "Uso: ./deploy.sh <NOME_DA_SUA_STACK>"
    exit 1
fi

STACK_NAME=$1
echo "Iniciando deploy para a stack: $STACK_NAME"

# variáveis
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY_URI=$(aws ecr describe-repositories --repository-names "${STACK_NAME}-repo" --query "repositories[0].repositoryUri" --output text)
ECS_CLUSTER_NAME="${STACK_NAME}-cluster"
ECS_SERVICE_NAME="demand-tracker-service"
ECS_TASK_DEFINITION_NAME="demand-tracker-task"
S3_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='S3BucketName'].OutputValue" --output text)
DB_HOST=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='RDSEndpoint'].OutputValue" --output text)


echo "Atualizando o código-fonte do repo.."
git pull

echo "Fazendo login no  ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "Construindo a imagem..."
IMAGE_TAG=$(date +%Y%m%d%H%M%S)
docker build -t $ECR_REPOSITORY_URI .

echo "Enviando para o ECR..."
docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:$IMAGE_TAG
docker push $ECR_REPOSITORY_URI:$IMAGE_TAG
docker push $ECR_REPOSITORY_URI:latest

echo "Criando nova revisão da Task Definition (usando LabRole)..."
DB_PASSWORD=$(cat /home/ec2-user/db_secret.txt)
TASK_DEF_JSON_PATH="/home/ec2-user/app/task-definition.json"

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/LabRole"

# Gerar o arquivo JSON
cat > ${TASK_DEF_JSON_PATH} <<EOF
{
  "family": "${ECS_TASK_DEFINITION_NAME}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "${ROLE_ARN}",
  "taskRoleArn": "${ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "demand-tracker-container",
      "image": "${ECR_REPOSITORY_URI}:${IMAGE_TAG}",
      "portMappings": [
        {
          "containerPort": 5050,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {"name": "MYSQL_HOST", "value": "${DB_HOST}"},
        {"name": "MYSQL_USER", "value": "admin"},
        {"name": "MYSQL_DB", "value": "demandtrackerdb"},
        {"name": "S3_BUCKET", "value": "${S3_BUCKET_NAME}"},
        {"name": "SECRET_KEY", "value": "uma-chave-secreta-forte-deve-ser-usada-aqui"},
        {"name": "MYSQL_PASSWORD", "value": "${DB_PASSWORD}"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/${ECS_TASK_DEFINITION_NAME}",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

# Registra a nova definição de tarefa
aws ecs register-task-definition --cli-input-json file://${TASK_DEF_JSON_PATH} > /dev/null

# Cria ou Atualiza o ECS
echo "Verificando o serviço ECS..."
SERVICE_EXISTS=$(aws ecs describe-services --cluster $ECS_CLUSTER_NAME --services $ECS_SERVICE_NAME --query "services[?status!='INACTIVE'] | length(@)")
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=${STACK_NAME}-PublicSubnet" --query "Subnets[0].SubnetId" --output text)
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=tag:Name,Values=${STACK_NAME}-ECS-Service-SG" --query "SecurityGroups[0].GroupId" --output text)

if [ "$SERVICE_EXISTS" -eq 0 ]; then
  echo "Serviço não encontrado. Criando um novo..."
  aws ecs create-service --cluster $ECS_CLUSTER_NAME --service-name $ECS_SERVICE_NAME --task-definition $ECS_TASK_DEFINITION_NAME --desired-count 1 --launch-type "FARGATE" --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[${SECURITY_GROUP_ID}],assignPublicIp=ENABLED}"
else
  echo "Serviço encontrado. Atualizando..."
  aws ecs update-service --cluster $ECS_CLUSTER_NAME --service $ECS_SERVICE_NAME --task-definition $ECS_TASK_DEFINITION_NAME --force-new-deployment
fi

echo "Deploy concluído com sucesso!"