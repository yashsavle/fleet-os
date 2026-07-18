FROM golang:1.22.12-bookworm@sha256:3d699e4d15d0f8f13c9195c0632a16702b8cbdece2955af1c23b37ae5d55a253 AS build

WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY gen/go ./gen/go
COPY services/telemetry-ingester ./services/telemetry-ingester

RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/telemetry-ingester ./services/telemetry-ingester/cmd/telemetry-ingester

FROM gcr.io/distroless/static-debian12:nonroot@sha256:aef9602f8710ec12bde19d593fed1f76c708531bb7aba205110f1029786ead7b

COPY --from=build /out/telemetry-ingester /telemetry-ingester

EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/telemetry-ingester"]

