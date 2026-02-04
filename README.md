# Photography Portfolio [Web Site](https://burcuatak.com)

The portfolio web site based on **Django** framework. It is ready to go & **dockerized** for **swarm cluster** on **AWS EC2 nodes**.

Staticfiles are served from **AWS S3 Bucket**.

The project uses **Traefik** for reverse proxy and **SSL cert** process.

Database requirement was met with Postgres image in swarm cluster.

The Github action is just to build and push docker image to docker hub repository.

Data persistent requirement is met by **AWS EFS** Volume for Traefik CERT and Postgres data location. With EFS Volume, new nodes can connect easyly to the DIRs.

## environtment example

Environment settings inside \*\*environments/burcuphoto_environment.txt"

- Email Receivers for website contact form's endpoint.
- DEBUG 1 (True) or 0 (False)
- DB_HOST willnot need to change if docker-compose-postgres' definition.

```shell
ADMIN_ADDRESS=CHANGE/WITH/YOUR/ADMIN/ENDPOINT
AlLOWED_HOSTS=example.com,www.example.com
EMAIL_RECEIVER_ONE=CHANGE_WITH_EMAIL_ONE
EMAIL_RECEIVER_TWO=CHANGE_WITH_EMAIL_TWO
DEBUG=1
POSTGRES_DB=CHANGE_WITH_DATABASE_NAME
DB_HOST=db
BUCKET_NAME=CHANGE_WITH_S3_BUCKET_NAME
AWS_S3_REGION_NAME=CHANGE_WITH_AWS_REGION_NAME
```

## docker-compose files

3 Docker compose files are setted up for swarm cluster and there are several **CHANGE_WITH** sections in the files.

## Local development with Docker Compose

Use the local compose file and env template below to run the app locally:

```shell
${EDITOR:-nano} environments/burcuphoto_local.env
docker compose up --build
```

The app will be available at http://localhost:8000.

## aws_user_data.sh

This file is for AWS EC2 instance creation page's **USER DATA** section. This scipt targets swarm worker instance. And it contains server harden & network optimization settings. There are several **CHANGE_WITH** sections.This file is for AWS EC2 instance creation page's **USER DATA** section. This scipt targets swarm worker instance. And it contains server harden & network optimization settings. There are several **CHANGE_WITH** sections.
