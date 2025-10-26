variable "REGISTRY" {
  default = "ghcr.io"
}

variable "IMAGE_NAME" {
  default = "calebsargeant/nmap-exporter"
}

variable "VERSION" {
  default = "latest"
}

variable "PLATFORMS" {
  default = "linux/amd64,linux/arm64"
}

group "default" {
  targets = ["nmap-exporter"]
}

target "docker-metadata-action" {}

target "nmap-exporter" {
  inherits   = ["docker-metadata-action"]
  context    = "."
  dockerfile = "Dockerfile"
  platforms  = split(",", PLATFORMS)
}

target "nmap-exporter-push" {
  inherits = ["nmap-exporter"]
  output   = ["type=registry"]
}
