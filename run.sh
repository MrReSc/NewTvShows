#!/bin/bash
sudo docker build --rm -t newtvshows:latest "."
sudo docker-compose up -d