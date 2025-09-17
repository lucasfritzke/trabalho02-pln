provider "aws" {
  region = var.region
}

# S3 para salvar os CSVs
resource "aws_s3_bucket" "csv_bucket" {
  bucket = var.bucket_name
}

# Role para SageMaker Job
resource "aws_iam_role" "sagemaker_role" {
  name = "sagemaker-processing-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Permissões de escrita no S3
resource "aws_iam_role_policy_attachment" "sagemaker_s3" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Repositório ECR para tua imagem
resource "aws_ecr_repository" "this" {
  name = "filme-job"
}

# CloudWatch Rule (1x por mês)
resource "aws_cloudwatch_event_rule" "monthly" {
  name                = "filme-job-monthly"
  schedule_expression = "cron(0 0 1 * ? *)"
}

# Permissão EventBridge → Lambda
resource "aws_lambda_permission" "allow_event" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.orchestrator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.monthly.arn
}

# Target: EventBridge dispara Lambda orquestradora
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.monthly.name
  target_id = "filme-job-orchestrator"
  arn       = aws_lambda_function.orchestrator.arn
}

# Lambda que dispara o SageMaker Job
resource "aws_lambda_function" "orchestrator" {
  function_name = "filme-job-orchestrator"
  role          = aws_iam_role.lambda_role.arn
  handler       = "orchestrator.lambda_handler"
  runtime       = "python3.13"
  filename      = "lambda_orchestrator.zip"
  timeout       = 60
  environment {
    variables = {
      SAGEMAKER_ROLE = aws_iam_role.sagemaker_role.arn
      IMAGE_URI      = "${aws_ecr_repository.this.repository_url}:latest"
      BUCKET_NAME    = var.bucket_name
    }
  }
}

# Role da Lambda
resource "aws_iam_role" "lambda_role" {
  name = "lambda-orchestrator-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Permissões para Lambda chamar SageMaker
resource "aws_iam_role_policy_attachment" "lambda_sagemaker" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}
