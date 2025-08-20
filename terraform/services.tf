resource "aws_instance" "app_server" {
  ami           = "ami-0c55b159cbfafe1f0" # Amazon Linux 2 AMI
  instance_type = "t2.micro"
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  subnet_id              = aws_subnet.public.id
  key_name               = "meu-par-de-chaves" # Substitua pelo seu par de chaves
  tags = { Name = "Demand-Tracker-EC2" }
}

resource "aws_db_instance" "default" {
  identifier           = "demand-tracker-db"
  allocated_storage    = 20
  instance_class       = "db.t3.micro"
  engine               = "mysql"
  engine_version       = "8.0"
  username             = "admin"
  password             = var.db_password
  db_subnet_group_name = aws_db_subnet_group.default.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot  = true
}

resource "aws_s3_bucket" "attachments" {
  bucket = "demand-tracker-attachments-${random_id.bucket_id.hex}"
}
# ... (outros recursos como random_id, db_subnet_group)