# asobann
online card / board game platform

## How to run locally

```
% git clone https://github.com/asobann/asobann_app.git
% cd asobann_app/
% npm i -d
% npx webpack
% docker compose -f .\deploy\localdev\docker-compose.yml up --build
Access http://localhost:8000/
```

## How to make things up to date after a while

1. Remove Pipfile.lock
1. Make sure old pipenv venv is not there.  Run pipenv --rm
1. Run pipenv install --python 3.xx (better use latest python)
1. Remove package-lock.json
1. Update pipfile.json by following commands (it was my case)
    1. reinstall nvm
    2. nvm install lts
    3. npx npm-check-updates -u
    4. npm install --save-dev @babel/core @babel/preset-env
1. npm i -d
1. Check and commit