#!/bin/bash
podman pod stop -a 
podman pod rm -a
podman build --rm -t newtvshows:latest "."
podman-compose up