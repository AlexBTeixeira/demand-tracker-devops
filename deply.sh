#!/bin/bash
# deploy.sh (versão sem SSM)

set -e

echo "Iniciando processo de deploy..."

# --- PASSO 0: OBTER INFORMAÇÕES DA STACK ATIVA ---
STACK_NAME=$(aws cloudformation describe-stacks --query "Stacks[?StackName | contains(@, 'demand-tracker') && StackStatus=='CREATE_COMPLETE' || StackStatus=='UPDATE_COMPLETE'].StackName" --output text | sort | tail -n 1)
if [ -z "$STACK_NAME" ]; then
    echo "ERRO: Nenhuma stack ativa do CloudFormation encontrada."
    exit 1
fi
echo "Usando informações da stack: $STACK_NAME"

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY_URI=$(aws ecr describe-repositories --repository-names "${STACK_NAME}-repo" --query "repositories[0].repositoryUri" --output text)
ECS_CLUSTER_NAME="${STACK_NAME}-cluster"
ECS_SERVICE_NAME="demand-tracker-service"
ECS_TASK_DEFINITION_NAME="demand-tracker-task"
S3_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='S3BucketName'].OutputValue" --output text)
DB_HOST=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='RDSEndpoint'].OutputValue" --output text)

# --- PASSO 1: ATUALIZAR O CÓDIGO FONTE ---
echo "Atualizando o código-fonte do repositório..."
cd /home/ec2-user/app
git pull

# --- PASSO 2: BUILD, TAG E PUSH DA IMAGEM DOCKER ---
echo "Fazendo login no Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "Construindo a imagem Docker..."
IMAGE_TAG=$(date +%Y%m%d%H%M%S)
docker build -t $ECR_REPOSITORY_URI .

echo "Criando a tag e enviando a imagem para o ECR..."
docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:$IMAGE_TAG
docker push $ECR_REPOSITORY_URI:$IMAGE_TAG
docker push $ECR_REPOSITORY_URI:latest

# --- PASSO 3: CRIAR/ATUALIZAR A DEFINIÇÃO DA TAREFA ECS ---
echo "Criando nova revisão da Task Definition..."

# --- INÍCIO DA MODIFICAÇÃO: Ler a senha do arquivo local ---
# Lê a senha do arquivo criado pelo UserData do CloudFormation
DB_PASSWORD=$(cat /home/ec2-user/db_secret.txt)
# --- FIM DA MODIFICAÇÃO ---

# Roles do ambiente AWS Academy
TASK_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/LabInstanceProfile"
EXECUTION_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskExecutionRole"

# Cria o arquivo de definição de tarefa dinamicamente
cat > /home/ec2-user/app/task-definition.json <<EOF
{
  "family": "${ECS_TASK_DEFINITION_NAME}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "${EXECUTION_ROLE_ARN}",
  "taskRoleArn": "${TASK_ROLE_ARN}",
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
        
        # --- INÍCIO DA MODIFICAÇÃO: Passar senha como variável de ambiente ---
        {"name": "MYSQL_PASSWORD", "value": "${DB_PASSWORD}"}
        # --- FIM DA MODIFICAÇÃO ---
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

aws ecs register-task-definition --cli-input-json file:///home/ec2-user/app/task-definition.json > /dev/null

# --- PASSO 4: CRIAR/ATUALIZAR O SERVIÇO ECS ---
echo "Verificando se o serviço ECS já existe..."
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