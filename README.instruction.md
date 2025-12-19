# Technical description

Use language python.


Locally run in venv create with uv tool.
Use venv with uv for Python environment management and dependency installation.
Keep requirements.txt updated.

Backend server flask.

UI - use plain javascript

App should be delivered as docker image.

Generate docker compose file to deploy to docker swarm.

# Update docker secret



docker service scale brencher_brencher-backend=0 brencher2_brencher-backend=0
docker service update --secret-rm brencher-secrets brencher_brencher-backend
docker service update --secret-rm brencher-secrets brencher2_brencher-backend
docker secret rm brencher-secrets

printf "GIT_USERNAME=git\nGIT_PASSWORD=TODO\n" | \
docker secret create brencher-secrets -

docker service update --secret-add brencher-secrets brencher_brencher-backend
docker service update --secret-add brencher-secrets brencher2_brencher-backend
docker service scale brencher_brencher-backend=1 brencher2_brencher-backend=1
