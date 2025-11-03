#!/bin/bash -l
git pull
./batch_process.py
jupyter nbconvert --to notebook --execute --inplace smooth.ipynb
git add .
git commit -am "auto update" --author="vedgesat-bot <ubuntu@wave.storm-surge.cloud.edu.au>"
git push
TAG=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
git tag $TAG
git push origin $TAG
gh release create $TAG --generate-notes