variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 instance type (free-tier eligible by default)"
  type        = string
  default     = "t2.micro"
}

variable "project_name" {
  description = "Project name used for tagging and naming resources"
  type        = string
  default     = "cloudops-pulse"
}

variable "docker_image" {
  description = "Container image to run on EC2 (GHCR image after CI deploy)"
  type        = string
  default     = "ghcr.io/anshchaudhary289-prog/cloudops-pulse:latest"
}

variable "app_port" {
  description = "Port the application listens on"
  type        = number
  default     = 8000
}
