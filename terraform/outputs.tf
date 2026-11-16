output "public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_instance.app.public_ip
}

output "app_url" {
  description = "Application URL"
  value       = "http://${aws_instance.app.public_ip}:${var.app_port}"
}

output "health_url" {
  description = "Health-check URL"
  value       = "http://${aws_instance.app.public_ip}:${var.app_port}/health"
}

output "s3_bucket" {
  description = "S3 bucket for logs and artifacts"
  value       = aws_s3_bucket.logs.bucket
}
