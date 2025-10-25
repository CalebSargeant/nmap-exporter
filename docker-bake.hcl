variable "REGISTRY" {
  default = "ghcr.io"
}

variable "IMAGE_NAME" {
  default = "calebsargeant/nmap-exporter"
}

variable "VERSION" {
  default = "latest"
}

group "default" {
  targets = ["nmap-exporter"]
}

target "nmap-exporter" {
  context    = "."
  dockerfile = "Dockerfile"
  tags = [
    "${REGISTRY}/${IMAGE_NAME}:${VERSION}",
    "${REGISTRY}/${IMAGE_NAME}:latest"
  ]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "nmap-exporter-push" {
  inherits = ["nmap-exporter"]
  output   = ["type=registry"]
}
