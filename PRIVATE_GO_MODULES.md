# Private Go modules

Go services depend on the private module `github.com/sunshineOfficial/golib`.
Configure Go and GitHub authentication before running `go get`, `go mod
download`, or Docker builds.

## Local Go commands

Run once on the developer machine:

```bash
go env -w GOPRIVATE=github.com/sunshineOfficial/*
go env -w GONOSUMDB=github.com/sunshineOfficial/*
```

Authenticate GitHub for HTTPS, for example with `gh auth login`, or configure
Git to use a token:

```bash
git config --global url."https://x-access-token:${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"
```

Then commands such as this work from any Go service directory:

```bash
go get github.com/sunshineOfficial/golib@v0.0.25
go mod download
```

## Docker builds

The Go Dockerfiles read a BuildKit secret named `github_token`. For a single
service build:

```bash
export GITHUB_TOKEN=<token-with-access-to-golib>
docker build --secret id=github_token,env=GITHUB_TOKEN -t task-service:latest ../task-service
```

For the dev stack, Compose passes the same environment variable as a build
secret:

```bash
export GITHUB_TOKEN=<token-with-access-to-golib>
docker compose -f docker-compose.dev.yml -p energy-control-system up -d --build
```

The token is available only during `go mod download` and is not copied into the
runtime image.
