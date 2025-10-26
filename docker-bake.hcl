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

target "nmap-exporter" {
  context    = "."
  dockerfile = "Dockerfile"
  tags       = ["${REGISTRY}/${IMAGE_NAME}:${VERSION}"]
  platforms  = split(",", PLATFORMS)
}

target "nmap-exporter-push" {
  inherits  = ["nmap-exporter"]
  tags      = ["${REGISTRY}/${IMAGE_NAME}:${VERSION}"]
  platforms = split(",", PLATFORMS)
  output    = ["type=registry"]
}
