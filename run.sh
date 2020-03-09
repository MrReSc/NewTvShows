#!/bin/bash
sudo docker build --rm -t newtvshows:latest "."
sudo docker-compose -f docker-compose-production.yml up -d