# variables.tf
# Define input variables for Terraform modules
# TODO: Add variables for resource names, locations, SKUs, etc.

variable "location" {
  description = "Azure region to deploy resources"
  type        = string
  default     = "eastus"
} 