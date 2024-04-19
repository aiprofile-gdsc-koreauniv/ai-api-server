####################################################
############# Build & Run Management ###############
####################################################
.PHONY: help build build_dev run run_dev install_model setup_model_dir bootstrap_extensions install_extension list_extensions install_extensions_dependencies install_custom_dependencies default

IMAGE_NAME = ai-api-server

help:
	@echo "Help for make commands @$(IMAGE_NAME)"
	@awk '/^\t@###/{print "\t" substr($$0, index($$0, "\t@###") + length("\t@###"))}' Makefile | while read -r helpline; do \
		echo "\t- $$helpline"; \
	done

build:
	@### build : build base docker image for only api-server
	@echo "Building Docker image..."
	@docker build -f dev.dockerfile -t $(IMAGE_NAME):base .

run:
	@### run : run docker image as $(IMAGE_NAME):base
	@echo "Running Docker container..."
	@read -p "Enter webui hostname to bind: " DOCKER_HOSTNAME; 
	@## For volume mount,
	@## docker run --rm -v models:/app/stable-diffusion-webui/models/ -p 7860:7860 $(IMAGE_NAME):base
	@# docker run -e WEBUI_URL="$$DOCKER_HOSTNAME" -p 5672:5672 -p 9001:9001 $(IMAGE_NAME):base

default: help
